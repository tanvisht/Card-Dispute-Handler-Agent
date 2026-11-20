"""Score classifier output against a hand-labeled gold set and check acceptance criteria.

Gold file: CSV with columns complaint_id, gold_root_cause, gold_priority[, labeler, notes]
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ..models import Classification
from ..taxonomy import FRAUD_ROOT_CAUSES, Priority, RootCause

# Documented in docs/ACCEPTANCE_CRITERIA.md - keep in sync.
ACCEPTANCE = {
    "root_cause_accuracy": 0.85,
    "priority_accuracy": 0.80,
    "fraud_recall": 0.95,          # missing a fraud case is the costliest error
    "p1_recall": 0.90,
    "auto_triaged_accuracy": 0.92,  # accuracy on cases NOT flagged for review
    "max_review_rate": 0.35,       # analysts can absorb at most ~1/3 of volume
}


@dataclass
class Report:
    n: int
    metrics: dict[str, float]
    per_class: dict[str, dict[str, float]]
    confusion: dict[str, dict[str, int]]
    acceptance: dict[str, dict] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(v["pass"] for v in self.acceptance.values())

    def to_json(self) -> str:
        return json.dumps({**self.__dict__, "passed": self.passed}, indent=2)


def load_gold(path: str) -> dict[str, tuple[RootCause, Priority]]:
    with open(path, newline="", encoding="utf-8") as f:
        return {r["complaint_id"]: (RootCause(r["gold_root_cause"]), Priority(r["gold_priority"]))
                for r in csv.DictReader(f) if r.get("gold_root_cause")}


def _safe(a: float, b: float) -> float:
    return round(a / b, 4) if b else 0.0


def evaluate(preds: list[Classification], gold: dict[str, tuple[RootCause, Priority]]) -> Report:
    pairs = [(p, gold[p.complaint_id]) for p in preds if p.complaint_id in gold]
    if not pairs:
        raise ValueError("no overlap between predictions and gold labels")
    n = len(pairs)
    rc_ok = [p.root_cause == g[0] for p, g in pairs]
    pr_ok = [p.priority == g[1] for p, g in pairs]

    gold_fraud = [(p, g) for p, g in pairs if g[0] in FRAUD_ROOT_CAUSES]
    gold_p1 = [(p, g) for p, g in pairs if g[1] == Priority.P1]
    auto = [(p, g) for p, g in pairs if not p.needs_human_review]

    metrics = {
        "root_cause_accuracy": _safe(sum(rc_ok), n),
        "priority_accuracy": _safe(sum(pr_ok), n),
        "fraud_recall": _safe(sum(p.is_fraud for p, _ in gold_fraud), len(gold_fraud)),
        "p1_recall": _safe(sum(p.priority == Priority.P1 for p, _ in gold_p1), len(gold_p1)),
        "auto_triaged_accuracy": _safe(sum(p.root_cause == g[0] for p, g in auto), len(auto)),
        "review_rate": _safe(sum(p.needs_human_review for p, _ in pairs), n),
        "reason_code_accuracy": _safe(sum(p.visa_reason_code == _visa(g[0]) for p, g in pairs), n),
    }

    confusion: dict[str, Counter] = defaultdict(Counter)
    for p, g in pairs:
        confusion[g[0].value][p.root_cause.value] += 1
    per_class = {}
    for rc in RootCause:
        tp = confusion[rc.value][rc.value]
        fp = sum(confusion[g][rc.value] for g in confusion if g != rc.value)
        fn = sum(confusion[rc.value].values()) - tp
        if tp + fp + fn == 0:
            continue
        prec, rec = _safe(tp, tp + fp), _safe(tp, tp + fn)
        per_class[rc.value] = {"support": tp + fn, "precision": prec, "recall": rec,
                               "f1": _safe(2 * prec * rec, prec + rec)}

    acceptance = {}
    for k, thr in ACCEPTANCE.items():
        val = metrics["review_rate"] if k == "max_review_rate" else metrics[k]
        ok = val <= thr if k.startswith("max_") else val >= thr
        acceptance[k] = {"threshold": thr, "actual": val, "pass": ok}

    return Report(n=n, metrics=metrics, per_class=per_class,
                  confusion={k: dict(v) for k, v in confusion.items()}, acceptance=acceptance)


def _visa(rc: RootCause) -> str:
    from ..taxonomy import REASON_CODES
    return REASON_CODES[rc][0]


def to_markdown(r: Report) -> str:
    lines = [f"# Evaluation report (n={r.n})", "", f"**Overall: {'PASS' if r.passed else 'FAIL'}**", "",
             "| Criterion | Threshold | Actual | Result |", "|---|---|---|---|"]
    for k, v in r.acceptance.items():
        op = "<=" if k.startswith("max_") else ">="
        lines.append(f"| {k} | {op} {v['threshold']} | {v['actual']} | {'PASS' if v['pass'] else 'FAIL'} |")
    lines += ["", "## Per-class", "", "| Root cause | Support | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    for k, v in sorted(r.per_class.items(), key=lambda kv: -kv[1]["support"]):
        lines.append(f"| {k} | {v['support']} | {v['precision']} | {v['recall']} | {v['f1']} |")
    return "\n".join(lines) + "\n"
