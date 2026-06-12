from flask import Blueprint, request, jsonify, current_app
from src.evaluation import get_metrics
from src.diagnostic import get_system_data
from src.tfidf_search import search as tfidf_search
from src.utils import transform_result

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
        transform_result(raw, rank=i + 1, query=query)
        for i, raw in enumerate(final_results)
    ]
    
  
    return jsonify({
        "results": display_results,
        "total": len(display_results),
        "query": query,
        "translated_query": translated_query 
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


@api_bp.route('/metrics')
def metrics():
    clause_metrics = get_metrics(mode="clause")          # {baseline, ranked}
    granularity_metrics = get_metrics(mode="all")        # {clause, as, document}

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
    }

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