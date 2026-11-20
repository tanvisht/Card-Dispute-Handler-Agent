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


def _page(*ids):
    return {"hits": {"hits": [{"_source": {"complaint_id": i, "date_received": "2026-01-01",
                                           "product": "Credit card", "complaint_what_happened": "x"}} for i in ids]}}


def test_retries_on_429_then_succeeds():
    responses = iter([httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(503),
                      httpx.Response(200, json=_page("1")), httpx.Response(200, json={"hits": {"hits": []}})])
    slept = []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: next(responses)))
    out = list(fetch_from_api(limit=5, client=client, sleep=slept.append))
    assert [c.complaint_id for c in out] == ["1"]
    assert slept == [2.0, 2.0]  # Retry-After honoured, then backoff 1*2**1


def test_gives_up_after_max_attempts():
    import pytest
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        list(fetch_from_api(limit=5, client=client, sleep=lambda s: None))


def test_dedupes_overlapping_pages():
    pages = iter([_page("1", "2"), _page("2", "3"), {"hits": {"hits": []}}])
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=next(pages))))
    out = list(fetch_from_api(limit=10, page_size=2, client=client))
    assert [c.complaint_id for c in out] == ["1", "2", "3"]
