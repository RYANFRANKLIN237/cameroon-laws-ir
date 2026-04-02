# import json
# import os
# from src.tfidf_search import search

# GROUND_TRUTH_PATH = os.path.join("data", "ground_truth", "ground_truth.json")
# GROUND_TRUTH_PATH_AS = os.path.join("data", "ground_truth", "ground_truth_as.json")
# GROUND_TRUTH_PATH_DOCUMENT = os.path.join("data", "ground_truth", "ground_truth_document.json")

# INVERTED_INDEX_PATH = os.path.join("index", "inverted_index.json")
# LEGAL_UNITS_PATH = os.path.join("data", "legal_units")




# def load_ground_truth():
#     with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
#         return json.load(f)

# def load_inverted_index():
#     with open(INVERTED_INDEX_PATH, "r", encoding="utf-8") as f:
#         return json.load(f)


# def diagnose():
#     ground_truth = load_ground_truth()
    
#     failures = []
    
#     for query, relevant_docs in ground_truth.items():
#         results = search(query, top_k=20, use_rerank=False)
#         retrieved = [r["unit_id"] for r in results]
        
#         # Find position of first relevant doc
#         first_position = None
#         for pos, doc_id in enumerate(retrieved, start=1):
#             if doc_id in relevant_docs:
#                 first_position = pos
#                 break
        
#         if first_position is None:
#             failures.append({
#                 "query": query,
#                 "relevant": relevant_docs,
#                 "retrieved_top5": retrieved[:5],
#                 "status": "NOT_FOUND"
#             })
#         elif first_position > 10:
#             failures.append({
#                 "query": query,
#                 "relevant": relevant_docs,
#                 "first_position": first_position,
#                 "retrieved_top5": retrieved[:5],
#                 "status": "RANK_TOO_LOW"
#             })
    
#     print(f"\n{'='*80}")
#     print(f"DIAGNOSTIC REPORT")
#     print(f"{'='*80}")
#     print(f"Total queries: {len(ground_truth)}")
#     print(f"Failures: {len(failures)}")
#     print(f"\n{'='*80}")
    
#     for i, failure in enumerate(failures[:10], 1):  # Show first 10 failures
#         print(f"\nFAILURE #{i}:")
#         print(f"Query: {failure['query']}")
#         print(f"Expected: {failure['relevant'][0]}")
#         print(f"Status: {failure['status']}")
#         if failure['status'] == 'RANK_TOO_LOW':
#             print(f"Found at position: {failure['first_position']}")
#         print(f"Top 5 retrieved:")
#         for j, doc in enumerate(failure['retrieved_top5'], 1):
#             print(f"  {j}. {doc}")

# def get_system_data() -> dict:

#     legal_corpus_size = len([
#         f for f in os.listdir(LEGAL_UNITS_PATH)
#         if f.endswith(".txt")
#     ])

   
#     inverted_index = load_inverted_index()
#     inverted_index_size = len(inverted_index)

   
#     ground_truth = load_ground_truth()
#     ground_truth_queries = len(ground_truth)

#     failed_count = 0
#     for query, relevant_docs in ground_truth.items():
#         results  = search(query, top_k=20, use_rerank=False)
#         retrieved = [r["unit_id"] for r in results]

#         first_position = None
#         for pos, doc_id in enumerate(retrieved, start=1):
#             if doc_id in relevant_docs:
#                 first_position = pos
#                 break

#         if first_position is None or first_position > 10:
#             failed_count += 1

#     return {
#         "legalCorpusSize":    legal_corpus_size,
#         "invertedIndexSize":  inverted_index_size,
#         "groundTruthQueries": ground_truth_queries,
#         "failedQueries":      failed_count,
#     }               

# if __name__ == "__main__":
#     diagnose()

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

def diagnose(granularity="clause"):

    ground_truth = load_ground_truth(granularity)

    failures = []

    for query, relevant_docs in ground_truth.items():

        results = search(
            query,
            top_k=20,
            use_rerank=False,
            granularity=granularity
        )

        retrieved = [r["unit_id"] for r in results]

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
    print(f"DIAGNOSTIC REPORT ({granularity})")
    print(f"{'='*80}")
    print(f"Total queries: {len(ground_truth)}")
    print(f"Failures: {len(failures)}")
    print(f"{'='*80}")

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

def count_failures(granularity="clause"):

    ground_truth = load_ground_truth(granularity)

    failed_count = 0

    for query, relevant_docs in ground_truth.items():

        results = search(
            query,
            top_k=20,
            use_rerank=False,
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

    failed_clause = count_failures("clause")
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
    diagnose("clause")

    print("\nAS diagnostics")
    diagnose("as")

    print("\nDocument diagnostics")
    diagnose("document")