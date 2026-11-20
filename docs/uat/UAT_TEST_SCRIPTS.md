# UAT Test Scripts

Run against a local stack (`make run-api`) loaded with `make demo`. Record Pass/Fail plus the tester and date.

| ID | Scenario | Steps | Expected result | AC |
|----|----------|-------|-----------------|----|
| UAT-01 | Health check | `GET /health` | 200, `{"status":"ok"}` | n/a |
| UAT-02 | Classify a clear duplicate charge | `POST /v1/classify` with the narrative from fixture T003 | `root_cause=duplicate_processing`, `visa_reason_code=12.6.1`, `mastercard_reason_code=4834` | AC-1 |
| UAT-03 | Account takeover is P1 and queued | Ingest fixtures; `GET /v1/cases/T006` | `priority=P1`, `is_fraud=true`, `case_status=PENDING_REVIEW`, `review_reasons` contains `p1_requires_analyst_signoff` | AC-4, AC-10 |
| UAT-04 | Short narrative gets flagged | `POST /v1/classify` `{"narrative":"charged twice"}` | `needs_human_review=true`, `short_narrative` in reasons | AC-5 |
| UAT-05 | Idempotent ingest | `POST /v1/complaints/ingest` with the same body twice | 2nd response `classified=0`, `skipped_already_done=10` | AC-9 |
| UAT-06 | Analyst override | `POST /v1/cases/T008/review` with a new root cause | `case_status=REVIEWED`, the view shows the analyst's label, `model_root_cause` is unchanged | n/a |
| UAT-07 | Queue filters | `GET /v1/cases?status=PENDING_REVIEW&priority=P1` | Only P1 pending cases, oldest first | n/a |
| UAT-08 | Bad input rejected | `POST /v1/classify` `{"narrative":""}` | 422 | AC-7 |
| UAT-09 | Invalid enum on review | `POST /v1/cases/T001/review` with `root_cause="foo"` | 422 | AC-7 |
| UAT-10 | Dashboard numbers reconcile | Compare `GET /v1/metrics/summary` with Power BI card totals | Totals match | n/a |
| UAT-11 | Offline evaluation gate | `triage evaluate` on the gold set | Report written to `reports/`; exit 0 only if every AC passes | AC-1..6 |

Automated equivalents live in `tests/test_api.py` and `tests/test_classify.py`.
