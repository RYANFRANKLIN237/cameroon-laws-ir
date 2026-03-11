import json
import os
from src.tfidf_search import search

GROUND_TRUTH_PATH = os.path.join("data", "ground_truth", "ground_truth.json")
INVERTED_INDEX_PATH = os.path.join("index", "inverted_index.json")
LEGAL_UNITS_PATH = os.path.join("data", "legal_units")




def load_ground_truth():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_inverted_index():
    with open(INVERTED_INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def diagnose():
    ground_truth = load_ground_truth()
    
    failures = []
    
    for query, relevant_docs in ground_truth.items():
        results = search(query, top_k=20, use_rerank=False)
        retrieved = [r["unit_id"] for r in results]
        
        # Find position of first relevant doc
        first_position = None
        for pos, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant_docs:
                first_position = pos
                break
        
        if first_position is None:
            failures.append({
                "query": query,
                "relevant": relevant_docs,
                "retrieved_top5": retrieved[:5],
                "status": "NOT_FOUND"
            })
        elif first_position > 10:
            failures.append({
                "query": query,
                "relevant": relevant_docs,
                "first_position": first_position,
                "retrieved_top5": retrieved[:5],
                "status": "RANK_TOO_LOW"
            })
    
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC REPORT")
    print(f"{'='*80}")
    print(f"Total queries: {len(ground_truth)}")
    print(f"Failures: {len(failures)}")
    print(f"\n{'='*80}")
    
    for i, failure in enumerate(failures[:10], 1):  # Show first 10 failures
        print(f"\nFAILURE #{i}:")
        print(f"Query: {failure['query']}")
        print(f"Expected: {failure['relevant'][0]}")
        print(f"Status: {failure['status']}")
        if failure['status'] == 'RANK_TOO_LOW':
            print(f"Found at position: {failure['first_position']}")
        print(f"Top 5 retrieved:")
        for j, doc in enumerate(failure['retrieved_top5'], 1):
            print(f"  {j}. {doc}")

def get_system_data() -> dict:

    legal_corpus_size = len([
        f for f in os.listdir(LEGAL_UNITS_PATH)
        if f.endswith(".txt")
    ])

   
    inverted_index = load_inverted_index()
    inverted_index_size = len(inverted_index)

   
    ground_truth = load_ground_truth()
    ground_truth_queries = len(ground_truth)

    failed_count = 0
    for query, relevant_docs in ground_truth.items():
        results  = search(query, top_k=20, use_rerank=False)
        retrieved = [r["unit_id"] for r in results]

        first_position = None
        for pos, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant_docs:
                first_position = pos
                break

        if first_position is None or first_position > 10:
            failed_count += 1

    return {
        "legalCorpusSize":    legal_corpus_size,
        "invertedIndexSize":  inverted_index_size,
        "groundTruthQueries": ground_truth_queries,
        "failedQueries":      failed_count,
    }               

if __name__ == "__main__":
    diagnose()