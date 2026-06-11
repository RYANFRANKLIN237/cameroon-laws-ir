import os
import json
import joblib
import sys

from langdetect import detect, DetectorFactory
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import save_npz
from tqdm import tqdm


DetectorFactory.seed = 0

PROCESSED_DIR = os.path.join("data", "processed_units")
PROCESSED_DIR_AS = os.path.join("data", "processed_units_as")
PROCESSED_DIR_DOCUMENT = os.path.join("data", "processed_unit_full")


INDEX_DIR = "index"
INDEX_DIR_AS = "index_as"
INDEX_DIR_DOCUMENT = "index_document"


def build_tfidf_index(input_dir, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    unit_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    )

    if not unit_files:
        print("No processed files found.")
        return

    corpus_en = []
    ids_en = []

    corpus_fr = []
    ids_fr = []

    unknown = 0

    print("Loading multilingual documents...")

    for unit_file in tqdm(unit_files):

        path = os.path.join(input_dir, unit_file)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            continue

        try:
            lang = detect(text[:1000])

            if lang == "en":
                corpus_en.append(text)
                ids_en.append(unit_file)

            elif lang == "fr":
                corpus_fr.append(text)
                ids_fr.append(unit_file)

            else:
                unknown += 1

        except:
            unknown += 1

    vectorizer_en = TfidfVectorizer(
        tokenizer=str.split,
        lowercase=False,
        min_df=1,
        max_df=0.8,
        sublinear_tf=True,
        norm="l2"
    )

    vectorizer_fr = TfidfVectorizer(
        tokenizer=str.split,
        lowercase=False,
        min_df=1,
        max_df=0.8,
        sublinear_tf=True,
        norm="l2"
    )

    print("\nBuilding English TF-IDF...")
    tfidf_en = vectorizer_en.fit_transform(corpus_en)

    print("Building French TF-IDF...")
    tfidf_fr = vectorizer_fr.fit_transform(corpus_fr)

    save_npz(
        os.path.join(output_dir, "tfidf_matrix_en.npz"),
        tfidf_en
    )

    save_npz(
        os.path.join(output_dir, "tfidf_matrix_fr.npz"),
        tfidf_fr
    )

    with open(
        os.path.join(output_dir, "tfidf_unit_ids_en.json"),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(ids_en, f)

    with open(
        os.path.join(output_dir, "tfidf_unit_ids_fr.json"),
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(ids_fr, f)

    joblib.dump(
        vectorizer_en,
        os.path.join(output_dir, "tfidf_vectorizer_en.joblib")
    )

    joblib.dump(
        vectorizer_fr,
        os.path.join(output_dir, "tfidf_vectorizer_fr.joblib")
    )

    print("\nMultilingual TF-IDF built successfully.")
    print(f"English documents : {len(ids_en)}")
    print(f"French documents  : {len(ids_fr)}")
    print(f"Unknown documents : {unknown}")
    print(f"English features  : {tfidf_en.shape[1]}")
    print(f"French features   : {tfidf_fr.shape[1]}")
    print("\nSaved:")
    print(f"  EN -> {output_dir}/tfidf_matrix_en.npz")
    print(f"  FR -> {output_dir}/tfidf_matrix_fr.npz")


def run_build(granularity):

    if granularity == "clause":

        build_tfidf_index(
            PROCESSED_DIR,
            INDEX_DIR
        )

    elif granularity == "as":

        build_tfidf_index(
            PROCESSED_DIR_AS,
            INDEX_DIR_AS
        )

    elif granularity == "document":

        build_tfidf_index(
            PROCESSED_DIR_DOCUMENT,
            INDEX_DIR_DOCUMENT
        )

    else:

        print("Granularity must be: clause | as | document")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.build_tfidf [clause | as | document]")
        sys.exit(1)

    granularity = sys.argv[1].lower()

    run_build(granularity)
