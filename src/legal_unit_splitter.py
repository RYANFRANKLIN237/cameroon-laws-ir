"""
Legal unit splitter for Cameroon laws.
Splits extracted text into individual articles/sections (and clauses),
preserving PDF page spans in sidecar metadata.
"""
import os
import re
import sys
from tqdm import tqdm
import shutil

from src.page_utils import (
    make_highlight_quote,
    meta_path_for,
    page_span_for_range,
    source_pdf_from_stem,
    strip_page_markers,
    write_jsonl,
)

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

        clauses.append((clause_id, clause_text, start, end))

    return clauses


def safe_unit_id_from(unit_id: str) -> str:
    safe_unit_id = re.sub(r"\s+", "_", unit_id.lower())
    safe_unit_id = re.sub(r"_\(\d+\)", "", safe_unit_id)
    safe_unit_id = re.sub(r"(section|article)_", "", safe_unit_id)
    return safe_unit_id


def process_documents(granularity):

    if granularity == "clause":
        output_dir = CLAUSE_DIR
    else:
        output_dir = AS_DIR

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    txt_files = [f for f in os.listdir(TEXT_DIR) if f.endswith(".txt")]

    if not txt_files:
        print("No extracted text files found.")
        return

    metadata_by_id = {}

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

            unit_text = text[unit_start:next_unit_start]
            safe_unit_id = safe_unit_id_from(unit["id"])

            # CLAUSE MODE
            if granularity == "clause":

                clause_parts = split_into_clauses(unit_text)

                for clause_part in clause_parts:
                    if len(clause_part) == 4:
                        clause_id, clause_text, rel_start, rel_end = clause_part
                        abs_start = unit_start + rel_start
                        abs_end = unit_start + rel_end
                    else:
                        clause_id, clause_text = clause_part
                        abs_start, abs_end = unit_start, next_unit_start

                    clean_text = strip_page_markers(clause_text).strip()
                    if not clean_text:
                        continue

                    page_start, page_end = page_span_for_range(
                        text, abs_start, abs_end
                    )

                    filename = (
                        f"{base_name}_"
                        f"{unit['type']}_"
                        f"{safe_unit_id}_"
                        f"clause_{clause_id}.txt"
                    )

                    output_path = os.path.join(output_dir, filename)

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(clean_text)

                    metadata_by_id[filename] = {
                        "unit_id": filename,
                        "source_pdf": source_pdf_from_stem(base_name),
                        "page_start": page_start,
                        "page_end": page_end,
                        "highlight_quote": make_highlight_quote(clean_text),
                    }

            # ARTICLE / SECTION MODE
            else:

                clean_text = strip_page_markers(unit_text).strip()
                if not clean_text:
                    continue

                page_start, page_end = page_span_for_range(
                    text, unit_start, next_unit_start
                )

                filename = (
                    f"{base_name}_"
                    f"{unit['type']}_"
                    f"{safe_unit_id}.txt"
                )

                output_path = os.path.join(output_dir, filename)

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)

                metadata_by_id[filename] = {
                    "unit_id": filename,
                    "source_pdf": source_pdf_from_stem(base_name),
                    "page_start": page_start,
                    "page_end": page_end,
                    "highlight_quote": make_highlight_quote(clean_text),
                }

    metadata_records = list(metadata_by_id.values())
    write_jsonl(meta_path_for(granularity), metadata_records)
    print(
        f"\n{granularity.upper()} level splitting completed "
        f"({len(metadata_records)} units, "
        f"metadata → {meta_path_for(granularity)})."
    )


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python -m src.legal_unit_splitter [clause | as]")
        sys.exit(1)

    granularity = sys.argv[1].lower()

    if granularity not in ["clause", "as"]:
        print("Granularity must be: clause | as")
        sys.exit(1)

    process_documents(granularity)
