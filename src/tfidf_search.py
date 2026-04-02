import os
os.environ["FASTEMBED_CACHE_PATH"] = "./models"

import json
import joblib
import numpy as np
from scipy.sparse import load_npz
from sklearn.metrics.pairwise import cosine_similarity
from fastembed import TextEmbedding

from src.legal_reranker import rerank_results
from src.preprocessing import preprocess_text


############################################
# CONFIGURATION
############################################

CONFIG = {

    "clause": {
        "index_dir": "index",
        "legal_dir": "data/legal_units",

        "inverted_index": "inverted_index.json",
        "tfidf_matrix": "tfidf_matrix.npz",
        "unit_ids": "tfidf_unit_ids.json",
        "vectorizer": "tfidf_vectorizer.joblib",
        "embeddings": "embeddings.npy",
        "embedding_ids": "embedding_unit_ids.json"
    },

    "as": {
        "index_dir": "index_as",
        "legal_dir": "data/legal_units_as",

        "inverted_index": "inverted_index_as.json",
        "tfidf_matrix": "tfidf_matrix_as.npz",
        "unit_ids": "tfidf_unit_ids_as.json",
        "vectorizer": "tfidf_vectorizer_as.joblib",
        "embeddings": "embeddings_as.npy",
        "embedding_ids": "embedding_unit_ids_as.json"
    },

    "document": {
        "index_dir": "index_document",
        "legal_dir": "data/extracted_text",

        "inverted_index": "inverted_index_document.json",
        "tfidf_matrix": "tfidf_matrix_document.npz",
        "unit_ids": "tfidf_unit_ids_document.json",
        "vectorizer": "tfidf_vectorizer_document.joblib",
        "embeddings": "embeddings_document.npy",
        "embedding_ids": "embedding_unit_ids_document.json"
    }

}


############################################
# RESOURCE CACHE
############################################

RESOURCE_CACHE = {}

embedding_model = TextEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)


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
        "not liable": ["exempt", "exonerated", "exonéré", "non-assujetti"],
        "natural persons": ["individuals", "personnes physiques"],
        "election": ["poll", "voters", "scrutin", "électoral"],
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


############################################
# LOAD RESOURCES
############################################

def load_resources(granularity):

    if granularity in RESOURCE_CACHE:
        return RESOURCE_CACHE[granularity]

    config = CONFIG[granularity]

    index_dir = config["index_dir"]

    inverted_index_path = os.path.join(index_dir, config["inverted_index"])
    tfidf_matrix_path = os.path.join(index_dir, config["tfidf_matrix"])
    unit_ids_path = os.path.join(index_dir, config["unit_ids"])
    vectorizer_path = os.path.join(index_dir, config["vectorizer"])
    embeddings_path = os.path.join(index_dir, config["embeddings"])
    embedding_ids_path = os.path.join(index_dir, config["embedding_ids"])

    with open(inverted_index_path, "r", encoding="utf-8") as f:
        inverted_index = json.load(f)

    tfidf_matrix = load_npz(tfidf_matrix_path)

    with open(unit_ids_path, "r", encoding="utf-8") as f:
        unit_ids = json.load(f)

    vectorizer = joblib.load(vectorizer_path)

    embeddings = np.load(embeddings_path)

    with open(embedding_ids_path, "r", encoding="utf-8") as f:
        embedding_unit_ids = json.load(f)

    doc_id_to_idx = {doc_id: i for i, doc_id in enumerate(unit_ids)}

    RESOURCE_CACHE[granularity] = (
        inverted_index,
        tfidf_matrix,
        unit_ids,
        vectorizer,
        embeddings,
        embedding_unit_ids,
        doc_id_to_idx
    )

    return RESOURCE_CACHE[granularity]


############################################
# CANDIDATE RETRIEVAL
############################################

def get_candidate_indices(query_tokens, inverted_index, doc_id_to_idx):

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
# SEARCH FUNCTION
############################################

def search(query, top_k=20, use_rerank=False, granularity="clause"):

    if granularity not in CONFIG:
        raise ValueError(f"Invalid granularity: {granularity}")

    (
        inverted_index,
        tfidf_matrix,
        unit_ids,
        vectorizer,
        embeddings,
        embedding_unit_ids,
        doc_id_to_idx
    ) = load_resources(granularity)

    legal_dir = CONFIG[granularity]["legal_dir"]

    expanded_query = expand_query(query)
    processed_query = preprocess_query(expanded_query)

    query_tokens = processed_query.split()

    query_vector = vectorizer.transform([processed_query])
    query_embedding = list(embedding_model.embed([expanded_query]))[0]

    tfidf_scores_global = cosine_similarity(query_vector, tfidf_matrix)[0]

    candidate_indices = get_candidate_indices(query_tokens, inverted_index, doc_id_to_idx)

    if candidate_indices:

        candidate_indices = set(candidate_indices)

        fallback_indices = np.argsort(tfidf_scores_global)[::-1][:100]

        candidate_indices.update(fallback_indices)

        candidate_indices = list(candidate_indices)

    else:

        candidate_indices = np.argsort(tfidf_scores_global)[::-1][:100]

    tfidf_subset = tfidf_matrix[candidate_indices]
    embedding_subset = embeddings[candidate_indices]

    tfidf_scores = cosine_similarity(query_vector, tfidf_subset)[0]
    semantic_scores = cosine_similarity([query_embedding], embedding_subset)[0]

    scores = 0.6 * tfidf_scores + 0.4 * semantic_scores

    ranked = sorted(
        zip(candidate_indices, scores),
        key=lambda x: x[1],
        reverse=True
    )[:50]

    results = []

    for idx, score in ranked:

        if score == 0:
            continue

        unit_id = unit_ids[idx]

        text_path = os.path.join(legal_dir, unit_id)

        with open(text_path, "r", encoding="utf-8") as f:
            text = f.read()

        results.append({
            "unit_id": unit_id,
            "score": float(score),
            "text": text
        })

    if use_rerank:
        results = rerank_results(results, query=query)

    return results[:top_k]


############################################
# CLI MODE
############################################

if __name__ == "__main__":

    while True:

        query = input("\nEnter legal query (or 'exit'): ")

        if query.lower() == "exit":
            break

        granularity = input("Granularity (clause/as/document) [clause]: ")

        if granularity == "":
            granularity = "clause"

        results = search(query, top_k=5, use_rerank=True, granularity=granularity)

        print("\nTop Results:")

        for r in results:
            print("-" * 60)
            print(f"Unit: {r['unit_id']}")
            print(f"Score: {r['score']:.4f}")
            print(r["text"][:500])
            if "final_score" in r:
                print(f"Reranker score: {r['final_score']:.4f}")
            if "law_type" in r:
                print(f"Law type: {r['law_type']} | Unit type: {r['unit_type']}")



