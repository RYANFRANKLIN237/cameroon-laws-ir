from src.legal_metadata import infer_law_type, infer_unit_type, LAW_TYPE_WEIGHT


def compute_length_signal(text):
    """
    Converts document length into a small ranking signal.

    Legal units that are too short are usually fragments.
    Medium-length clauses are usually most informative.
    """
    word_count = len(text.split())

    if word_count < 25:
        return -0.03

    elif 25 <= word_count <= 150:
        return 0.02

    elif 150 < word_count <= 400:
        return 0.015

    else:
        return -0.01


def detect_target_law(query):
    """
    Detect explicit law references in query.
    """
    query_lower = query.lower()

    law_targets = {
        "penal": ["penal", "pénal"],
        "labor": ["labor", "labour", "travail"],
        "electoral": ["electoral", "électoral"],
        "tax": ["tax", "fiscal", "impôt", "impot"],
        "constitution": ["constitution", "constitutionnel"]
    }

    for key, synonyms in law_targets.items():
        if any(s in query_lower for s in synonyms):
            return key

    return None


def rerank_results(results, query=None):
    """
    Lightweight legal-aware reranker.

    IMPORTANT:
    Uses additive signals so it does not destroy the
    hybrid retrieval ranking.
    """

    if not query:
        return results

    target_law = detect_target_law(query)

    reranked = []

    for r in results:

        base_score = r["score"]
        unit_id = r["unit_id"].lower()
        text = r["text"]

        law_type = infer_law_type(unit_id)
        unit_type = infer_unit_type(unit_id)

        final_score = base_score

        # -----------------------------
        # 1️⃣ Explicit law targeting
        # -----------------------------
        if target_law and target_law in unit_id:
            final_score += 0.05

        # -----------------------------
        # 2️⃣ Legal hierarchy signal
        # -----------------------------
        hierarchy_weight = LAW_TYPE_WEIGHT.get(law_type, 1.0)

        hierarchy_signal = (hierarchy_weight - 1.0) * 0.02
        final_score += hierarchy_signal

        # -----------------------------
        # 3️⃣ Clause preference
        # -----------------------------
        if unit_type == "clause":
            final_score += 0.03

        elif unit_type == "document":
            final_score -= 0.03

        # -----------------------------
        # 4️⃣ Length signal
        # -----------------------------
        length_signal = compute_length_signal(text)
        final_score += length_signal

        reranked.append({
            **r,
            "law_type": law_type,
            "unit_type": unit_type,
            "length_signal": length_signal,
            "final_score": final_score
        })

    reranked.sort(key=lambda x: x["final_score"], reverse=True)

    return reranked