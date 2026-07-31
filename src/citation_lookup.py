"""
Citation index and lookup for clause-level legal units.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Optional

from src.citation_parser import normalize_text
from src.legal_metadata import infer_law_type, infer_unit_type
from src.utils import CONFIG

# statute_key -> substrings that identify source stems (normalized)
STATUTE_STEM_HINTS: dict[str, list[str]] = {
    "labor_code": ["labor code", "labour code", "92 007"],
    "penal_code": ["penal code"],
    "tax_code": ["tax code"],
    "fiscal_law": ["fiscal law", "2009 019"],
    "electoral_code": ["electoral code", "electoral"],
    "highway_code": ["highway code", "2022 007"],
    "constitution": [
        "constitution of 2 june",
        "constitution du 02 juin",
        "amend the constitution",
        "revision de la constitution",
        "amending constitution",
        "modification de la constitution",
    ],
    "hrc": ["human rights commission"],
    "national_id": ["carte nationale"],
    "land_regime": ["regime foncier"],
}

UNIT_SPLIT_RE = re.compile(
    r"^(.*)_(section|article)_(.+)$",
    re.IGNORECASE,
)


def _parse_filename(unit_id: str) -> Optional[dict]:
    name = unit_id.removesuffix(".txt")
    match = UNIT_SPLIT_RE.match(name)
    if not match:
        return None

    source_raw = match.group(1)
    unit_type = match.group(2).lower()
    rest = match.group(3)
    rest_parts = rest.split("_")
    unit_number = rest_parts[0].lower()
    if unit_number.isdigit():
        unit_number = str(int(unit_number))

    clause_id = "full"
    if len(rest_parts) >= 3 and rest_parts[1].lower() == "clause":
        clause_id = rest_parts[2].lower()
        if clause_id.isdigit():
            clause_id = str(int(clause_id))

    return {
        "unit_id": unit_id,
        "source_raw": source_raw,
        "source_norm": normalize_text(source_raw),
        "unit_type": unit_type,
        "unit_number": unit_number,
        "clause_id": clause_id,
    }


def _extract_marker_span(text: str, clause_id: str) -> Optional[str]:
    """Pull a highlight quote for (3) or (c) inside parent unit text."""
    if not text or not clause_id:
        return None

    patterns = [
        rf"\({re.escape(clause_id)}\)",
        rf"\b{re.escape(clause_id)}\)",
    ]
    # lettered: also allow uppercase
    if re.fullmatch(r"[a-z]+", clause_id):
        patterns.insert(0, rf"\({clause_id.upper()}\)")

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        start = match.start()
        # take from marker to next sibling marker or ~220 chars
        tail = text[start:]
        next_marker = re.search(
            r"\n\s*\(([a-z]|\d+)\)\s",
            tail[len(match.group(0)):],
            flags=re.IGNORECASE,
        )
        if next_marker:
            end = start + len(match.group(0)) + next_marker.start()
            snippet = text[start:end].strip()
        else:
            snippet = text[start:start + 220].strip()
        snippet = re.sub(r"\s+", " ", snippet)
        return snippet[:160] if snippet else None
    return None


class CitationIndex:
    def __init__(self, legal_dir: str):
        self.legal_dir = legal_dir
        # (source_norm, unit_type, unit_number, clause_id) -> [records]
        self.exact: dict[tuple, list[dict]] = {}
        # (source_norm, unit_type, unit_number) -> [records]
        self.by_unit: dict[tuple, list[dict]] = {}
        self.stems_by_key: dict[str, set[str]] = {
            key: set() for key in STATUTE_STEM_HINTS
        }
        self._build()

    def _add(self, record: dict) -> None:
        exact_key = (
            record["source_norm"],
            record["unit_type"],
            record["unit_number"],
            record["clause_id"],
        )
        unit_key = (
            record["source_norm"],
            record["unit_type"],
            record["unit_number"],
        )
        self.exact.setdefault(exact_key, []).append(record)
        self.by_unit.setdefault(unit_key, []).append(record)

        for key, hints in STATUTE_STEM_HINTS.items():
            if any(hint in record["source_norm"] for hint in hints):
                self.stems_by_key[key].add(record["source_norm"])

    def _build(self) -> None:
        if not os.path.isdir(self.legal_dir):
            return
        for filename in os.listdir(self.legal_dir):
            if not filename.endswith(".txt"):
                continue
            parsed = _parse_filename(filename)
            if parsed:
                self._add(parsed)

    def resolve_sources(self, statute_key: str) -> list[str]:
        return sorted(self.stems_by_key.get(statute_key, set()))


def _sort_records(records: list[dict]) -> list[dict]:
    def key_fn(record: dict):
        clause = record["clause_id"]
        # prefer exact numeric/letter clauses before full when listing siblings
        if clause == "full":
            return (1, clause)
        if clause.isdigit():
            return (0, f"{int(clause):05d}")
        return (0, clause)

    # Deduplicate by unit_id preserving order after sort
    seen = set()
    ordered = []
    for record in sorted(records, key=key_fn):
        if record["unit_id"] in seen:
            continue
        seen.add(record["unit_id"])
        ordered.append(record)
    return ordered


def _lookup_on_sources(
    index: CitationIndex,
    sources: list[str],
    unit_type: str,
    unit_number: str,
    clause_id: Optional[str],
) -> tuple[list[dict], str]:
    """
    Returns (records, match_kind).
    match_kind: exact | cross_type | parent | section_all
    """
    other_type = "article" if unit_type == "section" else "section"

    def collect(utype: str, with_clause: bool) -> list[dict]:
        hits = []
        for source in sources:
            if with_clause and clause_id:
                hits.extend(
                    index.exact.get((source, utype, unit_number, clause_id), [])
                )
            else:
                hits.extend(
                    index.by_unit.get((source, utype, unit_number), [])
                )
        return hits

    if clause_id:
        preferred = collect(unit_type, with_clause=True)
        if preferred:
            return _sort_records(preferred), "exact"

        alternate = collect(other_type, with_clause=True)
        if alternate:
            return _sort_records(alternate), "cross_type"

        preferred_parent = collect(unit_type, with_clause=False)
        if preferred_parent:
            return _sort_records(preferred_parent), "parent"

        alternate_parent = collect(other_type, with_clause=False)
        if alternate_parent:
            return _sort_records(alternate_parent), "cross_type"

        return [], "none"

    # No clause: prefer stated type, then also include the other type
    # (important for EN section vs FR article on the same statute).
    preferred = collect(unit_type, with_clause=False)
    alternate = collect(other_type, with_clause=False)
    if preferred and alternate:
        merged = _sort_records(preferred + alternate)
        return merged, "section_all"
    if preferred:
        return _sort_records(preferred), "section_all"
    if alternate:
        return _sort_records(alternate), "cross_type"
    return [], "none"


@lru_cache(maxsize=4)
def get_citation_index(granularity: str = "clause") -> CitationIndex:
    legal_dir = CONFIG[granularity]["legal_dir"]
    return CitationIndex(legal_dir)


def lookup_citation(
    citation: dict,
    granularity: str = "clause",
    top_k: int = 10,
) -> list[dict]:
    """
    Resolve a parsed citation to search-result-shaped dicts.
    Empty list means caller should fall back to concept search.
    """
    index = get_citation_index(granularity)
    sources = index.resolve_sources(citation["statute_key"])
    if not sources:
        return []

    records, match_kind = _lookup_on_sources(
        index,
        sources,
        citation["unit_type"],
        citation["unit_number"],
        citation.get("clause_id"),
    )
    if not records:
        return []

    legal_dir = CONFIG[granularity]["legal_dir"]
    results = []
    requested_clause = citation.get("clause_id")

    for record in records[:top_k]:
        path = os.path.join(legal_dir, record["unit_id"])
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read().strip()
        except OSError:
            continue

        highlight_quote = None
        if (
            requested_clause
            and match_kind in {"parent", "cross_type", "section_all"}
            and record["clause_id"] == "full"
        ):
            highlight_quote = _extract_marker_span(text, requested_clause)

        results.append({
            "unit_id": record["unit_id"],
            "score": 1.0,
            "final_score": 1.0,
            "text": text,
            "law_type": infer_law_type(record["unit_id"]),
            "unit_type": infer_unit_type(record["unit_id"]),
            "language": "en",  # refined later by transform/detect if needed
            "citation_match": match_kind,
            "citation_highlight_quote": highlight_quote,
        })

    return results
