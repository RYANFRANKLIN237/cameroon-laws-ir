from flask import Blueprint, request, jsonify, current_app
from src.evaluation import get_metrics
from src.diagnostic import get_system_data
from src.tfidf_search import search as tfidf_search
from src.utils import transform_result
from app import translate_client, pdf_file_map, pdf_storage_path  

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Cache for translations (could be moved to a dedicated module)
translation_cache = {}

@api_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": [], "total": 0, "query": query})

    try:
        raw_results = tfidf_search(query, top_k=10, use_rerank=True)
    except Exception as e:
        current_app.logger.error(f"Search failed: {e}")
        return jsonify({"results": [], "total": 0, "query": query, "error": str(e)})

    display_results = [
        transform_result(raw, rank=i + 1, query=query)
        for i, raw in enumerate(raw_results)
    ]
    return jsonify({
        "results": display_results,
        "total": len(display_results),
        "query": query,
    })

@api_bp.route('/translate', methods=['POST'])
def translate_text():
    data = request.json
    text = data.get("text", "")
    target = data.get("target", "")
    source = data.get("source", None)

    if not text or not target:
        return jsonify({"error": "Missing text or target"}), 400

    cache_key = f"{text[:200]}_{target}"
    if cache_key in translation_cache:
        return jsonify({"translatedText": translation_cache[cache_key]})

    try:
        result = translate_client.translate(
            text,
            source_language=source,
            target_language=target
        )
        translated = result["translatedText"]
        translation_cache[cache_key] = translated
        return jsonify({"translatedText": translated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/metrics')
def metrics():
    clause_metrics = get_metrics(mode="clause")
    granularity_metrics = get_metrics(mode="all")
    system_data = get_system_data()

    return jsonify({
        "baseline": clause_metrics["baseline"],
        "ranked": clause_metrics["ranked"],
        "granularity": {
            "document": granularity_metrics["document"],
            "as": granularity_metrics["as"],
            "clause": granularity_metrics["clause"],
        },
        "systemData": system_data,
    })