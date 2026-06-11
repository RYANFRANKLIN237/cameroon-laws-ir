import os
import io
import pdfplumber

from tqdm import tqdm
from dotenv import load_dotenv
from google.cloud import vision
from pdf2image import convert_from_path

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

load_dotenv()

vision_client = vision.ImageAnnotatorClient()

RAW_DIR = os.path.join("data", "raw_pdfs")
TEXT_DIR = os.path.join("data", "extracted_text")


# ------------------------------------------------------------------
# OCR Helper
# ------------------------------------------------------------------

def ocr_page(pdf_path, page_number):
    """
    Convert a single PDF page to image and run Google Vision OCR.
    page_number is 1-based.
    """

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

    response = vision_client.document_text_detection(
        image=vision_image
    )

    if response.error.message:
        raise Exception(response.error.message)

    return response.full_text_annotation.text


# ------------------------------------------------------------------
# Hybrid Extraction
# ------------------------------------------------------------------

def extract_pdf_text(pdf_path):
    """
    Hybrid extraction:

    1. Try pdfplumber text extraction.
    2. If little/no text exists, use OCR.
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
                    page_num
                )

                extracted_pages.append(ocr_text)

    return "\n\n".join(extracted_pages)


# ------------------------------------------------------------------
# Main Extraction Pipeline
# ------------------------------------------------------------------

def extract_all_pdfs():

    os.makedirs(TEXT_DIR, exist_ok=True)

    try:

        pdf_files = [
            f for f in os.listdir(RAW_DIR)
            if f.lower().endswith(".pdf")
        ]

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

                safe_name = "".join(
                    c if c.isalnum() or c in " ._-"
                    else "_"
                    for c in pdf_file
                )

                txt_path = os.path.join(
                    TEXT_DIR,
                    safe_name.replace(".pdf", ".txt")
                )

                print(f"\nProcessing: {pdf_file}")

                full_text = extract_pdf_text(
                    pdf_path
                )

                # Overwrites existing file automatically
                with open(
                    txt_path,
                    "w",
                    encoding="utf-8"
                ) as f:
                    f.write(full_text)

                print(
                    f"✓ Saved: "
                    f"{os.path.basename(txt_path)} "
                    f"({len(full_text)} characters)"
                )

            except Exception as e:

                print(
                    f"\nError processing "
                    f"{pdf_file}: {e}"
                )

                continue

        print("\nExtraction completed!")

    except Exception as e:

        print(
            f"An error occurred: {e}"
        )


# ------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------

if __name__ == "__main__":

    print("Starting PDF extraction...")
    print(
        f"Source directory: "
        f"{os.path.abspath(RAW_DIR)}"
    )
    print(
        f"Output directory: "
        f"{os.path.abspath(TEXT_DIR)}"
    )

    extract_all_pdfs()
