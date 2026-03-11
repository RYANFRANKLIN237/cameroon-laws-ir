import os
import json
from collections import defaultdict
from tqdm import tqdm

PROCESSED_DIR = os.path.join("data", "processed_units")
INDEX_DIR = "index"
INDEX_PATH = os.path.join(INDEX_DIR, "inverted_index.json")


def build_inverted_index():
    os.makedirs(INDEX_DIR, exist_ok=True)

    inverted_index = defaultdict(lambda: defaultdict(list))

    unit_files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith(".txt")]

    if not unit_files:
        print("No processed legal units found.")
        return

    for unit_file in tqdm(unit_files, desc="Building inverted index"):
        unit_id = unit_file  # legal unit identifier
        path = os.path.join(PROCESSED_DIR, unit_file)

        with open(path, "r", encoding="utf-8") as f:
            tokens = f.read().split()

        for position, token in enumerate(tokens):
            inverted_index[token][unit_id].append(position)

    # Convert defaultdicts to normal dicts for JSON serialization
    inverted_index = {
        term: dict(postings)
        for term, postings in inverted_index.items()
    }

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(inverted_index, f, indent=2)

    print(f"\nInverted index built successfully.")
    print(f"Total terms: {len(inverted_index)}")
    print(f"Saved to: {INDEX_PATH}")


if __name__ == "__main__":
    build_inverted_index()
