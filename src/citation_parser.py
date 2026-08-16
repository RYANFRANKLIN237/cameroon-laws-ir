"""
Conservative citation parser for Cameroon legal queries.

Only returns a citation when BOTH a unit number and a statute hint
are present, so concept queries stay on the TF-IDF path.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Longer aliases first for greedy matching
STATUTE_ALIAS_PATTERNS: list[tuple[str, str]] = [
    ("code du travail", "labor_code"),
    ("labour code", "labor_code"),
    ("labor code", "labor_code"),
    ("code penal", "penal_code"),
    ("code pénal", "penal_code"),
    ("penal code", "penal_code"),
    ("code general des impots", "tax_code"),
    ("code général des impôts", "tax_code"),
    ("tax code", "tax_code"),
    ("fiscal law", "fiscal_law"),
    ("local fiscal", "fiscal_law"),
    ("electoral code", "electoral_code"),
    ("code electoral", "electoral_code"),
    ("code électoral", "electoral_code"),
    ("highway code", "highway_code"),
    ("code de la route", "highway_code"),
    ("human rights commission", "hrc"),
    ("carte nationale", "national_id"),
    ("regime foncier", "land_regime"),
    ("régime foncier", "land_regime"),
    ("constitution", "constitution"),
]


UNIT_TYPE_RE = re.compile(
    r"\b(section|article|art\.?)\b",
    re.IGNORECASE,
)

# section 32 / article premier / art. 14
UNIT_NUMBER_RE = re.compile(
    r"\b(?:section|article|art\.?)\s+"
    r"(premier|premi[eè]re|\d+)\b",
    re.IGNORECASE,
)

# Trailing (3) or (c) right after the unit number: section 80(3)
INLINE_CLAUSE_RE = re.compile(
    r"\b(?:section|article|art\.?)\s+"
    r"(?:premier|premi[eè]re|\d+)\s*"
    r"[\(\[]\s*([a-z]{1,4}|\d+|iii|ii|iv|ix|vi{0,3}|i{1,3})\s*[\)\]]",
    re.IGNORECASE,
)

# Explicit subdivision markers. "sub" is treated as clause/paragraph.
# EN: sub, subsection, clause, paragraph, para.
# FR: sous-section, sous-alinéa, clause, paragraphe, alinéa, al.
CLAUSE_RE = re.compile(
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
        |
        \b(?:paragr|para)\b
    )
    \s*
    [\(\[]?\s*
    ([a-z]{1,4}|\d+|iii|ii|iv|ix|vi{0,3}|i{1,3})
    \s*[\)\]]?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_unit_number(raw: str) -> str:
    value = raw.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    if value in {"premier", "premiere"}:
        return "premier"
    return re.sub(r"^0+(\d)", r"\1", value)


def _normalize_clause_id(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    value = raw.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    roman = {
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
    }
    if value in roman:
        # Keep both possibilities available via lookup; store arabic primary
        return roman[value]
    if re.fullmatch(r"[a-z]+", value) and len(value) <= 3:
        return value
    if value.isdigit():
        return str(int(value))
    return value


def _detect_clause_id(query: str) -> Optional[str]:
    inline = INLINE_CLAUSE_RE.search(query)
    if inline:
        return _normalize_clause_id(inline.group(1))

    for text in (query, normalize_text(query)):
        clause_match = CLAUSE_RE.search(text)
        if clause_match:
            return _normalize_clause_id(clause_match.group(1))
    return None


def _detect_unit_type(query: str) -> Optional[str]:
    match = UNIT_TYPE_RE.search(query)
    if not match:
        return None
    token = match.group(1).lower().rstrip(".")
    if token.startswith("art"):
        return "article"
    return "section"


def _detect_statute_key(query: str) -> Optional[str]:
    normalized = normalize_text(query)
    # Also keep accented original lower for patterns with accents
    lowered = query.lower()
    for alias, key in STATUTE_ALIAS_PATTERNS:
        alias_norm = normalize_text(alias)
        if alias_norm and alias_norm in normalized:
            return key
        if alias.lower() in lowered:
            return key
    return None


def parse_citation(query: str) -> Optional[dict]:
    """
    Parse a citation query.

    Returns None unless both unit_number and statute_hint/key are found.
    """
    if not query or not query.strip():
        return None

    unit_match = UNIT_NUMBER_RE.search(query)
    if not unit_match:
        return None

    statute_key = _detect_statute_key(query)
    if not statute_key:
        return None

    unit_type = _detect_unit_type(query) or "section"
    unit_number = _normalize_unit_number(unit_match.group(1))
    clause_id = _detect_clause_id(query)

    return {
        "unit_type": unit_type,
        "unit_number": unit_number,
        "clause_id": clause_id,
        "statute_key": statute_key,
        "raw_query": query.strip(),
    }
