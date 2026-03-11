import pdfplumber
import os
import sys
from tqdm import tqdm

# Define directories
RAW_DIR = os.path.join("data", "raw_pdfs")
TEXT_DIR = os.path.join("data", "extracted_text")

def extract_all_pdfs():
    # Create output directory if it doesn't exist
    os.makedirs(TEXT_DIR, exist_ok=True)
    
    # Get list of PDF files
    try:
        pdf_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(".pdf")]
        if not pdf_files:
            print(f"No PDF files found in {os.path.abspath(RAW_DIR)}")
            return
            
        print(f"Found {len(pdf_files)} PDF files to process...")
        
        for pdf_file in tqdm(pdf_files, desc="Extracting PDFs"):
            try:
                pdf_path = os.path.join(RAW_DIR, pdf_file)
                # Create a safe filename by replacing spaces and special characters
                safe_name = "".join(c if c.isalnum() or c in ' ._-' else '_' for c in pdf_file)
                txt_path = os.path.join(TEXT_DIR, safe_name.replace(".pdf", ".txt"))
                
                print(f"\nProcessing: {pdf_file}")
                
                text = []
                with pdfplumber.open(pdf_path) as pdf:
                    for i, page in enumerate(pdf.pages, 1):
                        page_text = page.extract_text()
                        if page_text:
                            text.append(page_text)
                        print(f"  - Extracted page {i}", end='\r')
                
                # Join all pages with double newlines
                full_text = "\n\n".join(text)
                
                # Write to file
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                
                print(f"\n✓ Saved: {os.path.basename(txt_path)} ({len(full_text)} characters)")
                
            except Exception as e:
                print(f"\nError processing {pdf_file}: {str(e)}")
                continue
                
        print("\nExtraction completed!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return

if __name__ == "__main__":
    print(f"Starting PDF extraction...")
    print(f"Source directory: {os.path.abspath(RAW_DIR)}")
    print(f"Output directory: {os.path.abspath(TEXT_DIR)}")
    extract_all_pdfs()
