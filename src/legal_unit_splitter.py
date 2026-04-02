"""
Legal unit splitter for Cameroon laws.
Splits extracted text into individual articles/sections.
"""

# import os
# import re
# from tqdm import tqdm

# TEXT_DIR = os.path.join("data", "extracted_text")
# UNIT_DIR = os.path.join("data", "legal_units")

# # Detect Articles (English + French)
# ARTICLE_PATTERN = re.compile(
#     r'(?im)^\s*article\s+(premier|\d+)\b',
# )


# # Detect Sections (English)
# SECTION_PATTERN = re.compile(
#     r'(?im)^\s*section\s+\d+(?:\s*\(\d+\))?',
# )


# # Detect numbered clauses: (1), (2), (3)...
# CLAUSE_PATTERN = re.compile(
#     r'\(\d+\)'
# )

# def find_all_units(text):
#     units = []

#     for match in ARTICLE_PATTERN.finditer(text):
#         units.append({
#             "type": "article",
#             "id": match.group(0).strip(),
#             "start": match.start()
#         })

#     for match in SECTION_PATTERN.finditer(text):
#         units.append({
#             "type": "section",
#             "id": match.group(0).strip(),
#             "start": match.start()
#         })

#     units.sort(key=lambda x: x["start"])
#     return units


# def split_into_clauses(unit_text):
#     """
#     Split a section/article into clause-level units.
#     Returns list of (clause_id, clause_text)
#     """
#     clauses = []
#     matches = list(CLAUSE_PATTERN.finditer(unit_text))

#     # If no clauses, return whole unit
#     if not matches:
#         return [("full", unit_text.strip())]

#     for i, match in enumerate(matches):
#         start = match.start()
#         end = matches[i + 1].start() if i + 1 < len(matches) else len(unit_text)

#         clause_id = match.group(0).strip("()")
#         clause_text = unit_text[start:end].strip()

#         clauses.append((clause_id, clause_text))

#     return clauses


# def process_documents():
#     os.makedirs(UNIT_DIR, exist_ok=True)

#     txt_files = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]

#     if not txt_files:
#         print("No extracted text files found.")
#         return

#     for txt_file in tqdm(txt_files, desc="Splitting legal units into clauses"):
#         base_name = os.path.splitext(txt_file)[0]
#         path = os.path.join(TEXT_DIR, txt_file)

#         with open(path, "r", encoding="utf-8") as f:
#             text = f.read()

#         units = find_all_units(text)

#         # Fallback: whole document
#         if not units:
#             output_path = os.path.join(
#                 UNIT_DIR, f"{base_name}_full_document.txt"
#             )
#             with open(output_path, "w", encoding="utf-8") as f:
#                 f.write(text)
#             continue

#         for unit in units:
#             unit_start = unit["start"]
#             next_unit_start = next(
#                 (u["start"] for u in units if u["start"] > unit_start),
#                 len(text)
#             )

#             unit_text = text[unit_start:next_unit_start].strip()

#             clauses = split_into_clauses(unit_text)

#             for clause_id, clause_text in clauses:
#                 safe_unit_id = re.sub(r"\s+", "_", unit["id"].lower())
#                 safe_unit_id = re.sub(r"_\(\d+\)", "", safe_unit_id)
#                 safe_unit_id = re.sub(r"(section|article)_", "", safe_unit_id)

#                 filename = (
#                     f"{base_name}_"
#                     f"{unit['type']}_"
#                     f"{safe_unit_id}_"
#                     f"clause_{clause_id}.txt"
#                 )

#                 output_path = os.path.join(UNIT_DIR, filename)

#                 with open(output_path, "w", encoding="utf-8") as f:
#                     f.write(clause_text)

#     print("\nClause-level legal unit splitting completed.")


# if __name__ == "__main__":
#     process_documents()



import os
import re
import sys
from tqdm import tqdm

TEXT_DIR = os.path.join("data", "extracted_text")

CLAUSE_DIR = os.path.join("data", "legal_units")
AS_DIR = os.path.join("data", "legal_units_as")


ARTICLE_PATTERN = re.compile(
    r'(?im)^\s*article\s+(premier|\d+)\b'
)

SECTION_PATTERN = re.compile(
    r'(?im)^\s*section\s+\d+(?:\s*\(\d+\))?'
)

CLAUSE_PATTERN = re.compile(r'\(\d+\)')


def find_all_units(text):
    units = []

    for match in ARTICLE_PATTERN.finditer(text):
        units.append({
            "type": "article",
            "id": match.group(0).strip(),
            "start": match.start()
        })

    for match in SECTION_PATTERN.finditer(text):
        units.append({
            "type": "section",
            "id": match.group(0).strip(),
            "start": match.start()
        })

    units.sort(key=lambda x: x["start"])

    return units


def split_into_clauses(unit_text):

    clauses = []
    matches = list(CLAUSE_PATTERN.finditer(unit_text))

    if not matches:
        return [("full", unit_text.strip())]

    for i, match in enumerate(matches):

        start = match.start()

        end = matches[i + 1].start() if i + 1 < len(matches) else len(unit_text)

        clause_id = match.group(0).strip("()")

        clause_text = unit_text[start:end].strip()

        clauses.append((clause_id, clause_text))

    return clauses


def process_documents(granularity):

    if granularity == "clause":
        output_dir = CLAUSE_DIR
    else:
        output_dir = AS_DIR

    os.makedirs(output_dir, exist_ok=True)

    txt_files = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]

    if not txt_files:
        print("No extracted text files found.")
        return

    for txt_file in tqdm(txt_files, desc=f"Splitting ({granularity})"):

        base_name = os.path.splitext(txt_file)[0]

        path = os.path.join(TEXT_DIR, txt_file)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        units = find_all_units(text)

        if not units:
            continue

        for unit in units:

            unit_start = unit["start"]

            next_unit_start = next(
                (u["start"] for u in units if u["start"] > unit_start),
                len(text)
            )

            unit_text = text[unit_start:next_unit_start].strip()

            safe_unit_id = re.sub(r"\s+", "_", unit["id"].lower())
            safe_unit_id = re.sub(r"_\(\d+\)", "", safe_unit_id)
            safe_unit_id = re.sub(r"(section|article)_", "", safe_unit_id)

            # CLAUSE MODE (unchanged behavior)
            if granularity == "clause":

                clauses = split_into_clauses(unit_text)

                for clause_id, clause_text in clauses:

                    filename = (
                        f"{base_name}_"
                        f"{unit['type']}_"
                        f"{safe_unit_id}_"
                        f"clause_{clause_id}.txt"
                    )

                    output_path = os.path.join(output_dir, filename)

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(clause_text)

            # ARTICLE / SECTION MODE
            else:

                filename = (
                    f"{base_name}_"
                    f"{unit['type']}_"
                    f"{safe_unit_id}.txt"
                )

                output_path = os.path.join(output_dir, filename)

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(unit_text)

    print(f"\n{granularity.upper()} level splitting completed.")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.legal_unit_splitter [clause | as]")
        sys.exit(1)

    granularity = sys.argv[1].lower()

    if granularity not in ["clause", "as"]:
        print("Granularity must be: clause | as")
        sys.exit(1)

    process_documents(granularity)