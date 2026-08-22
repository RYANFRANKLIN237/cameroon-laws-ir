from flask import Blueprint, request, jsonify, current_app
from src.evaluation import get_metrics
from src.diagnostic import get_system_data
from src.tfidf_search import search as tfidf_search
from src.utils import transform_result, CONFIG
from src.legal_templates import CATEGORIES, TEMPLATES
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Cache for translations (could be moved to a dedicated module)
translation_cache = {}


@api_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({
            "results": [], 
            "total": 0, 
            "query": query, 
            "translated_query": ""
        })

    try:
      
        search_payload = tfidf_search(query, top_k=10, use_rerank=True)
        
        
        final_results = search_payload.get("final_results", [])
        translated_query = search_payload.get("translated_query", "")
        
    except Exception as e:
        current_app.logger.error(f"Search failed: {e}")
        return jsonify({
            "results": [], 
            "total": 0, 
            "query": query, 
            "translated_query": "",
            "error": str(e)
        })

   
    display_results = [
        transform_result(raw, rank=i + 1, query=query, granularity="clause")
        for i, raw in enumerate(final_results)
    ]
    
  
    return jsonify({
        "results": display_results,
        "total": len(display_results),
        "query": query,
        "translated_query": translated_query,
        "search_mode": search_payload.get("search_mode", "concept"),
        "citation": search_payload.get("citation"),
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
        result = current_app.translate_client.translate(
            text,
            source_language=source,
            target_language=target
        )
        translated = result["translatedText"]
        translation_cache[cache_key] = translated
        return jsonify({"translatedText": translated})
    except Exception as e:
        current_app.logger.exception("Translation failed")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/templates')
def templates():
    return jsonify({
        "categories": CATEGORIES,
        "templates": TEMPLATES,
    })


@api_bp.route('/metrics')
def metrics():
    clause_metrics = get_metrics(mode="clause")          # {baseline, ranked}
    granularity_metrics = get_metrics(
        mode="all",
        clause_ranked_scores=clause_metrics["ranked"]
    )                                                    # {clause, as, document}

    static_data = get_system_data()

    
    clause_failures = granularity_metrics["clause"]["failures"]
    as_failures = granularity_metrics["as"]["failures"]
    document_failures = granularity_metrics["document"]["failures"]

    
    system_data = {
        "legalCorpusSize": static_data["legalCorpusSize"],
        "invertedIndexSize": static_data["invertedIndexSize"],
        "groundTruthQueries": static_data["groundTruthQueries"],
        "failedQueries": clause_failures,
        "failedQueries_as": as_failures,
        "failedQueries_document": document_failures,
        "retrievalLatencySeconds": granularity_metrics["clause"]["avg_latency_seconds"],
    }

    metrics_payload = {
        "baseline": clause_metrics["baseline"],
        "ranked": clause_metrics["ranked"],
        "granularity": {
            "document": granularity_metrics["document"],
            "as": granularity_metrics["as"],
            "clause": granularity_metrics["clause"],
        },
        "systemData": system_data,
    }
    response = jsonify(metrics_payload)
    response.headers["Cache-Control"] = "no-store"

    return response


@api_bp.route('/unit')
def get_unit():
    """
    Get a single unit by unit_id with transform_result-like payload.
    Used for lazy expansion of cross-references.
    """
    unit_id = request.args.get('id', '').strip()
    if not unit_id:
        return jsonify({"error": "Missing unit_id"}), 400

    granularity = request.args.get('granularity', 'clause')
    legal_dir = CONFIG[granularity]["legal_dir"]
    unit_path = os.path.join(legal_dir, unit_id)

    if not os.path.exists(unit_path):
        return jsonify({"error": "Unit not found"}), 404

    try:
        with open(unit_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    except Exception as e:
        current_app.logger.error(f"Failed to read unit {unit_id}: {e}")
        return jsonify({"error": "Failed to read unit"}), 500

    # Build a minimal raw result dict for transform_result
    from src.legal_metadata import infer_law_type, infer_unit_type
    raw_result = {
        "unit_id": unit_id,
        "score": 1.0,
        "final_score": 1.0,
        "text": text,
        "law_type": infer_law_type(unit_id),
        "unit_type": infer_unit_type(unit_id),
    }

    # Use transform_result to get the full display format
    display_result = transform_result(
        raw_result,
        rank=1,
        query="",  # No query needed for unit lookup
        granularity=granularity,
        include_refs=False  # Don't re-compute refs for the target unit
    )

    return jsonify(display_result)
