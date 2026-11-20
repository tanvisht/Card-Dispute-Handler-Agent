import json

import httpx

from dispute_triage.ingest.cfpb import fetch_from_api, record_to_complaint
from tests.conftest import FIX


def test_api_paging_skips_empty_narratives():
    page = json.loads((FIX / "cfpb_api_page.json").read_text())
    calls = []

    def handler(req: httpx.Request):
        calls.append(req.url)
        return httpx.Response(200, json=page if len(calls) == 1 else {"hits": {"hits": []}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = list(fetch_from_api(limit=10, client=client))
    assert [c.complaint_id for c in out] == ["9000001"]
    assert out[0].date_received.isoformat() == "2026-05-02"
    assert "has_narrative=true" in str(calls[0])


def test_csv_row_mapping():
    c = record_to_complaint({"Complaint ID": "1", "Date received": "2025-01-02", "Product": "Credit card",
                             "Consumer complaint narrative": "  charged twice  "})
    assert c.complaint_id == "1" and c.narrative == "charged twice"
