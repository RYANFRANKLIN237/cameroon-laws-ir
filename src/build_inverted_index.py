import os
import json
import sys
from collections import defaultdict
from tqdm import tqdm
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

PROCESSED_DIR = os.path.join("data", "processed_units")
PROCESSED_DIR_AS = os.path.join("data", "processed_units_as")
PROCESSED_DIR_DOCUMENT = os.path.join("data", "processed_unit_full")

INDEX_DIR = "index"
INDEX_DIR_AS = "index_as"
INDEX_DIR_DOCUMENT = "index_document"

# Clause-level indexes
INDEX_PATH_EN = os.path.join(INDEX_DIR, "inverted_index_en.json")
INDEX_PATH_FR = os.path.join(INDEX_DIR, "inverted_index_fr.json")

# Article/Section-level indexes
INDEX_PATH_AS_EN = os.path.join(
    INDEX_DIR_AS,
    "inverted_index_as_en.json"
)
INDEX_PATH_AS_FR = os.path.join(
    INDEX_DIR_AS,
    "inverted_index_as_fr.json"
)

# Document-level indexes
INDEX_PATH_DOC_EN = os.path.join(
    INDEX_DIR_DOCUMENT,
    "inverted_index_document_en.json"
)
INDEX_PATH_DOC_FR = os.path.join(
    INDEX_DIR_DOCUMENT,
    "inverted_index_document_fr.json"
)


def build_index(input_dir, output_dir, english_path, french_path):

    os.makedirs(output_dir, exist_ok=True)

    english_index = defaultdict(lambda: defaultdict(list))
    french_index = defaultdict(lambda: defaultdict(list))

    unit_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

    if not unit_files:
        print("No processed files found.")
        return

    english_docs = 0
    french_docs = 0

    for unit_file in tqdm(unit_files, desc="Building multilingual index"):

        path = os.path.join(input_dir, unit_file)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            continue

        try:
            language = detect(text[:1000])
        except Exception:
            continue

        tokens = text.split()

        if language == "fr":
            target_index = french_index
            french_docs += 1
        else:
            target_index = english_index
            english_docs += 1

        for position, token in enumerate(tokens):
            target_index[token][unit_file].append(position)

    english_index = {
        term: dict(postings)
        for term, postings in english_index.items()
    }

    french_index = {
        term: dict(postings)
        for term, postings in french_index.items()
    }

    with open(english_path, "w", encoding="utf-8") as f:
        json.dump(english_index, f)

    with open(french_path, "w", encoding="utf-8") as f:
        json.dump(french_index, f)

    print("\nMultilingual inverted index built successfully.")
    print(f"English documents: {english_docs}")
    print(f"French documents: {french_docs}")
    print(f"English terms: {len(english_index)}")
    print(f"French terms: {len(french_index)}")
    print(f"\nSaved:")
    print(f"  EN -> {english_path}")
    print(f"  FR -> {french_path}")


def run_build(granularity):

    if granularity == "clause":

        build_index(
            PROCESSED_DIR,
            INDEX_DIR,
            INDEX_PATH_EN,
            INDEX_PATH_FR
        )

    elif granularity == "as":

        build_index(
            PROCESSED_DIR_AS,
            INDEX_DIR_AS,
            INDEX_PATH_AS_EN,
            INDEX_PATH_AS_FR
        )

    elif granularity == "document":

        build_index(
            PROCESSED_DIR_DOCUMENT,
            INDEX_DIR_DOCUMENT,
            INDEX_PATH_DOC_EN,
            INDEX_PATH_DOC_FR
        )

    else:

        print("Granularity must be: clause | as | document")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            "Usage: python -m src.build_inverted_index "
            "[clause | as | document]"
        )
        sys.exit(1)

    granularity = sys.argv[1].lower()

    run_build(granularity)