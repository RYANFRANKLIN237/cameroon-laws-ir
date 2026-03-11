import json
import os
from statistics import mean
from src.tfidf_search import search

GROUND_TRUTH_PATH = os.path.join("data", "ground_truth", "ground_truth.json")


def load_ground_truth():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
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


def evaluate(use_rerank):
    ground_truth = load_ground_truth()

    p3_scores = []
    p5_scores = []
    r10_scores = []
    mrr_scores = []

    for query, relevant_docs in ground_truth.items():
        results = search(query, top_k=20, use_rerank=use_rerank)

        retrieved_docs = [r["unit_id"] for r in results]

        p3_scores.append(precision_at_k(retrieved_docs, relevant_docs, 3))
        p5_scores.append(precision_at_k(retrieved_docs, relevant_docs, 5))
        r10_scores.append(recall_at_k(retrieved_docs, relevant_docs, 10))
        mrr_scores.append(reciprocal_rank(retrieved_docs, relevant_docs))

    scores = {
        "precisionAt3": round(mean(p3_scores),  3),
        "precisionAt5": round(mean(p5_scores),  3),
        "recallAt10":   round(mean(r10_scores), 3),
        "mrr":          round(mean(mrr_scores), 3),
    }    

       
    print("\n==============================")
    print("Rerank:", use_rerank)
    print("==============================")
    print(f"Mean Precision@3:  {mean(p3_scores):.3f}")
    print(f"Mean Precision@5:  {mean(p5_scores):.3f}")
    print(f"Mean Recall@10:    {mean(r10_scores):.3f}")
    print(f"Mean MRR:          {mean(mrr_scores):.3f}")

    return scores


def get_metrics() -> dict:

    baseline = evaluate(use_rerank=False)
    ranked   = evaluate(use_rerank=True)

    return {"baseline": baseline, "ranked": ranked}



if __name__ == "__main__":
    print("Evaluating TF-IDF baseline...")
    evaluate(use_rerank=False)

    print("\nEvaluating Legal-aware reranking...")
    evaluate(use_rerank=True)