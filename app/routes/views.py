from flask import Blueprint, render_template, send_from_directory, jsonify
from app import pdf_file_map, pdf_storage_path
from src.utils import normalize_filename

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def onboarding():
    return render_template('onboarding.html')

@views_bp.route('/search')
def search_home():
    return render_template('search.html')

@views_bp.route('/metrics')
def metrics():
    return render_template('metrics.html')

@views_bp.route('/view-pdf/<path:source_name>')
def serve_legal_pdf(source_name):
    norm_request = normalize_filename(source_name)
    actual_filename = pdf_file_map.get(norm_request)
    if actual_filename:
        return send_from_directory(pdf_storage_path, actual_filename)
    return jsonify({
        "error": "PDF not found",
        "details": f"Could not match '{source_name}' to any file in storage."
    }), 404