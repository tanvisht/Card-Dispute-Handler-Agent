import pytest

from dispute_triage.classify.prompts import SYSTEM_PROMPT, TRIAGE_TOOL
from dispute_triage.taxonomy import (
    FRAUD_ROOT_CAUSES,
    REASON_CODES,
    ROOT_CAUSE_DESCRIPTIONS,
    Priority,
    RootCause,
    reason_codes_for,
)

EXPECTED = {
    RootCause.UNAUTHORIZED_CARD_NOT_PRESENT: ("10.4", "4837"),
    RootCause.UNAUTHORIZED_CARD_PRESENT: ("10.3", "4837"),
    RootCause.ACCOUNT_TAKEOVER: ("10.4", "4837"),
    RootCause.MERCHANDISE_NOT_RECEIVED: ("13.1", "4853"),
    RootCause.NOT_AS_DESCRIBED: ("13.3", "4853"),
    RootCause.CREDIT_NOT_PROCESSED: ("13.6", "4853"),
    RootCause.CANCELLED_RECURRING: ("13.2", "4841"),
    RootCause.DUPLICATE_PROCESSING: ("12.6.1", "4834"),
    RootCause.INCORRECT_AMOUNT: ("12.5", "4834"),
    RootCause.PAID_BY_OTHER_MEANS: ("12.6.2", "4834"),
    RootCause.DISPUTE_PROCESS_FAILURE: ("N/A", "N/A"),
    RootCause.OTHER: ("N/A", "N/A"),
}


@pytest.mark.parametrize("root", list(RootCause))
def test_every_root_cause_has_reason_codes_and_description(root):
    codes = reason_codes_for(root)
    assert (codes["visa_reason_code"], codes["mastercard_reason_code"]) == EXPECTED[root]
    assert codes["reason_code_label"]
    assert root in ROOT_CAUSE_DESCRIPTIONS
    assert root.value in SYSTEM_PROMPT


def test_maps_are_exhaustive():
    assert set(REASON_CODES) == set(RootCause) == set(ROOT_CAUSE_DESCRIPTIONS)


def test_tool_schema_enums_match_taxonomy():
    props = TRIAGE_TOOL["input_schema"]["properties"]
    assert props["root_cause"]["enum"] == [r.value for r in RootCause]
    assert props["priority"]["enum"] == [p.value for p in Priority]


def test_fraud_set_is_exactly_the_unauthorized_causes():
    assert {r for r in FRAUD_ROOT_CAUSES} == {
        RootCause.UNAUTHORIZED_CARD_NOT_PRESENT, RootCause.UNAUTHORIZED_CARD_PRESENT, RootCause.ACCOUNT_TAKEOVER}
