# Acceptance Criteria

Thresholds are enforced in code by `src/dispute_triage/evaluation/evaluate.py::ACCEPTANCE`.
`triage evaluate` exits non-zero if any criterion fails, so it can gate a release in CI.

| ID | Criterion | Threshold | Why |
|----|-----------|-----------|-----|
| AC-1 | Root-cause accuracy vs. gold set | ≥ 0.85 | Primary quality bar for routing |
| AC-2 | Priority accuracy | ≥ 0.80 | SLA routing |
| AC-3 | Fraud recall (gold fraud predicted as any fraud cause) | ≥ 0.95 | A missed fraud case is the most expensive error |
| AC-4 | P1 recall | ≥ 0.90 | Regulatory/vulnerable-consumer cases must not be under-prioritised |
| AC-5 | Accuracy on auto-triaged (not flagged) cases | ≥ 0.92 | Proves the review flag catches the risky cases |
| AC-6 | Human-review rate | ≤ 0.35 | Analyst capacity |
| AC-7 | 100% of outputs schema-valid (enum root cause, confidence in [0,1]) | hard | Enforced by forced tool use + Pydantic |
| AC-8 | Evidence quote is verbatim from narrative, or the case is flagged | hard | Hallucination guard (`finalize()`) |
| AC-9 | Re-ingesting the same batch creates no duplicate classifications | hard | Idempotency (`test_ingest_idempotent_then_review_flow`) |
| AC-10 | Every P1 case enters the review queue | hard | `p1_requires_analyst_signoff` rule |

## Gold set protocol
* 300 complaints drawn with `triage sample -n 300` (stratified by CFPB issue/sub-issue, seed 42).
* Each labeled independently by 2 people using `docs/LABELING_GUIDE.md`. Disagreements are adjudicated by a third person.
* Report Cohen's kappa for the two labelers next to the model score. Model accuracy can't be read meaningfully above human agreement.
* The gold set is **frozen**. Prompt iterations are tuned on a separate dev sample to avoid overfitting the test set.
