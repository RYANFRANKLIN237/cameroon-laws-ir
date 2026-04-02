import json
import os
from statistics import mean

from src.tfidf_search import search



GROUND_TRUTH_FILES = {
    "clause": os.path.join("data", "ground_truth", "ground_truth.json"),
    "as": os.path.join("data", "ground_truth", "ground_truth_as.json"),
    "document": os.path.join("data", "ground_truth", "ground_truth_document.json")
}




def load_ground_truth(granularity="clause"):

    path = GROUND_TRUTH_FILES[granularity]

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)




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




def evaluate(use_rerank=False, granularity="clause"):

    ground_truth = load_ground_truth(granularity)

    p3_scores = []
    p5_scores = []
    r10_scores = []
    mrr_scores = []

    for query, relevant_docs in ground_truth.items():

        results = search(
            query,
            top_k=20,
            use_rerank=use_rerank,
            granularity=granularity
        )

        retrieved_docs = [r["unit_id"] for r in results]

        p3_scores.append(precision_at_k(retrieved_docs, relevant_docs, 3))
        p5_scores.append(precision_at_k(retrieved_docs, relevant_docs, 5))
        r10_scores.append(recall_at_k(retrieved_docs, relevant_docs, 10))
        mrr_scores.append(reciprocal_rank(retrieved_docs, relevant_docs))

    scores = {
        "precisionAt3": round(mean(p3_scores), 3),
        "precisionAt5": round(mean(p5_scores), 3),
        "recallAt10": round(mean(r10_scores), 3),
        "mrr": round(mean(mrr_scores), 3),
    }

    print("\n==============================")
    print(f"Granularity: {granularity}")
    print(f"Rerank: {use_rerank}")
    print("==============================")
    print(f"Mean Precision@3: {scores['precisionAt3']:.3f}")
    print(f"Mean Precision@5: {scores['precisionAt5']:.3f}")
    print(f"Mean Recall@10:   {scores['recallAt10']:.3f}")
    print(f"Mean MRR:         {scores['mrr']:.3f}")

    return scores


############################################
# METRICS API
############################################

def get_metrics(mode="clause") -> dict:

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

        clause_scores = evaluate(use_rerank=False, granularity="clause")
        as_scores = evaluate(use_rerank=False, granularity="as")
        document_scores = evaluate(use_rerank=False, granularity="document")

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