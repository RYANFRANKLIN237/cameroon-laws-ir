import os
import re
import nltk
from tqdm import tqdm

# NLTK data is assumed to be pre-installed
# Note: Run python -c "
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context
# import nltk
# nltk.download('all', quiet=False)
# " first if NLTK data is not installed


UNIT_DIR = os.path.join("data", "legal_units")
PROCESSED_DIR = os.path.join("data", "processed_units")



def preprocess_text(text):
    text = text.lower()
    
    # Keep hyphens, parentheses for legal citations
    text = re.sub(r"[^a-z0-9\s\-()./]", " ", text)
    
    tokens = nltk.word_tokenize(text)

    minimal_stopwords = {'the', 'a', 'an', 'and', 'of', 'to', 'in', 'on', 'at', 'by', 'le', 'la', 'les'}
    
    tokens = [t for t in tokens if t not in minimal_stopwords and len(t) > 1]  # Changed to > 1
    
    return tokens

def preprocess_legal_units():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    unit_files = [f for f in os.listdir(UNIT_DIR) if f.endswith(".txt")]

    if not unit_files:
        print("No legal unit files found.")
        return

    for unit_file in tqdm(unit_files, desc="Preprocessing legal units"):
        input_path = os.path.join(UNIT_DIR, unit_file)
        output_path = os.path.join(PROCESSED_DIR, unit_file)

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        tokens = preprocess_text(text)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(" ".join(tokens))

    print("\nPreprocessing of legal units completed.")


if __name__ == "__main__":
    preprocess_legal_units()