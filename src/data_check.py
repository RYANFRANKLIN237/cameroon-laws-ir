#!/usr/bin/env python3
"""
Data inspection script for Cameroon legal corpus.
"""

import os
import sys
from langdetect import detect, DetectorFactory
from src.evaluation import evaluate, latency_per_granularity

# Ensure deterministic language detection (optional but good practice)
DetectorFactory.seed = 0

# Project root relative to this file's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories
EXTRACTED_TEXT_DIR = os.path.join(BASE_DIR, "data", "extracted_text")
LEGAL_UNITS_AS_DIR = os.path.join(BASE_DIR, "data", "legal_units_as")


def count_txt_files(directory):
    """Return number of .txt files in the given directory."""
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory) if f.endswith(".txt")])


def detect_language_file(file_path):
    """Detect language of text in a file. Returns 'Unknown' if detection fails."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return "Empty"
        lang = detect(content)
        return lang.upper()  # e.g., 'EN', 'FR'
    except Exception:
        return "Unknown"


def print_language_table():
    """List all .txt files in extracted_text with their detected language."""
    if not os.path.isdir(EXTRACTED_TEXT_DIR):
        print(f"Directory not found: {EXTRACTED_TEXT_DIR}")
        return

    files = [f for f in os.listdir(EXTRACTED_TEXT_DIR) if f.endswith(".txt")]
    if not files:
        print("No .txt files found in extracted_text.")
        return

    # Build table rows
    rows = []
    for filename in sorted(files):
        file_path = os.path.join(EXTRACTED_TEXT_DIR, filename)
        lang = detect_language_file(file_path)
        rows.append((filename, lang))

    # Determine column widths
    max_name_len = max(len(row[0]) for row in rows)
    max_lang_len = max(len(row[1]) for row in rows)

    # Print header
    print("\n=== LANGUAGE DETECTION TABLE (extracted_text) ===\n")
    print(f"{'File Name'.ljust(max_name_len)}  {'Language'.ljust(max_lang_len)}")
    print("-" * (max_name_len + max_lang_len + 2))
    for filename, lang in rows:
        print(f"{filename.ljust(max_name_len)}  {lang.ljust(max_lang_len)}")
    print("\n")

# ------------------------------------------------------------------
# Evaluation results table (6 combinations)
# ------------------------------------------------------------------
def print_evaluation_table():
    """Run evaluate() for all granularities and rerank settings,
    then print a comparison table.
    """
    print("\n" + "=" * 60)
    print("         EVALUATION RESULTS – ALL GRANULARITIES")
    print("=" * 60)

    rows = []
    granularities = ["document", "as", "clause"]
    rerank_values = [False, True]

    for gran in granularities:
        for rerank in rerank_values:
            print(f"\nRunning evaluate(granularity={gran}, rerank={rerank}) ...")
            scores = evaluate(use_rerank=rerank, granularity=gran)
            rows.append({
                "granularity": gran,
                "rerank": "With" if rerank else "Without",
                "P@3": scores["precisionAt3"],
                "Hit@3": scores["hitAt3"],
                "R@10": scores["recallAt10"],
                "MRR": scores["mrr"],
                "AvgLen": scores["avg_result_length"],
                "avg_latency_seconds": scores["avg_latency_seconds"],
                "min_latency_seconds": scores["min_latency_seconds"],
                "max_latency_seconds": scores["max_latency_seconds"],
                "query_count": scores["query_count"],
            })

    # ── Print table ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("                   COMPARISON TABLE")
    print("=" * 60)

    header = ["Granularity", "Re-ranking", "P@3", "Hit@3", "R@10", "MRR", "Avg Length"]
    widths = {
        "Granularity": 12,
        "Re-ranking": 12,
        "P@3": 6,
        "Hit@3": 7,
        "R@10": 6,
        "MRR": 6,
        "Avg Length": 10,
    }

    # Header
    line = "|"
    for col in header:
        line += f" {col.ljust(widths[col])} |"
    print(line)
    sep = "|"
    for col in header:
        sep += "-" + "-" * widths[col] + "-|"
    print(sep)

    # Rows
    for row in rows:
        line = "|"
        line += f" {row['granularity'].ljust(widths['Granularity'])} |"
        line += f" {row['rerank'].ljust(widths['Re-ranking'])} |"
        line += f" {row['P@3']:>{widths['P@3']}.3f} |"
        line += f" {row['Hit@3']:>{widths['Hit@3']}.3f} |"
        line += f" {row['R@10']:>{widths['R@10']}.3f} |"
        line += f" {row['MRR']:>{widths['MRR']}.3f} |"
        line += f" {row['AvgLen']:>{widths['Avg Length']}.1f} |"
        print(line)

    print("\n" + "=" * 60)
    print_latency_table(rows)


def get_latency_rows():
    """Run quiet evaluations and collect latency for all granularities."""
    rows = []
    granularities = ["document", "as", "clause"]
    rerank_values = [False, True]

    for gran in granularities:
        for rerank in rerank_values:
            scores = evaluate(use_rerank=rerank, granularity=gran, verbose=False)
            rows.append({
                "granularity": gran,
                "rerank": "With" if rerank else "Without",
                "avg_latency_seconds": scores["avg_latency_seconds"],
                "min_latency_seconds": scores["min_latency_seconds"],
                "max_latency_seconds": scores["max_latency_seconds"],
                "query_count": scores["query_count"],
            })

    return rows


def print_latency_table(evaluation_rows=None):
    """Print average search latency per granularity in seconds."""
    if evaluation_rows is None:
        evaluation_rows = get_latency_rows()

    rows = latency_per_granularity(evaluation_rows)

    print("\n" + "=" * 72)
    print("                  LATENCY PER GRANULARITY")
    print("=" * 72)

    header = ["Granularity", "Re-ranking", "Queries", "Avg sec", "Min sec", "Max sec"]
    widths = {
        "Granularity": 12,
        "Re-ranking": 12,
        "Queries": 7,
        "Avg sec": 10,
        "Min sec": 10,
        "Max sec": 10,
    }

    line = "|"
    for col in header:
        line += f" {col.ljust(widths[col])} |"
    print(line)

    sep = "|"
    for col in header:
        sep += "-" + "-" * widths[col] + "-|"
    print(sep)

    for row in rows:
        line = "|"
        line += f" {row['granularity'].ljust(widths['Granularity'])} |"
        line += f" {row['rerank'].ljust(widths['Re-ranking'])} |"
        line += f" {row['query_count']:>{widths['Queries']}} |"
        line += f" {row['avg_latency_seconds']:>{widths['Avg sec']}.4f} |"
        line += f" {row['min_latency_seconds']:>{widths['Min sec']}.4f} |"
        line += f" {row['max_latency_seconds']:>{widths['Max sec']}.4f} |"
        print(line)

    print("\n" + "=" * 72)


def main():
    # print("\n=== DATA CHECK: CAMEROON LEGAL CORPUS ===\n")

    # # 1. Count files in legal_units_as
    # count_as = count_txt_files(LEGAL_UNITS_AS_DIR)
    # print(f"[1] Number of .txt files in data/legal_units_as/: {count_as}\n")

    # # 2. Print language table for extracted_text
    # print_language_table()
    print_latency_table()


if __name__ == "__main__":
    main()
