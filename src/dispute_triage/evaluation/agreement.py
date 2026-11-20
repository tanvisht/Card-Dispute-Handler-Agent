"""Inter-annotator agreement for the gold set.

Model accuracy is only meaningful relative to how often two humans agree.
Labeling sheet columns: complaint_id, labeler_a_root_cause, labeler_b_root_cause
(and optionally labeler_a_priority, labeler_b_priority).
"""
from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Sequence


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Cohen's kappa for two raters over nominal labels. Returns 1.0 for perfect agreement."""
    if len(a) != len(b) or not a:
        raise ValueError("label lists must be non-empty and the same length")
    n = len(a)
    p_obs = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    p_exp = sum(ca[k] * cb[k] for k in ca.keys() | cb.keys()) / (n * n)
    if p_exp == 1.0:
        return 1.0
    return round((p_obs - p_exp) / (1 - p_exp), 4)


def agreement_from_csv(path: str, field: str = "root_cause") -> dict:
    """Read a double-labeled sheet and return raw agreement, kappa and disagreeing ids."""
    a, b, ids = [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            la, lb = r.get(f"labeler_a_{field}"), r.get(f"labeler_b_{field}")
            if la and lb:
                a.append(la.strip())
                b.append(lb.strip())
                ids.append(r["complaint_id"])
    return {
        "field": field,
        "n": len(a),
        "raw_agreement": round(sum(x == y for x, y in zip(a, b)) / len(a), 4) if a else 0.0,
        "cohens_kappa": cohens_kappa(a, b) if a else 0.0,
        "to_adjudicate": [i for i, x, y in zip(ids, a, b) if x != y],
    }
