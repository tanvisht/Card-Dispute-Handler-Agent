"""Classifier interface + the shared post-processing (reason codes, review flags)."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from ..config import Settings, get_settings
from ..models import Classification, Complaint
from ..taxonomy import FRAUD_ROOT_CAUSES, Priority, RootCause, reason_codes_for

MIN_NARRATIVE_WORDS = 25


class RawLabel(dict):
    """root_cause, priority, confidence, rationale, evidence_quote."""


class Classifier(ABC):
    name: str

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @abstractmethod
    def _predict(self, complaint: Complaint) -> RawLabel: ...

    def classify(self, complaint: Complaint) -> Classification:
        raw = self._predict(complaint)
        return finalize(complaint, raw, self.name, self.settings)


def finalize(complaint: Complaint, raw: dict, classifier: str, settings: Settings) -> Classification:
    """Deterministic guardrails applied to *any* model output."""
    root = RootCause(raw["root_cause"])
    priority = Priority(raw["priority"])
    confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.0))))
    reasons: list[str] = []

    if confidence < settings.triage_confidence_threshold:
        reasons.append(f"low_confidence<{settings.triage_confidence_threshold}")
    if len(complaint.narrative.split()) < MIN_NARRATIVE_WORDS:
        reasons.append("short_narrative")
    if root == RootCause.OTHER:
        reasons.append("unclassified_root_cause")
    if priority == Priority.P1:
        reasons.append("p1_requires_analyst_signoff")
    quote = raw.get("evidence_quote")
    if quote and _norm(quote) not in _norm(complaint.narrative):
        reasons.append("evidence_quote_not_found_in_narrative")  # hallucination guard
        quote = None

    return Classification(
        complaint_id=complaint.complaint_id,
        root_cause=root,
        priority=priority,
        is_fraud=root in FRAUD_ROOT_CAUSES,
        confidence=round(confidence, 3),
        rationale=raw.get("rationale", "")[:1000],
        evidence_quote=quote,
        needs_human_review=bool(reasons),
        review_reasons=reasons,
        classifier=classifier,
        prompt_version=settings.triage_prompt_version,
        classified_at=datetime.now(UTC),
        **reason_codes_for(root),
    )


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def get_classifier(settings: Settings | None = None) -> Classifier:
    settings = settings or get_settings()
    if settings.triage_classifier == "rules":
        from .rules import RulesClassifier
        return RulesClassifier(settings)
    from .llm import LLMClassifier
    return LLMClassifier(settings)
