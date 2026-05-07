import json
import os
from src.tfidf_search import search


############################################
# CONFIG
############################################

CONFIG = {

    "clause": {
        "ground_truth": os.path.join("data", "ground_truth", "ground_truth.json"),
        "inverted_index": os.path.join("index", "inverted_index.json"),
        "legal_units": os.path.join("data", "legal_units")
    },

    "as": {
        "ground_truth": os.path.join("data", "ground_truth", "ground_truth_as.json"),
        "inverted_index": os.path.join("index_as", "inverted_index_as.json"),
        "legal_units": os.path.join("data", "legal_units_as")
    },

    "document": {
        "ground_truth": os.path.join("data", "ground_truth", "ground_truth_document.json"),
        "inverted_index": os.path.join("index_document", "inverted_index_document.json"),
        "legal_units": os.path.join("data", "extracted_text")
    }

}


############################################
# LOADERS
############################################

def load_ground_truth(granularity="clause"):

    path = CONFIG[granularity]["ground_truth"]

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_inverted_index(granularity="clause"):

    path = CONFIG[granularity]["inverted_index"]

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


############################################
# DIAGNOSTIC
############################################


def diagnose(granularity="clause", use_rerank=False):

    ground_truth = load_ground_truth(granularity)

    failures = []

    precision_failures = 0   # ❌ no relevant doc in top 3
    top5_misses = 0          # ❌ no relevant doc in top 5

    for query, relevant_docs in ground_truth.items():

        results = search(
            query,
            top_k=20,
            use_rerank=use_rerank,
            granularity=granularity
        )

        retrieved = [r["unit_id"] for r in results]

        # -----------------------------
        # 🔥 Precision diagnostics
        # -----------------------------
        if not any(doc in relevant_docs for doc in retrieved[:3]):
            precision_failures += 1

        if not any(doc in relevant_docs for doc in retrieved[:5]):
            top5_misses += 1

        # -----------------------------
        # Existing failure logic
        # -----------------------------
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

    # -----------------------------
    # REPORT
    # -----------------------------
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC REPORT ({granularity})")
    print(f"{'='*80}")
    print(f"Total queries: {len(ground_truth)}")
    print(f"Failures (out of top 10): {len(failures)}")
    print(f"Precision Failures (no hit in top 3): {precision_failures}")
    print(f"Top-5 Misses (no hit in top 5): {top5_misses}")
    print(f"{'='*80}")

    # -----------------------------
    # SAMPLE FAILURES
    # -----------------------------
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
# FAILURE COUNT (used by API)
############################################

def count_failures(granularity="clause", use_rerank=False):

    ground_truth = load_ground_truth(granularity)

    failed_count = 0

    for query, relevant_docs in ground_truth.items():

        results = search(
            query,
            top_k=20,
            use_rerank=use_rerank,
            granularity=granularity
        )

        retrieved = [r["unit_id"] for r in results]

        first_position = None

        for pos, doc_id in enumerate(retrieved, start=1):

            if doc_id in relevant_docs:
                first_position = pos
                break

        if first_position is None or first_position > 10:
            failed_count += 1

    return failed_count


############################################
# SYSTEM DATA (API)
############################################

def get_system_data() -> dict:

    clause_units_path = CONFIG["clause"]["legal_units"]
    legal_corpus_size = len([
        f for f in os.listdir(clause_units_path)
        if f.endswith(".txt")
    ])

    inverted_index = load_inverted_index()
    inverted_index_size = len(inverted_index)

    ground_truth = load_ground_truth()
    ground_truth_queries = len(ground_truth)

    failed_clause = count_failures("clause",True)
    failed_as = count_failures("as")
    failed_document = count_failures("document")

    return {
        "legalCorpusSize": legal_corpus_size,
        "invertedIndexSize": inverted_index_size,
        "groundTruthQueries": ground_truth_queries,

        "failedQueries": failed_clause,
        "failedQueries_as": failed_as,
        "failedQueries_document": failed_document
    }


############################################
# CLI
############################################

if __name__ == "__main__":

    print("Clause diagnostics")
    diagnose("clause",True)

    print("\nAS diagnostics")
    diagnose("as")

    print("\nDocument diagnostics")
    diagnose("document")