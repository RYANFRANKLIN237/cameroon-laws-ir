import os
import json
import numpy as np
from fastembed import TextEmbedding

PROCESSED_DIR = "data/processed_units"
INDEX_DIR = "index"

EMBEDDINGS_PATH = os.path.join(INDEX_DIR, "embeddings.npy")
UNIT_IDS_PATH = os.path.join(INDEX_DIR, "embedding_unit_ids.json")


def build_embeddings():

    os.makedirs(INDEX_DIR, exist_ok=True)

    model = TextEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )

    unit_files = sorted(
        [f for f in os.listdir(PROCESSED_DIR) if f.endswith(".txt")]
    )

    corpus = []
    unit_ids = []

    for file in unit_files:
        path = os.path.join(PROCESSED_DIR, file)

        with open(path, "r", encoding="utf-8") as f:
            corpus.append(f.read())

        unit_ids.append(file)

    print("Building embeddings...")

    embeddings = list(model.embed(corpus))
    embeddings = np.array(embeddings)

    np.save(EMBEDDINGS_PATH, embeddings)

    with open(UNIT_IDS_PATH, "w") as f:
        json.dump(unit_ids, f)

    print("Embeddings built.")
    print("Shape:", embeddings.shape)


if __name__ == "__main__":
    build_embeddings()