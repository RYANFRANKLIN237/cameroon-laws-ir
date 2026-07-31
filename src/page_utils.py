"""
Shared helpers for PDF page markers and unit location metadata.
"""
import json
import os
import re

PAGE_MARKER_RE = re.compile(r"<<<PAGE\s+(\d+)>>>")
METADATA_DIR = os.path.join("data", "metadata")

GRANULARITY_META_FILES = {
    "clause": "units_clause.jsonl",
    "as": "units_as.jsonl",
    "document": "units_document.jsonl",
}


def make_page_marker(page_num: int, leading_newline: bool = False) -> str:
    marker = f"<<<PAGE {page_num}>>>\n"
    if leading_newline:
        return "\n" + marker
    return marker


def join_pages_with_markers(extracted_pages: list[str]) -> tuple[str, dict]:
    """
    Join per-page strings with <<<PAGE N>>> markers.
    Returns (marked_text, pages_payload) where pages_payload has
    char offsets into marked_text for each page body.
    """
    chunks = []
    pages_meta = []
    offset = 0

    for page_num, page_text in enumerate(extracted_pages, start=1):
        marker = make_page_marker(page_num, leading_newline=(page_num > 1))
        chunks.append(marker)
        offset += len(marker)

        start = offset
        chunks.append(page_text)
        offset += len(page_text)

        pages_meta.append({
            "page": page_num,
            "char_start": start,
            "char_end": offset,
        })

    return "".join(chunks), {
        "pages": pages_meta,
        "page_count": len(extracted_pages),
    }


def strip_page_markers(text: str) -> str:
    if not text:
        return text
    cleaned = PAGE_MARKER_RE.sub("", text)
    # Collapse leftover blank lines from removed markers
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def page_at_offset(text: str, offset: int) -> int:
    """Return 1-based page number for a character offset in marked text."""
    page = 1
    for match in PAGE_MARKER_RE.finditer(text):
        if match.start() <= offset:
            page = int(match.group(1))
        else:
            break
    return page


def page_span_for_range(text: str, start: int, end: int) -> tuple[int, int]:
    if end <= start:
        page = page_at_offset(text, start)
        return page, page
    page_start = page_at_offset(text, start)
    page_end = page_at_offset(text, max(start, end - 1))
    return page_start, page_end


def make_highlight_quote(text: str, max_len: int = 100) -> str:
    cleaned = strip_page_markers(text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rstrip()


def meta_path_for(granularity: str) -> str:
    filename = GRANULARITY_META_FILES[granularity]
    return os.path.join(METADATA_DIR, filename)


def write_jsonl(path: str, records: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_unit_metadata(granularity: str) -> dict[str, dict]:
    """
    Load unit_id -> location metadata for a granularity.
    Returns {} if the file is missing.
    """
    path = meta_path_for(granularity)
    if not os.path.exists(path):
        return {}

    lookup = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            unit_id = record.get("unit_id")
            if unit_id:
                lookup[unit_id] = record
    return lookup


def source_pdf_from_stem(stem: str) -> str:
    return f"{stem}.pdf"
