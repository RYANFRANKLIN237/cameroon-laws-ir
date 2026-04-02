import os
import json
import sys
import numpy as np
from fastembed import TextEmbedding


CONFIG = {

    "clause": {
        "processed_dir": "data/processed_units",
        "index_dir": "index",
        "embeddings_file": "embeddings.npy",
        "unit_ids_file": "embedding_unit_ids.json"
    },

    "as": {
        "processed_dir": "data/processed_units_as",
        "index_dir": "index_as",
        "embeddings_file": "embeddings_as.npy",
        "unit_ids_file": "embedding_unit_ids_as.json"
    },

    "document": {
        "processed_dir": "data/processed_unit_full",
        "index_dir": "index_document",
        "embeddings_file": "embeddings_document.npy",
        "unit_ids_file": "embedding_unit_ids_document.json"
    }
}


def build_embeddings(unit_type):

    if unit_type not in CONFIG:
        raise ValueError(f"Invalid unit type: {unit_type}")

    config = CONFIG[unit_type]

    processed_dir = config["processed_dir"]
    index_dir = config["index_dir"]

    embeddings_path = os.path.join(index_dir, config["embeddings_file"])
    unit_ids_path = os.path.join(index_dir, config["unit_ids_file"])

    os.makedirs(index_dir, exist_ok=True)

    model = TextEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )

    unit_files = sorted(
        [f for f in os.listdir(processed_dir) if f.endswith(".txt")]
    )

    corpus = []
    unit_ids = []

    for file in unit_files:

        path = os.path.join(processed_dir, file)

        with open(path, "r", encoding="utf-8") as f:
            corpus.append(f.read())

        unit_ids.append(file)

    print(f"Building embeddings for {unit_type} units...")
    print(f"Documents: {len(corpus)}")

    embeddings = list(model.embed(corpus))
    embeddings = np.array(embeddings)

    np.save(embeddings_path, embeddings)

    with open(unit_ids_path, "w", encoding="utf-8") as f:
        json.dump(unit_ids, f)

    print("Embeddings built successfully.")
    print("Shape:", embeddings.shape)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python build_embeddings.py [clause | as | document]")
        sys.exit(1)

    unit_type = sys.argv[1]

    build_embeddings(unit_type)