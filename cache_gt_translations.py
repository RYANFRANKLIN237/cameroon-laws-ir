import os
import json
import sys

# Add the project root to the path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import translate_text, detect_language

def main():
    ground_truth_files = [
        "data/ground_truth/ground_truth.json",
        "data/ground_truth/ground_truth_as.json",
        "data/ground_truth/ground_truth_document.json"
    ]

    translations = {}
    output_path = "data/ground_truth/query_translations.json"

    # Load existing translations if the file already exists
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            translations = json.load(f)

    total_translated = 0

    for gt_file in ground_truth_files:
        if not os.path.exists(gt_file):
            print(f"Warning: {gt_file} not found.")
            continue
            
        print(f"Processing {gt_file}...")
        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
        
        for query in gt_data.keys():
            if query in translations:
                continue
            
            lang = detect_language(query)
            target = "en" if lang == "fr" else "fr"
            try:
                translated = translate_text(query, source=lang, target=target)
                translations[query] = translated
                total_translated += 1
                print(f"[{lang}->{target}] {query[:40]}... => {translated[:40]}...")
            except Exception as e:
                print(f"Error translating '{query}': {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=4)
        
    print(f"\nDone! Translated {total_translated} new queries.")
    print(f"Total translations saved to {output_path}: {len(translations)}")

if __name__ == "__main__":
    main()
