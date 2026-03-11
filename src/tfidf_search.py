import os
import json
import joblib
from scipy.sparse import load_npz
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from fastembed import TextEmbedding
from src.legal_reranker import rerank_results
from src.preprocessing import preprocess_text


INDEX_DIR = "index"
LEGAL_UNIT_DIR = os.path.join("data", "legal_units")

TFIDF_MATRIX_PATH = os.path.join(INDEX_DIR, "tfidf_matrix.npz")
UNIT_IDS_PATH = os.path.join(INDEX_DIR, "tfidf_unit_ids.json")
VECTORIZER_PATH = os.path.join(INDEX_DIR, "tfidf_vectorizer.joblib")
EMBEDDINGS_PATH = os.path.join(INDEX_DIR, "embeddings.npy")
EMBEDDING_UNIT_IDS_PATH = os.path.join(INDEX_DIR, "embedding_unit_ids.json")


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


def load_resources():
    tfidf_matrix = load_npz(TFIDF_MATRIX_PATH)

    with open(UNIT_IDS_PATH, "r", encoding="utf-8") as f:
        unit_ids = json.load(f)

    vectorizer = joblib.load(VECTORIZER_PATH)

    return tfidf_matrix, unit_ids, vectorizer

def load_embedding_resources():
    embeddings = np.load(EMBEDDINGS_PATH)

    with open(EMBEDDING_UNIT_IDS_PATH, "r", encoding="utf-8") as f:
        embedding_unit_ids = json.load(f)

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    return embeddings, embedding_unit_ids, model    



tfidf_matrix, unit_ids, vectorizer = load_resources()
embeddings, embedding_unit_ids, embedding_model = load_embedding_resources()

def search(query, top_k=20, use_rerank=False):

    expanded_query = expand_query(query)
    processed_query = preprocess_query(expanded_query)

    query_vector = vectorizer.transform([processed_query])
    tfidf_scores = cosine_similarity(query_vector, tfidf_matrix)[0]
    query_embedding = list(embedding_model.embed([expanded_query]))[0]
    semantic_scores = cosine_similarity([query_embedding], embeddings)[0]
    scores = 0.6 * tfidf_scores + 0.4 * semantic_scores

    ranked_indices = scores.argsort()[::-1][:50]

    results = []
    for idx in ranked_indices:
        score = scores[idx]
        if score == 0:
            continue

        unit_id = unit_ids[idx]

        legal_text_path = os.path.join(LEGAL_UNIT_DIR, unit_id)
        with open(legal_text_path, "r", encoding="utf-8") as f:
            legal_text = f.read()

        results.append({
            "unit_id": unit_id,
            "score": float(score),
            "text": legal_text
        })

    if use_rerank:
        results = rerank_results(results, query=query)

    return results[:top_k]



if __name__ == "__main__":
    while True:
        query = input("\nEnter legal query (or 'exit'): ")
        if query.lower() == "exit":
            break

        results = search(query, top_k=5, use_rerank=True)

        print("\nTop Results:")
        for r in results:
            print("-" * 60)
            print(f"Unit: {r['unit_id']}")
            print(f"tf-idf score: {r['score']:.4f}")
            print(r['text'][:500], "...")
            print(f"reranker score: {r['final_score']:.4f}")
            print(f"Law type: {r['law_type']} | Unit type: {r['unit_type']}")


