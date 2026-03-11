def infer_law_type(filename: str) -> str:
    name = filename.lower()

    if "constitution" in name:
        return "constitution"

    if "code" in name:
        return "code"

    if (
        "law no" in name
        or "law of" in name
        or "act no" in name
        or "loi n" in name
        or "loi du" in name
        or "loi de" in name
    ):
        return "ordinary_law"

    if "decree" in name or "décret" in name:
        return "decree"

    return "unknown"


def infer_unit_type(filename: str) -> str:
    name = filename.lower()

    if "clause_" in name and not "clause_full" in name:
        return "clause"

    if "_section_" in name:
        return "section"

    if "_article_" in name:
        return "article"

    return "document"


#Kelsen’s Pyramid

LAW_TYPE_WEIGHT = {
    "constitution": 1.5,
    "code": 1.3,
    "ordinary_law": 1.1,
    "decree": 1.0,
    "unknown": 0.8
}



UNIT_TYPE_WEIGHT = {
    "clause": 1.2,
    "section": 1.05,
    "article": 1.05,
    "document": 0.85
}

