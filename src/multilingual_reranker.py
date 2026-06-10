# import torch
# from transformers import AutoModelForSequenceClassification, AutoTokenizer

# # Global Initialization (Executes once when the module is imported)
# MODEL_NAME = "BAAI/bge-reranker-v2-m3"

# print(f"[INFO] Initializing {MODEL_NAME} natively on CPU...")
# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# model = torch.quantization.quantize_dynamic(
#     model,
#     {torch.nn.Linear},
#     dtype=torch.qint8
# )

# # Force the model onto CPU explicitly
# device = torch.device("cpu")
# model.to(device)
# model.eval()

# def multilingual_cross_rerank(query: str, results: list, top_k: int = 10):
#     """
#     Cross-encoder reranking using native Hugging Face transformers.
#     Maintains complete backward compatibility with the existing tfidf_search pipeline.
    
#     Parameters:
#     - query: The absolute mathematical anchor query (Original user query)
#     - results: Combined pool of documents from primary and secondary pipelines
#     - top_k: Number of final sorted results to return
#     """
#     if not results:
#         return []

#     # 1. Format data into BGE Cross-Encoder text pairs
#     # Format: [[query, doc1_text], [query, doc2_text], ...]
#     pairs = [[query, r["text"]] for r in results]

#     # 2. Execute native tokenization and inference on CPU
#     with torch.no_grad():
#         inputs = tokenizer(
#             pairs,
#             padding=True,
#             truncation=True,
#             max_length=512,  
#             return_tensors="pt"
#         ).to(device)
        
#         # Extract raw relevance scores (logits) from the classification head
#         logits = model(**inputs).logits.view(-1)
#         scores = logits.cpu().tolist()

#     # 3. Map scores back to original metadata dictionaries
#     final_results = []
#     for idx, r in enumerate(results):
#         result = r.copy()
#         result["cross_score"] = float(scores[idx])
#         final_results.append(result)

#     # 4. Sort descending by the cross-encoder relevance score
#     final_results.sort(key=lambda x: x["cross_score"], reverse=True)

#     return final_results[:top_k]

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = "BAAI/bge-reranker-v2-m3"

print(f"[INFO] Loading {MODEL_NAME} weights...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
raw_model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# 1. Force raw model to CPU and set to evaluation mode FIRST
raw_model.to(torch.device("cpu"))
raw_model.eval()

# 2. Apply Dynamic Quantization safely to the Linear layers
print("[INFO] Quantizing model weights from Float32 to Int8 for CPU speed...")
model = torch.quantization.quantize_dynamic(
    raw_model,
    {torch.nn.Linear},
    dtype=torch.qint8
)

def multilingual_cross_rerank(query: str, results: list, top_k: int = 10):
    """Cross-encoder reranking using optimized INT8 dynamic quantization."""
    if not results:
        return []

    pairs = [[query, r["text"]] for r in results]

    with torch.no_grad():
        inputs = tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=512, 
            return_tensors="pt"
        )
        
        # Run inference through the quantized model
        logits = model(**inputs).logits.view(-1)
        scores = logits.tolist()

    final_results = []
    for idx, r in enumerate(results):
        result = r.copy()
        result["cross_score"] = float(scores[idx])
        final_results.append(result)

    final_results.sort(key=lambda x: x["cross_score"], reverse=True)
    return final_results[:top_k]