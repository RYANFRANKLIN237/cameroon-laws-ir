import os
import json
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz
from tqdm import tqdm

PROCESSED_DIR = os.path.join("data", "processed_units")
INDEX_DIR = "index"

TFIDF_MATRIX_PATH = os.path.join(INDEX_DIR, "tfidf_matrix.npz")
UNIT_IDS_PATH = os.path.join(INDEX_DIR, "tfidf_unit_ids.json")
VECTORIZER_PATH = os.path.join(INDEX_DIR, "tfidf_vectorizer.joblib")


def build_tfidf():
    os.makedirs(INDEX_DIR, exist_ok=True)

    unit_files = sorted(
        [f for f in os.listdir(PROCESSED_DIR) if f.endswith(".txt")]
    )

    if not unit_files:
        print("No processed legal units found.")
        return

    corpus = []
    unit_ids = []

    print("Loading legal units...")
    for unit_file in tqdm(unit_files):
        path = os.path.join(PROCESSED_DIR, unit_file)
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

    # Persist everything
    save_npz(TFIDF_MATRIX_PATH, tfidf_matrix)

    with open(UNIT_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(unit_ids, f)

    joblib.dump(vectorizer, VECTORIZER_PATH)

    print("\nTF-IDF matrix built successfully.")
    print(f"Shape: {tfidf_matrix.shape}")
    print(f"Saved to: {INDEX_DIR}/")


if __name__ == "__main__":
    build_tfidf()
