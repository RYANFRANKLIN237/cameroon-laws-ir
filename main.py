import re
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from src.evaluation import get_metrics
from src.diagnostic import get_system_data
from src.tfidf_search import search as tfidf_search
from src.utils import get_pdf_mapping, normalize_filename

app = Flask(__name__)

PDF_STORAGE_PATH = os.path.join(os.getcwd(), "data", "raw_pdfs")
PDF_FILE_MAP = get_pdf_mapping(PDF_STORAGE_PATH)

# ─── Result Transformer ───────────────────────────────────────────────────────

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


def transform_result(raw: dict, rank: int) -> dict:
    """
    Converts a raw result from tfidf_search.search() into the display
    format expected by the UI.

    raw dict keys: unit_id, score, text, (optionally) final_score, law_type, unit_type
    """
    parsed = parse_unit_id(raw["unit_id"])

    return {
        "id":          rank,
        "rank":        rank,
        "title":       parsed["title"],
        "content":     raw["text"].strip(),
        "source":      parsed["source"],
        "language":    "en",    
        "translation": "",
        "tfidf_score":   round(raw.get("score", 0), 4),
        "rerank_score":  round(raw.get("final_score", 0), 4),
        "law_type":      raw.get("law_type", ""),
        "unit_type":     raw.get("unit_type", ""),
    }

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def onboarding():
    # This serves the onboarding screen first
    return render_template('onboarding.html')

@app.route('/search')
def search_home():
   return render_template('search.html')

@app.route('/metrics')
def metrics():
    return render_template('metrics.html')



@app.route('/api/search')
def api_search():
    """
    GET /api/search?q=<query>

    Calls tfidf_search.search() with reranking enabled,
    then transforms raw results into UI-ready display objects.
    """
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({"results": [], "total": 0, "query": query})

    try:
        raw_results = tfidf_search(query, top_k=10, use_rerank=True)
    except Exception as e:
        app.logger.error(f"Search failed for query '{query}': {e}")
        return jsonify({"results": [], "total": 0, "query": query, "error": str(e)})

    display_results = [
        transform_result(raw, rank=i + 1)
        for i, raw in enumerate(raw_results)
    ]

    return jsonify({
        "results": display_results,
        "total":   len(display_results),
        "query":   query,
    })

@app.route('/api/metrics')
def api_metrics():
    """
    Assembles data from all evaluation modules into one JSON response.
    To swap in real data later, edit only the individual module files:
      evaluation.py  -> baseline + ranked metrics
      diagnostics.py -> system data (corpus size, index, ground truth, failures)
    """
    metrics_data = get_metrics()
    system_data  = get_system_data()
    return jsonify({
        "baseline":   metrics_data["baseline"],
        "ranked":     metrics_data["ranked"],
        "systemData": system_data,
    })   

@app.route('/view-pdf/<path:source_name>')
def serve_legal_pdf(source_name):
    """
    Resolves the source name to the actual PDF filename using fuzzy matching.
    """
    # 1. Try to find an exact match first
    # 2. If not found, normalize the requested name and look in our map
    norm_request = normalize_filename(source_name)
    actual_filename = PDF_FILE_MAP.get(norm_request)

    if actual_filename:
        return send_from_directory(PDF_STORAGE_PATH, actual_filename)
    
    # Fallback/Debug if it still fails
    app.logger.error(f"Mapping failed for: {source_name} (Normalized: {norm_request})")
    return jsonify({
        "error": f"PDF not found",
        "details": f"Could not match '{source_name}' to any file in storage."
    }), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)