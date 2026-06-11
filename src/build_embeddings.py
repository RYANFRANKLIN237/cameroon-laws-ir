import os
os.environ["FASTEMBED_CACHE_PATH"] = "./models"

import json
import sys
import numpy as np

from langdetect import detect, DetectorFactory
from fastembed import TextEmbedding

DetectorFactory.seed = 0


CONFIG = {

    "clause": {
        "processed_dir": "data/processed_units",
        "index_dir": "index"
    },

    "as": {
        "processed_dir": "data/processed_units_as",
        "index_dir": "index_as"
    },

    "document": {
        "processed_dir": "data/processed_unit_full",
        "index_dir": "index_document"
    }
}


def build_embeddings(unit_type):

    if unit_type not in CONFIG:
        raise ValueError(f"Invalid unit type: {unit_type}")

    config = CONFIG[unit_type]

    processed_dir = config["processed_dir"]
    index_dir = config["index_dir"]

    os.makedirs(index_dir, exist_ok=True)

    model = TextEmbedding(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    unit_files = sorted(
        [f for f in os.listdir(processed_dir)
         if f.endswith(".txt")]
    )

    corpus_en = []
    ids_en = []

    corpus_fr = []
    ids_fr = []

    unknown = 0

    print("Loading multilingual documents...")

    for file in unit_files:

        path = os.path.join(processed_dir, file)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        # Skip empty garbage files
        if not text.strip():
            continue

        try:

            lang = detect(text[:1000])

            if lang == "en":

                corpus_en.append(text)
                ids_en.append(file)

            elif lang == "fr":

                corpus_fr.append(text)
                ids_fr.append(file)

            else:

                unknown += 1

        except Exception:

            unknown += 1

    print("\nBuilding English embeddings...")
    embeddings_en = np.array(
        list(model.embed(corpus_en))
    )

    print("Building French embeddings...")
    embeddings_fr = np.array(
        list(model.embed(corpus_fr))
    )

    np.save(
        os.path.join(index_dir, "embeddings_en.npy"),
        embeddings_en
    )

    np.save(
        os.path.join(index_dir, "embeddings_fr.npy"),
        embeddings_fr
    )

    with open(
        os.path.join(index_dir,
                     "embedding_unit_ids_en.json"),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(ids_en, f)

    with open(
        os.path.join(index_dir,
                     "embedding_unit_ids_fr.json"),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(ids_fr, f)

    print("\nMultilingual embeddings built successfully.")
    print(f"English documents : {len(ids_en)}")
    print(f"French documents  : {len(ids_fr)}")
    print(f"Unknown documents : {unknown}")
    print(f"Embedding dimension : {embeddings_en.shape[1]}")
    print("\nSaved:")
    print(f"  EN -> {index_dir}/embeddings_en.npy")
    print(f"  FR -> {index_dir}/embeddings_fr.npy")


def run_build(granularity):

    if granularity == "clause":

        build_embeddings("clause")

    elif granularity == "as":

        build_embeddings("as")

    elif granularity == "document":

        build_embeddings("document")

    else:

        print("Granularity must be: clause | as | document")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Usage: python -m src.build_embeddings "
            "[clause | as | document]"
        )
        sys.exit(1)

    granularity = sys.argv[1].lower()

    run_build(granularity)