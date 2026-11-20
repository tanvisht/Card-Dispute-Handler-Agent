import pytest

from dispute_triage.classify.rules import RulesClassifier
from dispute_triage.models import Complaint
from dispute_triage.textutils import extract_amounts, max_amount


@pytest.mark.parametrize("text,expected", [
    ("charged $3,450.00 twice", [3450.0]),
    ("about 1200 dollars", [1200.0]),
    ("USD 950 and $12.5", [950.0, 12.5]),
    ("$ 1,000,000", [1000000.0]),
    ("1,250.75 usd", [1250.75]),
    ("redacted {$XXXX} amount", []),
    ("on 03/12/2026 at 5pm", []),
])
def test_extract_amounts(text, expected):
    assert extract_amounts(text) == expected


def test_max_amount_default_zero():
    assert max_amount("no money here") == 0.0


def test_large_amount_escalates_rules_priority(settings):
    base = "I did not authorize an online charge from a store for a laptop and the bank will not remove it"
    small = Complaint(complaint_id="s", date_received="2026-01-01", product="Credit card",
                      narrative=base + " of $40.")
    big = small.model_copy(update={"complaint_id": "b", "narrative": base + " of 2,300 dollars."})
    clf = RulesClassifier(settings)
    assert clf.classify(small).priority.value == "P2"
    assert clf.classify(big).priority.value == "P1"
