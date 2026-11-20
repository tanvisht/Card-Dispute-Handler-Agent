from types import SimpleNamespace

from dispute_triage.classify.base import finalize
from dispute_triage.classify.llm import LLMClassifier
from dispute_triage.classify.rules import RulesClassifier
from dispute_triage.taxonomy import Priority, RootCause


def test_rules_baseline_on_fixtures(settings, complaints):
    clf = RulesClassifier(settings)
    by_id = {c.complaint_id: clf.classify(c) for c in complaints}
    assert by_id["T003"].root_cause == RootCause.DUPLICATE_PROCESSING
    assert by_id["T003"].visa_reason_code == "12.6.1"
    assert by_id["T006"].root_cause == RootCause.ACCOUNT_TAKEOVER
    assert by_id["T006"].priority == Priority.P1 and by_id["T006"].is_fraud


def test_guardrails_flag_low_confidence_and_hallucinated_quote(settings, complaints):
    c = complaints[0]
    out = finalize(c, {"root_cause": "unauthorized_card_not_present", "priority": "P2", "confidence": 0.5,
                       "rationale": "x", "evidence_quote": "this text is not in the narrative"}, "t", settings)
    assert out.needs_human_review
    assert any(r.startswith("low_confidence") for r in out.review_reasons)
    assert "evidence_quote_not_found_in_narrative" in out.review_reasons
    assert out.evidence_quote is None


def test_high_confidence_clean_case_is_auto_triaged(settings, complaints):
    c = complaints[1]
    out = finalize(c, {"root_cause": "merchandise_not_received", "priority": "P2", "confidence": 0.93,
                       "rationale": "never arrived", "evidence_quote": "The order never arrived"}, "t", settings)
    assert not out.needs_human_review and out.visa_reason_code == "13.1" and out.mastercard_reason_code == "4853"


def test_llm_classifier_uses_forced_tool_call(settings, complaints):
    captured = {}

    class FakeMessages:
        def create(self, **kw):
            captured.update(kw)
            return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input={
                "root_cause": "duplicate_processing", "priority": "P2", "confidence": 0.95,
                "rationale": "charged twice", "evidence_quote": "I was charged twice"})])

    clf = LLMClassifier(settings, client=SimpleNamespace(messages=FakeMessages()))
    out = clf.classify(complaints[2])
    assert out.root_cause == RootCause.DUPLICATE_PROCESSING and not out.needs_human_review
    assert captured["tool_choice"] == {"type": "tool", "name": "record_triage"}
    assert captured["temperature"] == 0
