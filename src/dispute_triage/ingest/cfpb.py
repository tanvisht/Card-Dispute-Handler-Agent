"""Ingest public complaints from the CFPB Consumer Complaint Database.

Source: https://www.consumerfinance.gov/data-research/consumer-complaints/
API docs: https://cfpb.github.io/api/ccdb/api.html

Only complaints where the consumer opted in to publish a narrative are used
(`has_narrative=true`); the CFPB scrubs PII from narratives (e.g. "XXXX").
"""
from __future__ import annotations

import csv
import logging
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path

import httpx

from ..models import Complaint

log = logging.getLogger(__name__)

CFPB_API = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"

# Products/issues that carry card dispute and card fraud complaints.
# "Credit card or prepaid card" was split into "Credit card" and "Prepaid card" in 2023.
DEFAULT_PRODUCTS = ["Credit card", "Credit card or prepaid card", "Prepaid card"]
DEFAULT_ISSUES = [
    "Problem with a purchase shown on your statement",
    "Unauthorized transactions or other transaction problem",
    "Fraud or scam",
    "Problem with a company's investigation into an existing problem",
]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def record_to_complaint(src: dict) -> Complaint | None:
    """Map a CFPB API `_source` dict or CSV row to a Complaint. Returns None if no narrative."""
    narrative = src.get("complaint_what_happened") or src.get("Consumer complaint narrative") or ""
    if not narrative.strip():
        return None
    g = lambda api_key, csv_key: src.get(api_key) or src.get(csv_key) or None
    return Complaint(
        complaint_id=str(g("complaint_id", "Complaint ID")),
        date_received=_parse_date(g("date_received", "Date received")),
        product=g("product", "Product") or "",
        sub_product=g("sub_product", "Sub-product"),
        issue=g("issue", "Issue"),
        sub_issue=g("sub_issue", "Sub-issue"),
        narrative=narrative.strip(),
        company=g("company", "Company"),
        state=g("state", "State"),
        submitted_via=g("submitted_via", "Submitted via"),
        company_response=g("company_response", "Company response to consumer"),
        timely=g("timely", "Timely response?"),
        date_sent_to_company=_parse_date(g("date_sent_to_company", "Date sent to company")),
    )


def fetch_from_api(
    limit: int = 5000,
    date_min: str = "2023-01-01",
    date_max: str | None = None,
    products: list[str] | None = None,
    issues: list[str] | None = None,
    page_size: int = 500,
    client: httpx.Client | None = None,
) -> Iterator[Complaint]:
    """Page through the CFPB search API and yield complaints that have narratives."""
    own = client is None
    client = client or httpx.Client(timeout=60, headers={"User-Agent": "dispute-triage/1.0"})
    params: list[tuple[str, str]] = [
        ("has_narrative", "true"),
        ("date_received_min", date_min),
        ("sort", "created_date_desc"),
        ("no_aggs", "true"),
        ("format", "json"),
    ]
    if date_max:
        params.append(("date_received_max", date_max))
    params += [("product", p) for p in (products or DEFAULT_PRODUCTS)]
    params += [("issue", i) for i in (issues or DEFAULT_ISSUES)]

    yielded, frm = 0, 0
    try:
        while yielded < limit:
            resp = client.get(CFPB_API, params=params + [("size", str(page_size)), ("frm", str(frm))])
            resp.raise_for_status()
            payload = resp.json()
            hits = payload["hits"]["hits"] if isinstance(payload, dict) else payload
            if not hits:
                break
            for h in hits:
                c = record_to_complaint(h.get("_source", h))
                if c:
                    yield c
                    yielded += 1
                    if yielded >= limit:
                        break
            frm += page_size
            log.info("fetched %s complaints", yielded)
    finally:
        if own:
            client.close()


def read_csv(path: str | Path, limit: int | None = None) -> Iterator[Complaint]:
    """Read the CFPB bulk export (complaints.csv) or a filtered extract."""
    with open(path, newline="", encoding="utf-8") as f:
        n = 0
        for row in csv.DictReader(f):
            c = record_to_complaint(row)
            if c and c.product in DEFAULT_PRODUCTS:
                yield c
                n += 1
                if limit and n >= limit:
                    return


def write_jsonl(complaints: Iterable[Complaint], path: str | Path) -> int:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for c in complaints:
            f.write(c.model_dump_json() + "\n")
            n += 1
    return n


def read_jsonl(path: str | Path) -> list[Complaint]:
    with open(path, encoding="utf-8") as f:
        return [Complaint.model_validate_json(line) for line in f if line.strip()]
