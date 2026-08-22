"""
Detect inline legal cross-references in clause body text (EN + FR).

Cue phrases (subject to, notwithstanding, …) are not links; they only
mark nearby numbered citations as dependencies.
"""
from __future__ import annotations

import re
from typing import Optional

from src.citation_parser import (
    _detect_statute_key,
    normalize_clause_id,
    normalize_unit_number,
)

CLAUSE_TOKEN = r"(?:[a-z]{1,4}|\d+|x|ix|viii|vii|vi|iv|v|iii|ii|i)"

NUMBERED_UNIT_RE = re.compile(
    r"""
    \b(?:section|article|art\.?)\s+
    (premier|premi[eè]re|\d+)
    (?:
        \s*
        [\(\[]\s*
        (""" + CLAUSE_TOKEN + r""")
        \s*[\)\]]
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)

SUBDIVISION_RE = re.compile(
    r"""
    (?:
        \b(?:
            sous[\s-]+sections?
            | sous[\s-]+alin[eé]as?
            | sub(?:[\s-]*sections?)?
            | paragraphes?
            | paragraphs?
            | clauses?
            | alin[eé]as?
        )\b
        |
        \b(?:paragr|para|al)\.
    )
    \s*
    [\(\[]?\s*
    (""" + CLAUSE_TOKEN + r""")
    \s*[\)\]]?
    """,
    re.IGNORECASE | re.VERBOSE,
)

RELATIVE_RE = re.compile(
    r"""
    \b(?:
        this\s+section
        | this\s+article
        | le\s+pr[eé]sent\s+article
        | la\s+pr[eé]sente\s+section
        | the\s+foregoing
        | the\s+preceding
        | ci-dessus
        | ci-dessous
        | above
        | below
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

CUE_RE = re.compile(
    r"""
    \b(?:
        subject\s+to
        | provided\s+that
        | notwithstanding
        | except
        | sous\s+r[eé]serve(?:\s+de|\s+que)?
        | nonobstant
        | sauf
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

CUE_WINDOW = 40
STATUTE_WINDOW = 80


def _unit_type_from_surface(surface: str) -> Optional[str]:
    lowered = surface.lower()
    if lowered.startswith("art"):
        return "article"
    if "section" in lowered:
        return "section"
    if "article" in lowered or "présent article" in lowered or "present article" in lowered:
        return "article"
    return None


def _relative_kind(surface: str) -> Optional[str]:
    lowered = surface.lower()
    if lowered in {"this section", "this article", "le présent article", "le present article",
                   "la présente section", "la presente section"}:
        return "parent"
    if lowered in {"the foregoing", "the preceding", "above", "ci-dessus"}:
        return "previous"
    if lowered in {"below", "ci-dessous"}:
        return "next"
    return None


def _has_cue_before(text: str, start: int) -> bool:
    window = text[max(0, start - CUE_WINDOW):start]
    return bool(CUE_RE.search(window))


def _statute_near(text: str, start: int, end: int) -> Optional[str]:
    window = text[start:min(len(text), end + STATUTE_WINDOW)]
    return _detect_statute_key(window)


def _dedupe_spans(spans: list[dict]) -> list[dict]:
    spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    kept = []
    last_end = -1
    for span in spans:
        if span["start"] < last_end:
            continue
        kept.append(span)
        last_end = span["end"]
    return kept


def find_cross_refs(text: str) -> list[dict]:
    """Return non-overlapping citation/relative spans in clause text."""
    if not text:
        return []

    spans: list[dict] = []

    for match in NUMBERED_UNIT_RE.finditer(text):
        surface = match.group(0)
        unit_type = _unit_type_from_surface(surface) or "section"
        spans.append({
            "start": match.start(),
            "end": match.end(),
            "surface": surface,
            "unit_type": unit_type,
            "unit_number": normalize_unit_number(match.group(1)),
            "clause_id": normalize_clause_id(match.group(2)) if match.group(2) else None,
            "relative": None,
            "kind": "dependency" if _has_cue_before(text, match.start()) else "citation",
            "statute_key": _statute_near(text, match.start(), match.end()),
        })

    for match in SUBDIVISION_RE.finditer(text):
        surface = match.group(0)
        spans.append({
            "start": match.start(),
            "end": match.end(),
            "surface": surface,
            "unit_type": None,
            "unit_number": None,
            "clause_id": normalize_clause_id(match.group(1)),
            "relative": None,
            "kind": "dependency" if _has_cue_before(text, match.start()) else "citation",
            "statute_key": None,
        })

    for match in RELATIVE_RE.finditer(text):
        surface = match.group(0)
        relative = _relative_kind(surface)
        if not relative:
            continue
        spans.append({
            "start": match.start(),
            "end": match.end(),
            "surface": surface,
            "unit_type": _unit_type_from_surface(surface),
            "unit_number": None,
            "clause_id": None,
            "relative": relative,
            "kind": "relative",
            "statute_key": None,
        })

    return _dedupe_spans(spans)
