"""Keyword baseline. Used offline, in CI, and as a sanity floor for the LLM."""
from __future__ import annotations

import re

from ..models import Complaint
from ..taxonomy import Priority, RootCause
from ..textutils import max_amount
from .base import Classifier, RawLabel

# Ordered: first strong match wins ties.
PATTERNS: list[tuple[RootCause, list[str]]] = [
    (RootCause.ACCOUNT_TAKEOVER, [r"chang\w* (my )?(address|email|phone)", r"opened .* in my name",
                                  r"identity theft", r"authorized user .* (added|without)", r"took over"]),
    (RootCause.DUPLICATE_PROCESSING, [r"charged twice", r"double[- ]charged", r"duplicate (charge|transaction)",
                                      r"same (charge|transaction) (twice|two times)"]),
    (RootCause.CANCELLED_RECURRING, [r"subscription", r"recurring", r"after (i )?cancel", r"membership",
                                     r"auto[- ]?renew"]),
    (RootCause.CREDIT_NOT_PROCESSED, [r"refund", r"returned (the|it|them)", r"credit (was )?never (posted|issued)",
                                      r"promised (a )?credit"]),
    (RootCause.MERCHANDISE_NOT_RECEIVED, [r"never (received|arrived|delivered|showed)", r"not (been )?delivered",
                                          r"did not receive", r"didn'?t receive", r"never provided"]),
    (RootCause.NOT_AS_DESCRIBED, [r"defective", r"counterfeit", r"not as described", r"broken", r"damaged",
                                  r"(fake|wrong) (item|product)"]),
    (RootCause.INCORRECT_AMOUNT, [r"wrong amount", r"overcharged", r"charged more than", r"incorrect amount"]),
    (RootCause.PAID_BY_OTHER_MEANS, [r"paid (in )?cash", r"paid .* (another|different) (card|method)",
                                     r"already paid"]),
    (RootCause.UNAUTHORIZED_CARD_PRESENT, [r"(lost|stolen) (my )?(card|wallet|purse)", r"skimm", r"in[- ]store"]),
    (RootCause.UNAUTHORIZED_CARD_NOT_PRESENT, [r"unauthori[sz]ed", r"did not (make|authorize)", r"didn'?t (make|authorize)",
                                               r"fraudulent", r"not recogni[sz]e", r"\bfraud\b", r"online"]),
]
PROCESS_FAILURE = [r"provisional credit", r"(denied|closed) (my|the) (dispute|claim)", r"never investigat",
                   r"no response", r"reversed the credit", r"60 days", r"regulation (z|e)", r"fair credit billing"]
P1_SIGNALS = [r"elderly", r"\bdisab", r"\bveteran", r"collections?", r"credit (report|score)",
              r"lawyer|attorney|lawsuit", r"identity theft", r"still happening|ongoing"]
P1_AMOUNT = 1000.0


def _hits(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text))


class RulesClassifier(Classifier):
    name = "rules:v1"

    def _predict(self, complaint: Complaint) -> RawLabel:
        text = complaint.narrative.lower()
        scores = {rc: _hits(text, pats) for rc, pats in PATTERNS}
        best, best_score = max(scores.items(), key=lambda kv: kv[1])
        process = _hits(text, PROCESS_FAILURE)

        if best_score == 0 and process == 0:
            root, conf = RootCause.OTHER, 0.3
        elif process >= 2 and process >= best_score:
            root, conf = RootCause.DISPUTE_PROCESS_FAILURE, 0.6
        else:
            root = best
            runner_up = sorted(scores.values())[-2]
            conf = 0.55 + 0.1 * min(best_score - runner_up, 3)

        p1 = _hits(text, P1_SIGNALS) + (max_amount(text) >= P1_AMOUNT)
        priority = Priority.P1 if p1 >= 1 else (Priority.P3 if root == RootCause.OTHER else Priority.P2)
        return RawLabel(root_cause=root.value, priority=priority.value, confidence=conf,
                        rationale=f"keyword scores={ {k.value: v for k, v in scores.items() if v} } process={process}",
                        evidence_quote=None)
