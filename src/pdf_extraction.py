import os
import io
import json
import pdfplumber

from tqdm import tqdm
from dotenv import load_dotenv
from pdf2image import convert_from_path

from src.page_utils import (
    join_pages_with_markers,
    make_highlight_quote,
    meta_path_for,
    source_pdf_from_stem,
    write_jsonl,
)

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

load_dotenv()

RAW_DIR = os.path.join("data", "raw_pdfs")
TEXT_DIR = os.path.join("data", "extracted_text")
OCR_CACHE_DIR = os.path.join("data", "ocr_cache")

_vision_client = None


def get_vision_client():
    global _vision_client
    if _vision_client is None:
        from google.cloud import vision
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


def safe_stem_from_pdf(pdf_file: str) -> str:
    safe_name = "".join(
        c if c.isalnum() or c in " ._-"
        else "_"
        for c in pdf_file
    )
    stem = safe_name[:-4] if safe_name.lower().endswith(".pdf") else safe_name
    return stem


# ------------------------------------------------------------------
# OCR Helper
# ------------------------------------------------------------------

def ocr_page(pdf_path, page_number, cache_dir=None):
    """
    Convert a single PDF page to image and run Google Vision OCR.
    page_number is 1-based. Results are cached under cache_dir when set.
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"page_{page_number}.txt")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = f.read()
            print(f"    Page {page_number}: OCR (cache)")
            return cached

    from google.cloud import vision

    images = convert_from_path(
        pdf_path,
        first_page=page_number,
        last_page=page_number
    )

    image = images[0]

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    vision_image = vision.Image(
        content=buffer.getvalue()
    )

    response = get_vision_client().document_text_detection(
        image=vision_image
    )

    if response.error.message:
        raise Exception(response.error.message)

    text = response.full_text_annotation.text or ""

    if cache_dir:
        cache_path = os.path.join(cache_dir, f"page_{page_number}.txt")
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(text)

    return text


# ------------------------------------------------------------------
# Hybrid Extraction
# ------------------------------------------------------------------

def extract_pdf_pages(pdf_path, cache_dir=None):
    """
    Hybrid extraction:

    1. Try pdfplumber text extraction.
    2. If little/no text exists, use OCR (with optional page cache).

    Returns a list of per-page text strings (1-based page order).
    """

    extracted_pages = []

    with pdfplumber.open(pdf_path) as pdf:

        for page_num, page in enumerate(pdf.pages, start=1):

            page_text = page.extract_text()

            # Text PDF
            if page_text and len(page_text.strip()) > 100:

                print(
                    f"    Page {page_num}: PDF text "
                    f"({len(page_text)} chars)"
                )

                extracted_pages.append(page_text)

            # Scanned page
            else:

                print(
                    f"    Page {page_num}: OCR"
                )

                ocr_text = ocr_page(
                    pdf_path,
                    page_num,
                    cache_dir=cache_dir,
                )

                extracted_pages.append(ocr_text)

    return extracted_pages


def extract_pdf_text(pdf_path):
    """
    Backward-compatible helper: marked full text only.
    Prefer extract_pdf_pages + join_pages_with_markers for new code.
    """
    pages = extract_pdf_pages(pdf_path)
    marked_text, _ = join_pages_with_markers(pages)
    return marked_text


# ------------------------------------------------------------------
# Main Extraction Pipeline
# ------------------------------------------------------------------

def extract_all_pdfs(skip_existing=False):

    os.makedirs(TEXT_DIR, exist_ok=True)
    document_records = []

    try:

        pdf_files = sorted(
            f for f in os.listdir(RAW_DIR)
            if f.lower().endswith(".pdf")
        )

        if not pdf_files:
            print(
                f"No PDF files found in "
                f"{os.path.abspath(RAW_DIR)}"
            )
            return

        print(
            f"Found {len(pdf_files)} PDF files to process..."
        )

        for pdf_file in tqdm(
            pdf_files,
            desc="Extracting PDFs"
        ):

            try:

                pdf_path = os.path.join(
                    RAW_DIR,
                    pdf_file
                )

                stem = safe_stem_from_pdf(pdf_file)

                txt_path = os.path.join(
                    TEXT_DIR,
                    f"{stem}.txt"
                )
                pages_path = os.path.join(
                    TEXT_DIR,
                    f"{stem}.pages.json"
                )

                if (
                    skip_existing
                    and os.path.exists(txt_path)
                    and os.path.exists(pages_path)
                ):
                    print(f"\nSkipping (exists): {pdf_file}")
                    with open(pages_path, "r", encoding="utf-8") as f:
                        pages_payload = json.load(f)
                    with open(txt_path, "r", encoding="utf-8") as f:
                        full_text = f.read()
                    page_count = pages_payload.get("page_count", 1) or 1
                    document_records.append({
                        "unit_id": f"{stem}.txt",
                        "source_pdf": source_pdf_from_stem(stem),
                        "page_start": 1,
                        "page_end": page_count,
                        "highlight_quote": make_highlight_quote(full_text),
                    })
                    continue

                print(f"\nProcessing: {pdf_file}")

                cache_dir = os.path.join(OCR_CACHE_DIR, stem)
                pages = extract_pdf_pages(pdf_path, cache_dir=cache_dir)
                full_text, pages_payload = join_pages_with_markers(pages)

                with open(
                    txt_path,
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(full_text)

                with open(
                    pages_path,
                    "w",
                    encoding="utf-8"
                ) as f:
                    json.dump(pages_payload, f, ensure_ascii=False, indent=2)

                unit_id = f"{stem}.txt"
                page_count = pages_payload.get("page_count", len(pages)) or 1
                document_records.append({
                    "unit_id": unit_id,
                    "source_pdf": source_pdf_from_stem(stem),
                    "page_start": 1,
                    "page_end": page_count,
                    "highlight_quote": make_highlight_quote(full_text),
                })

                print(
                    f"✓ Saved: "
                    f"{os.path.basename(txt_path)} "
                    f"({len(full_text)} characters, "
                    f"{page_count} pages)"
                )

            except Exception as e:

                print(
                    f"\nError processing "
                    f"{pdf_file}: {e}"
                )

                continue

        write_jsonl(meta_path_for("document"), document_records)
        print(
            f"✓ Document metadata: "
            f"{meta_path_for('document')} "
            f"({len(document_records)} records)"
        )

        print("\nExtraction completed!")

    except Exception as e:

        print(
            f"An error occurred: {e}"
        )


# ------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    skip = "--skip-existing" in sys.argv

    print("Starting PDF extraction...")
    print(
        f"Source directory: "
        f"{os.path.abspath(RAW_DIR)}"
    )
    print(
        f"Output directory: "
        f"{os.path.abspath(TEXT_DIR)}"
    )

    extract_all_pdfs(skip_existing=skip)
