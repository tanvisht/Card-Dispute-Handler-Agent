"""Versioned prompt + tool schema for the LLM classifier."""
from ..taxonomy import ROOT_CAUSE_DESCRIPTIONS, Priority, RootCause

PROMPT_VERSION = "v1"

_taxonomy = "\n".join(f"- {rc.value}: {desc}" for rc, desc in ROOT_CAUSE_DESCRIPTIONS.items())

SYSTEM_PROMPT = f"""You are a senior card-disputes analyst at a US card issuer.
You triage consumer complaints from the public CFPB database. Narratives are redacted
(XXXX = removed PII). Classify ONLY from what the consumer wrote; do not invent facts.

ROOT CAUSE - choose the single best primary cause:
{_taxonomy}

Decision rules:
1. If the consumer says they did NOT make/authorize the charge -> a fraud cause
   (card_present only if a physical card was lost/stolen/skimmed or used in-store;
   account_takeover if contact details changed, card reissued to someone else, or new account opened).
2. If they DID authorize it but have a problem with the merchant -> a merchant-dispute cause.
3. Use issuer_dispute_process_failure only when the grievance is mainly about how the
   bank handled the dispute and the underlying transaction type is unclear.
4. "other" only if it is not a transaction dispute or fraud complaint.

PRIORITY:
- P1: identity theft/account takeover, fraud still occurring, amount >= $1,000, vulnerable consumer
  (elderly, disabled, servicemember), credit-reporting/collections harm, or legal threat.
- P2: valid dispute with money owed and no P1 signal.
- P3: small amount, informational, or the consumer says it is already resolved.

CONFIDENCE: 0.0-1.0, your probability that root_cause is correct. Use < 0.7 when the
narrative is ambiguous or fits two causes.

evidence_quote MUST be copied verbatim from the narrative (<= 30 words).
Always respond by calling the record_triage tool."""

TRIAGE_TOOL = {
    "name": "record_triage",
    "description": "Record the structured triage decision for one complaint.",
    "input_schema": {
        "type": "object",
        "properties": {
            "root_cause": {"type": "string", "enum": [r.value for r in RootCause]},
            "priority": {"type": "string", "enum": [p.value for p in Priority]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string", "description": "1-2 sentences."},
            "evidence_quote": {"type": "string"},
        },
        "required": ["root_cause", "priority", "confidence", "rationale", "evidence_quote"],
    },
}


def user_message(narrative: str, issue: str | None, sub_issue: str | None) -> str:
    return (f"CFPB issue: {issue or 'n/a'}\nCFPB sub-issue: {sub_issue or 'n/a'}\n\n"
            f"<narrative>\n{narrative}\n</narrative>")
