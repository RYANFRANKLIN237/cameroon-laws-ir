import os
import re

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
