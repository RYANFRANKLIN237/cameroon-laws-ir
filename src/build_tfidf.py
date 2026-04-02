import os
import json
import joblib
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz
from tqdm import tqdm


PROCESSED_DIR = os.path.join("data", "processed_units")
PROCESSED_DIR_AS = os.path.join("data", "processed_units_as")
PROCESSED_DIR_DOCUMENT = os.path.join("data", "processed_unit_full")


INDEX_DIR = "index"
INDEX_DIR_AS = "index_as"
INDEX_DIR_DOCUMENT = "index_document"


TFIDF_MATRIX_PATH = os.path.join(INDEX_DIR, "tfidf_matrix.npz")
UNIT_IDS_PATH = os.path.join(INDEX_DIR, "tfidf_unit_ids.json")
VECTORIZER_PATH = os.path.join(INDEX_DIR, "tfidf_vectorizer.joblib")


TFIDF_MATRIX_PATH_AS = os.path.join(INDEX_DIR_AS, "tfidf_matrix_as.npz")
UNIT_IDS_PATH_AS = os.path.join(INDEX_DIR_AS, "tfidf_unit_ids_as.json")
VECTORIZER_PATH_AS = os.path.join(INDEX_DIR_AS, "tfidf_vectorizer_as.joblib")


TFIDF_MATRIX_PATH_DOCUMENT = os.path.join(INDEX_DIR_DOCUMENT, "tfidf_matrix_document.npz")
UNIT_IDS_PATH_DOCUMENT = os.path.join(INDEX_DIR_DOCUMENT, "tfidf_unit_ids_document.json")
VECTORIZER_PATH_DOCUMENT = os.path.join(INDEX_DIR_DOCUMENT, "tfidf_vectorizer_document.joblib")


def build_tfidf_index(input_dir, output_dir, matrix_path, ids_path, vectorizer_path):

    os.makedirs(output_dir, exist_ok=True)

    unit_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    )

    if not unit_files:
        print("No processed files found.")
        return

    corpus = []
    unit_ids = []

    print("Loading documents...")

    for unit_file in tqdm(unit_files):

        path = os.path.join(input_dir, unit_file)

        with open(path, "r", encoding="utf-8") as f:
            corpus.append(f.read())
            unit_ids.append(unit_file)

    vectorizer = TfidfVectorizer(
        tokenizer=str.split,
        lowercase=False,
        min_df=1,
        max_df=0.8,
        sublinear_tf=True,
        norm="l2"
    )

    tfidf_matrix = vectorizer.fit_transform(corpus)

    save_npz(matrix_path, tfidf_matrix)

    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(unit_ids, f)

    joblib.dump(vectorizer, vectorizer_path)

    print("\nTF-IDF matrix built successfully.")
    print(f"Shape: {tfidf_matrix.shape}")
    print(f"Saved to: {output_dir}")


def run_build(granularity):

    if granularity == "clause":

        build_tfidf_index(
            PROCESSED_DIR,
            INDEX_DIR,
            TFIDF_MATRIX_PATH,
            UNIT_IDS_PATH,
            VECTORIZER_PATH
        )

    elif granularity == "as":

        build_tfidf_index(
            PROCESSED_DIR_AS,
            INDEX_DIR_AS,
            TFIDF_MATRIX_PATH_AS,
            UNIT_IDS_PATH_AS,
            VECTORIZER_PATH_AS
        )

    elif granularity == "document":

        build_tfidf_index(
            PROCESSED_DIR_DOCUMENT,
            INDEX_DIR_DOCUMENT,
            TFIDF_MATRIX_PATH_DOCUMENT,
            UNIT_IDS_PATH_DOCUMENT,
            VECTORIZER_PATH_DOCUMENT
        )

    else:

        print("Granularity must be: clause | as | document")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.build_tfidf [clause | as | document]")
        sys.exit(1)

    granularity = sys.argv[1].lower()

    run_build(granularity)
