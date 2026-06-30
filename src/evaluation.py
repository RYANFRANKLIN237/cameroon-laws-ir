import json
import os
from time import perf_counter
from statistics import mean

from src.tfidf_search import search



GROUND_TRUTH_FILES = {
    "clause": os.path.join("ground_truth", "ground_truth.json"),
    "as": os.path.join("ground_truth", "ground_truth_as.json"),
    "document": os.path.join("ground_truth", "ground_truth_document.json")
}




def load_ground_truth(granularity="clause"):

    path = GROUND_TRUTH_FILES[granularity]

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hit_at_k(retrieved, relevant, k):
    """
    Returns 1 if at least one relevant doc is in top-k, else 0
    """
    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)

    return 1 if any(doc in relevant_set for doc in retrieved_k) else 0

def precision_at_k(retrieved, relevant, k):

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)

    hits = sum(1 for doc in retrieved_k if doc in relevant_set)

    return hits / k


def recall_at_k(retrieved, relevant, k):

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)

    hits = sum(1 for doc in retrieved_k if doc in relevant_set)

    return hits / len(relevant_set) if relevant_set else 0


def reciprocal_rank(retrieved, relevant):

    relevant_set = set(relevant)

    for idx, doc in enumerate(retrieved, start=1):
        if doc in relevant_set:
            return 1 / idx

    return 0

def avg_result_length(results):
    """Average word count of the 'text' field of returned results."""
    if not results:
        return 0
    lengths = [len(r.get("text", "").split()) for r in results]
    return round(mean(lengths), 1)    


def latency_per_granularity(rows):
    """Summarize latency rows by granularity and rerank setting."""
    latency_rows = []
    for row in rows:
        latency_rows.append({
            "granularity": row["granularity"],
            "rerank": row["rerank"],
            "avg_latency_seconds": row["avg_latency_seconds"],
            "min_latency_seconds": row["min_latency_seconds"],
            "max_latency_seconds": row["max_latency_seconds"],
            "query_count": row["query_count"],
        })

    return latency_rows




def evaluate(use_rerank=False, granularity="clause", verbose=True):

    ground_truth = load_ground_truth(granularity)

    hit3_scores = []
    p3_scores = []
    r10_scores = []
    mrr_scores = []
    failed_count = 0
    length_scores = []
    latency_scores = []

    for query, relevant_docs in ground_truth.items():

        start_time = perf_counter()
        result_dict = search(
            query,
            top_k=20,
            use_rerank=use_rerank,
            granularity=granularity
        )
        latency_scores.append(perf_counter() - start_time)

        final_results = result_dict["final_results"]
        retrieved_docs = [r["unit_id"] for r in final_results]

        hit3_scores.append(hit_at_k(retrieved_docs, relevant_docs, 3))
        p3_scores.append(precision_at_k(retrieved_docs, relevant_docs, 3))
        r10_scores.append(recall_at_k(retrieved_docs, relevant_docs, 10))
        mrr_scores.append(reciprocal_rank(retrieved_docs, relevant_docs))
        length_scores.append(avg_result_length(final_results))

        first_pos = None
        for pos, doc_id in enumerate(retrieved_docs, start=1):
            if doc_id in relevant_docs:
                first_pos = pos
                break
        if first_pos is None or first_pos > 10:
            failed_count += 1

    scores = {
        "hitAt3": round(mean(hit3_scores), 3),
        "precisionAt3": round(mean(p3_scores), 3),
        "recallAt10": round(mean(r10_scores), 3),
        "mrr": round(mean(mrr_scores), 3),
        "failures": failed_count,
        "avg_result_length": round(mean(length_scores), 1) if length_scores else 0,
        "avg_latency_seconds": round(mean(latency_scores), 4) if latency_scores else 0,
        "min_latency_seconds": round(min(latency_scores), 4) if latency_scores else 0,
        "max_latency_seconds": round(max(latency_scores), 4) if latency_scores else 0,
        "query_count": len(latency_scores),
    }

    if verbose:
        print("\n==============================")
        print(f"Granularity: {granularity}")
        print(f"Rerank: {use_rerank}")
        print("==============================")
        print(f"Hit@3:           {scores['hitAt3']:.3f}")
        print(f"MRR:             {scores['mrr']:.3f}")
        print(f"Precision@3:     {scores['precisionAt3']:.3f}")
        print(f"Recall@10:       {scores['recallAt10']:.3f}")
        print(f"Failures:        {scores['failures']}")
        print(f"Avg. length:     {scores['avg_result_length']} words")
        print(f"Avg. latency:    {scores['avg_latency_seconds']:.4f} seconds")


    return scores


############################################
# METRICS API
############################################

def get_metrics(mode="clause", clause_ranked_scores=None) -> dict:

    # DEFAULT → clause baseline + rerank
    if mode == "clause":

        baseline = evaluate(use_rerank=False, granularity="clause")
        ranked = evaluate(use_rerank=True, granularity="clause")

        return {
            "baseline": baseline,
            "ranked": ranked
        }

    # COMPARISON TABLE MODE
    elif mode == "all":

        clause_scores = clause_ranked_scores or evaluate(use_rerank=True, granularity="clause")
        as_scores = evaluate(use_rerank=True, granularity="as")
        document_scores = evaluate(use_rerank=True, granularity="document")

        return {
            "clause": clause_scores,
            "as": as_scores,
            "document": document_scores
        }

    else:
        raise ValueError("mode must be 'clause' or 'all'")


if __name__ == "__main__":

    print("Evaluating Clause Baseline...")
    evaluate(use_rerank=False, granularity="clause")

    print("\nEvaluating Clause Reranked...")
    evaluate(use_rerank=True, granularity="clause")

    print("\nEvaluating AS Baseline...")
    evaluate(use_rerank=False, granularity="as")

    print("\nEvaluating Document Baseline...")
    evaluate(use_rerank=False, granularity="document")
