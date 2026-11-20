import pytest
from fastapi.testclient import TestClient

from dispute_triage.api.main import app, classifier_dep, repo_dep
from dispute_triage.classify.rules import RulesClassifier
from dispute_triage.storage.repository import SQLiteRepository


@pytest.fixture
def client(settings):
    repo, clf = SQLiteRepository(":memory:"), RulesClassifier(settings)
    app.dependency_overrides[repo_dep] = lambda: repo
    app.dependency_overrides[classifier_dep] = lambda: clf
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_classify_adhoc(client):
    r = client.post("/v1/classify", json={"narrative": "I was charged twice for the same dinner."})
    assert r.status_code == 200 and r.json()["root_cause"] == "duplicate_processing"
    assert r.json()["needs_human_review"]  # short narrative -> review


def test_ingest_idempotent_then_review_flow(client, complaints):
    body = [c.model_dump(mode="json") for c in complaints]
    first = client.post("/v1/complaints/ingest", json=body).json()
    assert first["classified"] == 10
    again = client.post("/v1/complaints/ingest", json=body).json()
    assert again["classified"] == 0 and again["skipped_already_done"] == 10

    pending = client.get("/v1/cases", params={"status": "PENDING_REVIEW"}).json()
    assert pending, "P1 cases must land in the review queue"
    cid = pending[0]["complaint_id"]
    r = client.post(f"/v1/cases/{cid}/review",
                    json={"reviewer": "analyst1", "root_cause": "account_takeover", "priority": "P1"})
    assert r.json()["case_status"] == "REVIEWED" and r.json()["root_cause"] == "account_takeover"

    s = client.get("/v1/metrics/summary").json()
    assert s["total_cases"] == 10


def test_unknown_case_404(client):
    assert client.get("/v1/cases/nope").status_code == 404


def test_request_id_echoed_and_generated(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123" and r.headers["Server-Timing"].startswith("app;dur=")
    assert len(client.get("/health").headers["X-Request-ID"]) == 32


def test_api_key_enforced_when_configured(client, monkeypatch):
    from dispute_triage.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("TRIAGE_API_KEY", "s3cret")
    try:
        assert client.get("/v1/cases").status_code == 401
        assert client.get("/v1/cases", headers={"X-API-Key": "wrong"}).status_code == 401
        assert client.get("/v1/cases", headers={"X-API-Key": "s3cret"}).status_code == 200
        assert client.get("/health").status_code == 200  # liveness stays open
    finally:
        get_settings.cache_clear()


def test_export_csv(client, complaints):
    import csv as _csv
    import io as _io
    client.post("/v1/complaints/ingest", json=[c.model_dump(mode="json") for c in complaints])
    r = client.get("/v1/cases/export")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(_csv.DictReader(_io.StringIO(r.text)))
    assert len(rows) == 10 and "visa_reason_code" in rows[0]
    p1 = client.get("/v1/cases/export", params={"priority": "P1"}).text
    assert all(row["priority"] == "P1" for row in _csv.DictReader(_io.StringIO(p1)))


def test_csv_formula_injection_neutralised():
    from dispute_triage.api.main import _csv_safe
    assert _csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)" and _csv_safe("Bank A") == "Bank A"
    assert _csv_safe(3) == 3
