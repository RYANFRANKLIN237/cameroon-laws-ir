import os
import json
import sys
from collections import defaultdict
from tqdm import tqdm

PROCESSED_DIR = os.path.join("data", "processed_units")
PROCESSED_DIR_AS = os.path.join("data", "processed_units_as")
PROCESSED_DIR_DOCUMENT = os.path.join("data", "processed_unit_full")

INDEX_DIR = "index"
INDEX_DIR_AS = "index_as"
INDEX_DIR_DOCUMENT = "index_document"

INDEX_PATH = os.path.join(INDEX_DIR, "inverted_index.json")
INDEX_PATH_AS = os.path.join(INDEX_DIR_AS, "inverted_index_as.json")
INDEX_PATH_DOCUMENT = os.path.join(INDEX_DIR_DOCUMENT, "inverted_index_document.json")


def build_index(input_dir, output_dir, output_path):

    os.makedirs(output_dir, exist_ok=True)

    inverted_index = defaultdict(lambda: defaultdict(list))

    unit_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

    if not unit_files:
        print("No processed files found.")
        return

    for unit_file in tqdm(unit_files, desc="Building inverted index"):

        unit_id = unit_file

        path = os.path.join(input_dir, unit_file)

        with open(path, "r", encoding="utf-8") as f:
            tokens = f.read().split()

        for position, token in enumerate(tokens):

            inverted_index[token][unit_id].append(position)

    inverted_index = {
        term: dict(postings)
        for term, postings in inverted_index.items()
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inverted_index, f)

    print("\nInverted index built successfully.")
    print(f"Total terms: {len(inverted_index)}")
    print(f"Saved to: {output_path}")


def run_build(granularity):

    if granularity == "clause":

        build_index(
            PROCESSED_DIR,
            INDEX_DIR,
            INDEX_PATH
        )

    elif granularity == "as":

        build_index(
            PROCESSED_DIR_AS,
            INDEX_DIR_AS,
            INDEX_PATH_AS
        )

    elif granularity == "document":

        build_index(
            PROCESSED_DIR_DOCUMENT,
            INDEX_DIR_DOCUMENT,
            INDEX_PATH_DOCUMENT
        )

    else:

        print("Granularity must be: clause | as | document")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.build_inverted_index [clause | as | document]")
        sys.exit(1)

    granularity = sys.argv[1].lower()

    run_build(granularity)