import os
import re
import sys
import nltk
from tqdm import tqdm

# NLTK data is assumed to be pre-installed
# Note: Run python -c "
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context
# import nltk
# nltk.download('all', quiet=False)
# " first if NLTK data is not installed

# python3 -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt')"



UNIT_DIR = os.path.join("data", "legal_units")
UNIT_DIR_AS = os.path.join("data", "legal_units_as")
TEXT_DIR = os.path.join("data", "extracted_text")

PROCESSED_DIR = os.path.join("data", "processed_units")
PROCESSED_DIR_AS = os.path.join("data", "processed_units_as")
PROCESSED_DIR_FULL = os.path.join("data", "processed_unit_full")



def preprocess_text(text):
    text = text.lower()
    
    # Keep hyphens, parentheses for legal citations
    text = re.sub(r"[^a-z0-9\s\-()./]", " ", text)
    
    tokens = nltk.word_tokenize(text)

    minimal_stopwords = {'the', 'a', 'an', 'and', 'of', 'to', 'in', 'on', 'at', 'by', 'le', 'la', 'les'}
    
    tokens = [t for t in tokens if t not in minimal_stopwords and len(t) > 1]  # Changed to > 1
    
    return tokens

def preprocess_corpus(input_dir, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    unit_files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

    if not unit_files:
        print("No files found in", input_dir)
        return

    for unit_file in tqdm(unit_files, desc=f"Preprocessing {input_dir}"):

        input_path = os.path.join(input_dir, unit_file)
        output_path = os.path.join(output_dir, unit_file)

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        tokens = preprocess_text(text)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(" ".join(tokens))

    print(f"\nPreprocessing completed for {input_dir}")


def run_preprocessing(granularity):

    if granularity == "clause":

        preprocess_corpus(
            UNIT_DIR,
            PROCESSED_DIR
        )

    elif granularity == "as":

        preprocess_corpus(
            UNIT_DIR_AS,
            PROCESSED_DIR_AS
        )

    elif granularity == "document":

        preprocess_corpus(
            TEXT_DIR,
            PROCESSED_DIR_FULL
        )

    else:

        print("Granularity must be: clause | as | document")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.preprocessing [clause | as | document]")
        sys.exit(1)
        
    granularity = sys.argv[1].lower()
    
    run_preprocessing(granularity)