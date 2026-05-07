import os
from flask import Flask
from google.cloud import translate_v2 as translate
from src.utils import get_pdf_mapping

# Global objects that need to be shared across blueprints
translate_client = None
pdf_file_map = {}
pdf_storage_path = os.path.join(os.getcwd(), "data", "raw_pdfs")

def create_app():
    global translate_client, pdf_file_map

    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Load environment variables (dotenv already loaded in main.py)
    translate_client = translate.Client()
    pdf_file_map = get_pdf_mapping(pdf_storage_path)

    
    from app.routes.api import api_bp
    from app.routes.views import views_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    return app