"""FastAPI service: ad-hoc classification, case queue, human review, dashboard metrics."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from .. import __version__
from ..classify import Classifier, get_classifier
from ..models import Classification, ClassifyRequest, Complaint, ReviewDecision
from ..pipeline import run
from ..storage import Repository, get_repository
from ..taxonomy import Priority, RootCause

app = FastAPI(title="Dispute Triage Copilot", version=__version__,
              description="LLM triage of CFPB card dispute & fraud complaints.")


@lru_cache
def repo_dep() -> Repository:
    return get_repository()


@lru_cache
def classifier_dep() -> Classifier:
    return get_classifier()


Repo = Annotated[Repository, Depends(repo_dep)]
Clf = Annotated[Classifier, Depends(classifier_dep)]


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.post("/v1/classify", response_model=Classification)
def classify(req: ClassifyRequest, clf: Clf):
    """Classify one narrative without persisting it."""
    c = Complaint(complaint_id=req.complaint_id, date_received=datetime.now(UTC).date(), product=req.product,
                  issue=req.issue, sub_issue=req.sub_issue, narrative=req.narrative)
    return clf.classify(c)


@app.post("/v1/complaints/ingest")
def ingest(complaints: list[Complaint], repo: Repo, clf: Clf):
    """Load complaints into RAW_COMPLAINTS and classify any not yet classified (idempotent)."""
    if len(complaints) > 1000:
        raise HTTPException(413, "max 1000 complaints per request; use the CLI for bulk loads")
    return run(repo, clf, complaints)


def _row(r: dict) -> dict:
    if isinstance(r.get("review_reasons"), str):
        r["review_reasons"] = json.loads(r["review_reasons"])
    for k in ("is_fraud", "needs_human_review"):
        if k in r and r[k] is not None:
            r[k] = bool(r[k])
    return r


@app.get("/v1/cases")
def list_cases(repo: Repo,
               status: str | None = Query(None, pattern="^(PENDING_REVIEW|AUTO_TRIAGED|REVIEWED)$"),
               priority: Priority | None = None, root_cause: RootCause | None = None,
               limit: int = Query(50, le=500), offset: int = 0):
    sql, args = "SELECT * FROM v_cases WHERE 1=1", []
    if status:
        sql += " AND case_status = ?"; args.append(status)
    if priority:
        sql += " AND priority = ?"; args.append(priority.value)
    if root_cause:
        sql += " AND root_cause = ?"; args.append(root_cause.value)
    sql += " ORDER BY priority ASC, age_days DESC LIMIT ? OFFSET ?"
    args += [limit, offset]
    return [_row(r) for r in repo.query(sql, tuple(args))]


@app.get("/v1/cases/{complaint_id}")
def get_case(complaint_id: str, repo: Repo):
    rows = repo.query("SELECT * FROM v_cases WHERE complaint_id = ?", (complaint_id,))
    if not rows:
        raise HTTPException(404, "case not found")
    return _row(rows[0])


@app.post("/v1/cases/{complaint_id}/review")
def review(complaint_id: str, decision: ReviewDecision, repo: Repo):
    if not repo.query("SELECT 1 FROM v_cases WHERE complaint_id = ?", (complaint_id,)):
        raise HTTPException(404, "case not found")
    repo.record_review(complaint_id, decision)
    return get_case(complaint_id, repo)


@app.get("/v1/metrics/summary")
def summary(repo: Repo):
    """Headline numbers the Power BI dashboard also shows (handy for smoke tests)."""
    q = repo.query
    return {
        "total_cases": q("SELECT COUNT(*) n FROM v_cases")[0]["n"],
        "by_status": q("SELECT case_status, COUNT(*) n FROM v_cases GROUP BY 1 ORDER BY 2 DESC"),
        "by_priority": q("SELECT priority, COUNT(*) n FROM v_cases GROUP BY 1 ORDER BY 1"),
        "by_root_cause": q("SELECT root_cause, COUNT(*) n FROM v_cases GROUP BY 1 ORDER BY 2 DESC"),
        "review_rate": q("SELECT ROUND(AVG(needs_human_review), 3) r FROM v_cases")[0]["r"],
        "aging_buckets": q("""SELECT CASE WHEN age_days <= 15 THEN '0-15' WHEN age_days <= 30 THEN '16-30'
                              WHEN age_days <= 60 THEN '31-60' ELSE '60+' END bucket, COUNT(*) n
                              FROM v_cases WHERE case_status = 'PENDING_REVIEW' GROUP BY 1 ORDER BY 1"""),
    }
