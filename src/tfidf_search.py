import os
os.environ["FASTEMBED_CACHE_PATH"] = "./models"

import json
import joblib
import numpy as np

from scipy.sparse import load_npz
from sklearn.metrics.pairwise import cosine_similarity
from fastembed import TextEmbedding

from src.citation_lookup import lookup_citation
from src.citation_parser import parse_citation
from src.legal_reranker import rerank_results
from src.preprocessing import preprocess_text
from src.utils import detect_language, translate_text, CONFIG


############################################
# RESOURCE CACHE
############################################

RESOURCE_CACHE = {}

embedding_model = TextEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


############################################
# LOAD RESOURCES
############################################

def load_resources(granularity):

    if granularity in RESOURCE_CACHE:
        return RESOURCE_CACHE[granularity]

    config = CONFIG[granularity]
    index_dir = config["index_dir"]

    resources = {}

    for language in ["en", "fr"]:

        with open(
            os.path.join(
                index_dir,
                config[f"inverted_index_{language}"]
            ),
            "r",
            encoding="utf-8"
        ) as f:
            inverted_index = json.load(f)

        tfidf_matrix = load_npz(
            os.path.join(
                index_dir,
                config[f"tfidf_matrix_{language}"]
            )
        )

        with open(
            os.path.join(
                index_dir,
                config[f"unit_ids_{language}"]
            ),
            "r",
            encoding="utf-8"
        ) as f:
            unit_ids = json.load(f)

        vectorizer = joblib.load(
            os.path.join(
                index_dir,
                config[f"vectorizer_{language}"]
            )
        )

        embeddings = np.load(
            os.path.join(
                index_dir,
                config[f"embeddings_{language}"]
            )
        )

        with open(
            os.path.join(
                index_dir,
                config[f"embedding_ids_{language}"]
            ),
            "r",
            encoding="utf-8"
        ) as f:
            embedding_unit_ids = json.load(f)   

        doc_id_to_idx = {
            doc_id: i
            for i, doc_id in enumerate(unit_ids)
        }

        resources[language] = {

            "inverted_index": inverted_index,

            "tfidf_matrix": tfidf_matrix,

            "unit_ids": unit_ids,

            "vectorizer": vectorizer,

            "embeddings": embeddings,

            "embedding_unit_ids": embedding_unit_ids,

            "doc_id_to_idx": doc_id_to_idx

        }

    RESOURCE_CACHE[granularity] = resources

    return resources


############################################
# QUERY EXPANSION
############################################

def expand_query(query):

    expansions = {
        "minimum age": ["minimum age", "age limit", "legal age"],
        "employment": ["employment", "work", "labor", "labour"],
        "durée maximale": ["durée maximale", "durée", "délai maximum", "période"],
        "séjour": ["séjour", "résidence", "présence"],
        "visiteur temporaire": ["visiteur temporaire", "visiteur", "étranger"],
        "liable": ["subject to", "responsible", "redevable", "assujetti"],
        "not liable": ["exempt", "exonerated", "exonéré", "non-assujetti", "business license"],
        "natural persons": ["individuals", "personnes physiques"],
        "election": ["poll", "voters", "scrutin", "électoral", "présidentielle", "presidential"],
        "voters": ["electorate", "électeurs"],
        "oppose": ["oppose", "refuse", "deny", "object to"],
        "étranger": ["étranger", "ressortissant étranger", "non-national"],
        "délai": ["délai", "période", "temps imparti"],
        "solliciter": ["solliciter", "demander", "faire une demande"],
        "encourues": ["encourues", "applicables", "prévues"],
        "facilite": ["facilite", "aide", "assiste", "contribue"],
        "entrée": ["entrée", "admission"],
        "conjointement": ["conjointement", "ensemble", "en collaboration"],
        "remitted": ["remitted", "paid", "transferred", "settled"],
        "forced": ["forced", "involuntary", "coerced"],
        "decree": ["decree", "presidential decree", "order", "décret"],
        "provisions": ["provisions", "entitlements", "benefits", "rights", "protections"]
    }

    query_lower = query.lower()
    expanded_terms = [query]

    for key, synonyms in expansions.items():
        if key in query_lower:
            expanded_terms.extend(synonyms)

    return " ".join(expanded_terms)


def preprocess_query(query: str) -> str:
    tokens = preprocess_text(query)
    return " ".join(tokens)


def get_candidate_indices(query_tokens, resources):

    inverted_index = resources["inverted_index"]
    doc_id_to_idx = resources["doc_id_to_idx"]

    candidate_docs = set()

    for token in query_tokens:

        postings = inverted_index.get(token)

        if postings:
            candidate_docs.update(postings.keys())

    if not candidate_docs:
        return None

    return [
        doc_id_to_idx[doc_id]
        for doc_id in candidate_docs
        if doc_id in doc_id_to_idx
    ]


 ############################################
# SINGLE LANGUAGE SEARCH
############################################

def search_single_language(
    processed_query,
    expanded_query,
    resources,
    legal_dir
):

    vectorizer = resources["vectorizer"]
    tfidf_matrix = resources["tfidf_matrix"]
    unit_ids = resources["unit_ids"]
    embeddings = resources["embeddings"]

    # -----------------------------------
    # Build query representations
    # -----------------------------------

    query_tokens = processed_query.split()

    query_vector = vectorizer.transform(
        [processed_query]
    )

    query_embedding = list(
        embedding_model.embed([expanded_query])
    )[0]

    # -----------------------------------
    # Candidate retrieval
    # -----------------------------------

    candidate_indices = get_candidate_indices(
        query_tokens,
        resources
    )

    tfidf_scores_global = cosine_similarity(
        query_vector,
        tfidf_matrix
    )[0]

    if candidate_indices:

        candidate_indices = set(candidate_indices)

        fallback_indices = np.argsort(
            tfidf_scores_global
        )[::-1][:100]

        candidate_indices.update(fallback_indices)

        candidate_indices = list(candidate_indices)

    else:

        candidate_indices = np.argsort(
            tfidf_scores_global
        )[::-1][:100]

    # -----------------------------------
    # Hybrid ranking
    # -----------------------------------

    tfidf_subset = tfidf_matrix[candidate_indices]

    embedding_subset = embeddings[candidate_indices]

    tfidf_scores = cosine_similarity(
        query_vector,
        tfidf_subset
    )[0]

    semantic_scores = cosine_similarity(
        [query_embedding],
        embedding_subset
    )[0]

    scores = (
        0.6 * tfidf_scores
        + 0.4 * semantic_scores
    )

    ranked = sorted(
        zip(candidate_indices, scores),
        key=lambda x: x[1],
        reverse=True
    )[:50]

    # -----------------------------------
    # Build results
    # -----------------------------------

    results = []

    for idx, score in ranked:

        if score == 0:
            continue

        unit_id = unit_ids[idx]

        text_path = os.path.join(
            legal_dir,
            unit_id
        )

        try:

            with open(
                text_path,
                "r",
                encoding="utf-8"
            ) as f:

                text = f.read()

        except Exception:
            continue

        results.append({

            "unit_id": unit_id,

            "score": float(score),

            "text": text

        })

    return results 


############################################
# HELPER: Deduplicate and sort combined results
############################################

def _combine_and_sort(primary_results, secondary_results):
    """
    Merge primary and secondary result lists,
    remove duplicates (keeping highest score),
    and sort by final_score (or score).
    Returns the sorted candidate pool.
    """
    candidate_pool = primary_results + secondary_results

    unique_results = {}
    for res in candidate_pool:
        unit_id = res["unit_id"]
        current_score = res.get("final_score", res.get("score", 0))
        if unit_id not in unique_results:
            unique_results[unit_id] = res
        else:
            existing_score = unique_results[unit_id].get("final_score", unique_results[unit_id].get("score", 0))
            if current_score > existing_score:
                unique_results[unit_id] = res

    candidate_pool = list(unique_results.values())
    candidate_pool.sort(key=lambda x: x.get("final_score", x["score"]), reverse=True)
    return candidate_pool 

############################################
# SEARCH
############################################   

def search(
    query,
    top_k=10,
    use_rerank=True,
    granularity="clause"
):
    # ----------------------------------------------------------
    # CITATION GATE (conservative): only when parse is confident
    # and lookup finds units. Otherwise concept search is unchanged.
    # ----------------------------------------------------------
    citation = parse_citation(query)
    if citation:
        citation_hits = lookup_citation(
            citation,
            granularity=granularity,
            top_k=top_k,
        )
        if citation_hits:
            query_language = detect_language(query)
            return {
                "query_language": query_language,
                "translated_query": "",
                "primary_results": citation_hits,
                "secondary_results": [],
                "final_results": citation_hits[:top_k],
                "search_mode": "citation",
                "citation": citation,
            }

    query_language = detect_language(query)
    resources = load_resources(granularity)
    legal_dir = CONFIG[granularity]["legal_dir"]

    # ----------------------------------------------------------
    # CASE 1: Query language is English or French
    # ----------------------------------------------------------
    if query_language in ["en", "fr"]:
        # Primary search in detected language
        expanded_query = expand_query(query)
        processed_query = preprocess_query(expanded_query)

        primary_results = search_single_language(
            processed_query=processed_query,
            expanded_query=expanded_query,
            resources=resources[query_language],
            legal_dir=legal_dir
        )
        if use_rerank:
            primary_results = rerank_results(primary_results, query=query)
        primary_results = primary_results[:10]

        # Translate to the other language
        if query_language == "en":
            translated_query = translate_text(text=query, source="en", target="fr")
            secondary_language = "fr"
        else:
            translated_query = translate_text(text=query, source="fr", target="en")
            secondary_language = "en"

        expanded_secondary = expand_query(translated_query)
        processed_secondary = preprocess_query(expanded_secondary)

        secondary_results = search_single_language(
            processed_query=processed_secondary,
            expanded_query=expanded_secondary,
            resources=resources[secondary_language],
            legal_dir=legal_dir
        )
        if use_rerank:
            secondary_results = rerank_results(secondary_results, query=translated_query)
        secondary_results = secondary_results[:10]

        # Add language labels
        for r in primary_results:
            r["language"] = query_language
        for r in secondary_results:
            r["language"] = secondary_language

        # Combine, deduplicate, sort
        candidate_pool = _combine_and_sort(primary_results, secondary_results)
        final_results = candidate_pool[:top_k]

        return {
            "query_language": query_language,
            "translated_query": translated_query,
            "primary_results": primary_results,
            "secondary_results": secondary_results,
            "final_results": final_results,
            "search_mode": "concept",
        }

    # ----------------------------------------------------------
    # CASE 2: Query language is NEITHER English nor French
    # ----------------------------------------------------------
    else:
        # Translate query to English and French
        eng_query = translate_text(text=query, source=query_language, target="en")
        fr_query = translate_text(text=query, source=query_language, target="fr")

        # --- Search in English index ---
        expanded_eng = expand_query(eng_query)
        processed_eng = preprocess_query(expanded_eng)

        primary_results = search_single_language(
            processed_query=processed_eng,
            expanded_query=expanded_eng,
            resources=resources["en"],
            legal_dir=legal_dir
        )
        if use_rerank:
            primary_results = rerank_results(primary_results, query=eng_query)
        primary_results = primary_results[:10]

        # --- Search in French index ---
        expanded_fr = expand_query(fr_query)
        processed_fr = preprocess_query(expanded_fr)

        secondary_results = search_single_language(
            processed_query=processed_fr,
            expanded_query=expanded_fr,
            resources=resources["fr"],
            legal_dir=legal_dir
        )
        if use_rerank:
            secondary_results = rerank_results(secondary_results, query=fr_query)
        secondary_results = secondary_results[:10]

        # Add language labels
        for r in primary_results:
            r["language"] = "en"
        for r in secondary_results:
            r["language"] = "fr"

        # Combine, deduplicate, sort
        candidate_pool = _combine_and_sort(primary_results, secondary_results)
        final_results = candidate_pool[:top_k]

        
        return {
            "query_language": query_language,
            "translated_query": eng_query,       # or fr_query – choose one
            "primary_results": primary_results,
            "secondary_results": secondary_results,
            "final_results": final_results,
            "search_mode": "concept",
        }  










if __name__ == "__main__":

    while True:

        query = input(
            "\nQuery (or exit): "
        ).strip()

        if query.lower() == "exit":
            break

        granularity = input(
            "Granularity (clause/as/document) [clause]: "
        ).strip()

        if not granularity:
            granularity = "clause"

        output = search(
            query=query,
            top_k=10,
            granularity=granularity,
            use_rerank=True
        )

        print("\n")
        print("=" * 80)
        print("FINAL CROSS-ENCODER RESULTS")
        print("=" * 80)

        print(
            f"Detected language : "
            f"{output['query_language']}"
        )

        print(
            f"Translated query  : "
            f"{output['translated_query']}"
        )

        print()

        for i, r in enumerate(
            output["final_results"],
            start=1
        ):

            print("-" * 70)

            print(
                f"Rank       : {i}"
            )

            print(
                f"Language   : "
                f"{r.get('language', 'unknown')}"
            )

            print(
                f"Unit       : "
                f"{r['unit_id']}"
            )

            print(
                f"Hybrid     : "
                f"{r['score']:.4f}"
            )

            if "final_score" in r:

                print(
                    f"LegalScore : "
                    f"{r['final_score']:.4f}"
                )

            if "cross_score" in r:
                print(
                    f"CrossScore : "
                    f"{r['cross_score']:.4f}"
                )

            print()

            print(
                r["text"][:500]
            )

            print()

