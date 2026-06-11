import os
import re
from langdetect import detect, DetectorFactory
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from transformers import pipeline, AutoTokenizer, AutoModelForQuestionAnswering
import torch


load_dotenv()
DetectorFactory.seed = 0
translate_client = translate.Client()

translation_cache = {}

# Preload ground truth query translations if available
import os
import json
cache_file = os.path.join("data", "ground_truth", "query_translations.json")
if os.path.exists(cache_file):
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
            for q, t in cached_data.items():
                lang = detect(q)
                if lang == "fr":
                    translation_cache[(q.lower(), "fr", "en")] = t
                else:
                    translation_cache[(q.lower(), "en", "fr")] = t
    except Exception as e:
        print(f"Failed to load translation cache: {e}")

MODEL_NAME = "deepset/xlm-roberta-base-squad2"

print(f"[INFO] Loading {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
base_model = AutoModelForQuestionAnswering.from_pretrained(MODEL_NAME)

# 1. CRITICAL: Force the model to CPU and set to evaluation mode FIRST
base_model.to(torch.device("cpu"))
base_model.eval()

# 2. Apply Dynamic Quantization safely
print("[INFO] Quantizing linear layers to INT8...")
# quantized_model = torch.quantization.quantize_dynamic(
#     base_model,
#     {torch.nn.Linear},
#     dtype=torch.qint8
# )
torch.backends.quantized.engine = 'qnnpack'

# 2. Your existing quantization block (Line 28)
quantized_model = torch.quantization.quantize_dynamic(
    base_model,
    {torch.nn.Linear},
    dtype=torch.qint8
)

# 3. Initialize pipeline explicitly declaring the CPU device to prevent internal pipeline crashes
qa_pipeline = pipeline(
    "question-answering",
    model=quantized_model,
    tokenizer=tokenizer,
    device=-1  # Explicitly forces Hugging Face to treat this as a pure CPU workload
)

# qa_pipeline = pipeline(
#     "question-answering",
#     model="deepset/xlm-roberta-base-squad2",
#     tokenizer="deepset/xlm-roberta-base-squad2" 
# )

def normalize_filename(name):
    if not name:
        return ""
    
    name = name.lower().strip()
    
    if name.endswith(".pdf"):
        name = name[:-4]
        
    return re.sub(r'[^a-z0-9]', '', name)

def get_pdf_mapping(pdf_dir):
    pdf_map = {}
    if not os.path.exists(pdf_dir):
        print(f"⚠️ Warning: {pdf_dir} does not exist.")
        return pdf_map
        
    for filename in os.listdir(pdf_dir):
        if filename.lower().endswith(".pdf"):
            norm_name = normalize_filename(filename)
            pdf_map[norm_name] = filename
            
    return pdf_map

############################################
# TRANSLATION
############################################      

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "fr" if lang == "fr" else "en"
    except:
        return "en"  


def translate_text(text, source, target):

    if source == target:
        return text

    key = (text.lower(), source, target)

    if key in translation_cache:
        return translation_cache[key]

    result = translate_client.translate(
        text,
        source_language=source,
        target_language=target
    )

    translated = result["translatedText"]

    translation_cache[key] = translated

    return translated

############################################
# QA
############################################      

def extract_answer(question: str, context: str):
    if not context or not question:
        return ""

    try:
        result = qa_pipeline(
            question=question,
            context=context,
            max_seq_len=512,
            doc_stride=128, 
            handle_impossible_answer=True
        )

        answer = result.get("answer", "").strip()
        score = result.get("score", 0)

        if score < 0.1 or len(answer) < 2:
            return ""

        return answer.replace(" ", " ").strip()

    except Exception as e:
        print(f"QA Error: {e}")
        return ""  

############################################
# PARSING
############################################      

def parse_unit_id(unit_id: str) -> dict:
    name = unit_id.removesuffix(".txt")

    parts = re.split(r'_(section|article)_', name, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) == 3:
        raw_source   = parts[0]   # everything before _section_ or _article_
        unit_keyword = parts[1]   # "section" or "article"
        rest         = parts[2]   # e.g. "1_clause_3" or "69_clause_full"
    else:
        return {
            "source": name.replace("_ ", " ").replace("_", " ").strip(),
            "title":  name.replace("_ ", " ").replace("_", " ").strip(),
        }

    source = raw_source.replace("_ ", " ").replace("_", " ").strip()
    rest_parts = rest.split("_")  

    unit_number  = rest_parts[0]                       
    clause_value = rest_parts[2] if len(rest_parts) >= 3 else "full" 

    base_title = f"{unit_keyword.capitalize()} {unit_number}"  

    if clause_value.lower() == "full":
        title = base_title
    else:
        title = f"{base_title} Sub {clause_value}"

    return {"source": source, "title": title}  
    
def transform_result(raw: dict, rank: int,query: str) -> dict:
    """
    Converts a raw result from tfidf_search.search() into the display
    format expected by the UI.

    raw dict keys: unit_id, score, text, (optionally) final_score, law_type, unit_type
    """
    parsed = parse_unit_id(raw["unit_id"])
    text = raw["text"].strip()
    lang = detect_language(text[:300])
    highlight = extract_answer(query, text)

    return {
        "id":          rank,
        "rank":        rank,
        "title":       parsed["title"],
        "content":     text,
        "highlight":   highlight,
        "source":      parsed["source"],
        "language":    lang,
        "translation": "",
        "isTranslating": False,
        "tfidf_score":   round(raw.get("score", 0), 4),
        "rerank_score":  round(raw.get("final_score", 0), 4),
        "law_type":      raw.get("law_type", ""),
        "unit_type":     raw.get("unit_type", "")
    }          



############################################
# CONFIGURATION
############################################  

CONFIG = {

    "clause": {

        "index_dir": "index",
        "legal_dir": "data/legal_units",

        "inverted_index_en": "inverted_index_en.json",
        "inverted_index_fr": "inverted_index_fr.json",

        "tfidf_matrix_en": "tfidf_matrix_en.npz",
        "tfidf_matrix_fr": "tfidf_matrix_fr.npz",

        "unit_ids_en": "tfidf_unit_ids_en.json",
        "unit_ids_fr": "tfidf_unit_ids_fr.json",

        "vectorizer_en": "tfidf_vectorizer_en.joblib",
        "vectorizer_fr": "tfidf_vectorizer_fr.joblib",

        "embeddings_en": "embeddings_en.npy",
        "embeddings_fr": "embeddings_fr.npy",

        "embedding_ids_en": "embedding_unit_ids_en.json",
        "embedding_ids_fr": "embedding_unit_ids_fr.json"
    },

    "as": {

        "index_dir": "index_as",
        "legal_dir": "data/legal_units_as",

        "inverted_index_en": "inverted_index_as_en.json",
        "inverted_index_fr": "inverted_index_as_fr.json",

        "tfidf_matrix_en": "tfidf_matrix_as_en.npz",
        "tfidf_matrix_fr": "tfidf_matrix_as_fr.npz",

        "unit_ids_en": "tfidf_unit_ids_as_en.json",
        "unit_ids_fr": "tfidf_unit_ids_as_fr.json",

        "vectorizer_en": "tfidf_vectorizer_as_en.joblib",
        "vectorizer_fr": "tfidf_vectorizer_as_fr.joblib",

        "embeddings_en": "embeddings_as_en.npy",
        "embeddings_fr": "embeddings_as_fr.npy",

        "embedding_ids_en": "embedding_unit_ids_as_en.json",
        "embedding_ids_fr": "embedding_unit_ids_as_fr.json"
    },

    "document": {

        "index_dir": "index_document",
        "legal_dir": "data/extracted_text",

        "inverted_index_en": "inverted_index_document_en.json",
        "inverted_index_fr": "inverted_index_document_fr.json",

        "tfidf_matrix_en": "tfidf_matrix_document_en.npz",
        "tfidf_matrix_fr": "tfidf_matrix_document_fr.npz",

        "unit_ids_en": "tfidf_unit_ids_document_en.json",
        "unit_ids_fr": "tfidf_unit_ids_document_fr.json",

        "vectorizer_en": "tfidf_vectorizer_document_en.joblib",
        "vectorizer_fr": "tfidf_vectorizer_document_fr.joblib",

        "embeddings_en": "embeddings_document_en.npy",
        "embeddings_fr": "embeddings_document_fr.npy",

        "embedding_ids_en": "embedding_unit_ids_document_en.json",
        "embedding_ids_fr": "embedding_unit_ids_document_fr.json"
    }

}
