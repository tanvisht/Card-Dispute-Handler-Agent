"""Pydantic domain models shared by the pipeline, storage and API."""
from datetime import date, datetime

from pydantic import BaseModel, Field

from .taxonomy import Priority, RootCause


class Complaint(BaseModel):
    """A single CFPB complaint (subset of the public schema we use)."""

    complaint_id: str
    date_received: date
    product: str
    sub_product: str | None = None
    issue: str | None = None
    sub_issue: str | None = None
    narrative: str = Field(..., description="consumer_complaint_narrative / complaint_what_happened")
    company: str | None = None
    state: str | None = None
    submitted_via: str | None = None
    company_response: str | None = None
    timely: str | None = None
    date_sent_to_company: date | None = None


class Classification(BaseModel):
    """Structured triage output for one complaint."""

    complaint_id: str
    root_cause: RootCause
    visa_reason_code: str
    mastercard_reason_code: str
    reason_code_label: str
    priority: Priority
    is_fraud: bool
    confidence: float = Field(ge=0, le=1)
    rationale: str
    evidence_quote: str | None = None
    needs_human_review: bool
    review_reasons: list[str] = Field(default_factory=list)
    classifier: str  # "llm:<model>" or "rules:v1"
    prompt_version: str
    classified_at: datetime


class ClassifyRequest(BaseModel):
    complaint_id: str = "adhoc"
    narrative: str = Field(..., min_length=1)
    issue: str | None = None
    sub_issue: str | None = None
    product: str = "Credit card"


class ReviewDecision(BaseModel):
    reviewer: str
    root_cause: RootCause
    priority: Priority
    notes: str | None = None
