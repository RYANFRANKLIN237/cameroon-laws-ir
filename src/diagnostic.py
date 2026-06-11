import json
import os

# Updated to use your cascading multilingual pipeline
from src.tfidf_search import search
from src.utils import CONFIG

############################################
# GROUND TRUTH
############################################

GROUND_TRUTH = {
    "clause": os.path.join("ground_truth", "ground_truth.json"),
    "as": os.path.join("ground_truth", "ground_truth_as.json"),
    "document": os.path.join("ground_truth", "ground_truth_document.json")
}

############################################
# LOADERS
############################################

def load_ground_truth(granularity="clause"):
    path = GROUND_TRUTH[granularity]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_inverted_index_size(granularity="clause"):
    index_dir = CONFIG[granularity]["index_dir"]
    with open(os.path.join(index_dir, CONFIG[granularity]["inverted_index_en"]), "r", encoding="utf-8") as f:
        en_index = json.load(f)
    with open(os.path.join(index_dir, CONFIG[granularity]["inverted_index_fr"]), "r", encoding="utf-8") as f:
        fr_index = json.load(f)
    return len(en_index) + len(fr_index)


############################################
# DIAGNOSTIC
############################################

def diagnose(granularity="clause", use_rerank=False):
    ground_truth = load_ground_truth(granularity)
    failures = []
    precision_failures = 0
    top5_misses = 0

    for query, relevant_docs in ground_truth.items():
        # Call the multilingual engine
        search_output = search(
            query=query,
            top_k=20,
            use_rerank=use_rerank,
            granularity=granularity
        )
        
        # Isolate the final cross-encoder ranked results
        results = search_output["final_results"]

        retrieved = [r["unit_id"] for r in results]

        # ----------------------------------
        # Precision diagnostics
        # ----------------------------------
        if not any(doc in relevant_docs for doc in retrieved[:3]):
            precision_failures += 1

        if not any(doc in relevant_docs for doc in retrieved[:5]):
            top5_misses += 1

        # ----------------------------------
        # Existing failure logic
        # ----------------------------------
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

    # ----------------------------------
    # REPORT
    # ----------------------------------
    print(f"\n{'=' * 80}")
    print(f"MULTILINGUAL DIAGNOSTIC REPORT ({granularity})")
    print(f"{'=' * 80}")
    print(f"Total queries: {len(ground_truth)}")
    print(f"Failures (out of top 10): {len(failures)}")
    print(f"Precision Failures (no hit in top 3): {precision_failures}")
    print(f"Top-5 Misses (no hit in top 5): {top5_misses}")
    print(f"{'=' * 80}")

    # ----------------------------------
    # SAMPLE FAILURES
    # ----------------------------------
    for i, failure in enumerate(failures[:10], 1):
        print(f"\nFAILURE #{i}")
        print(f"Query: {failure['query']}")
        print(f"Expected: {failure['relevant'][0]}")
        print(f"Status: {failure['status']}")
        if failure["status"] == "RANK_TOO_LOW":
            print(f"Found at position: {failure['first_position']}")
        print("Top 5 retrieved:")
        for j, doc in enumerate(failure["retrieved_top5"], 1):
            print(f"  {j}. {doc}")

    return failures


############################################
# SYSTEM DATA (API)
############################################

def get_system_data():
    clause_units_path = CONFIG["clause"]["legal_dir"]
    legal_corpus_size = len([
        f for f in os.listdir(clause_units_path) if f.endswith(".txt")
    ])

    inverted_index_size = get_inverted_index_size("clause")
    ground_truth = load_ground_truth("clause")
    ground_truth_queries = len(ground_truth)

    return {
        "legalCorpusSize": legal_corpus_size,
        "invertedIndexSize": inverted_index_size,
        "groundTruthQueries": ground_truth_queries
    }


############################################
# CLI
############################################

if __name__ == "__main__":
    print("\nRunning Cross-Lingual Pipeline Diagnostics...")
    diagnose(granularity="clause", use_rerank=True)