import os
import re
from langdetect import detect, DetectorFactory
from transformers import pipeline

DetectorFactory.seed = 0

qa_pipeline = pipeline(
    "question-answering",
    model="deepset/xlm-roberta-base-squad2",
    tokenizer="deepset/xlm-roberta-base-squad2" 
)

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

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "fr" if lang == "fr" else "en"
    except:
        return "en"  

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
