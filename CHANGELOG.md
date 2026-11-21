# Changelog

All notable changes to this project. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.

## [1.1.0] - 2026-11-21
### Added
- **Ingest**: CFPB API retries with exponential backoff on 429/5xx (honours `Retry-After`) and complaint-id de-duplication across pages.
- **Evaluation**:
  - Cohen's kappa for double-labeled gold sets (`triage agreement`)
  - confidence calibration (reliability bins + ECE) in the eval report
- **Rules baseline**: money-amount extractor (`$3,450.00`, `1,200 dollars`, `USD 950`) drives the ≥ $1,000 P1 rule and ignores CFPB-redacted amounts.
- **Prompt v2**: four worked examples covering the hardest boundary cases. `PROMPT_VERSION` is bumped to `v2`.
- **LLM cost tracking**: input, output, and cache-read tokens stored per classification, plus the Snowflake `V_LLM_USAGE` view.
- **API**:
  - optional `X-API-Key` auth (`TRIAGE_API_KEY`)
  - `X-Request-ID` and `Server-Timing` headers
  - `GET /v1/cases/export` CSV download with formula-injection protection
- **Snowflake**: `RAW_COMPLAINTS_STREAM`, `V_PENDING_CLASSIFICATION`, `SP_RUN_DQ_CHECKS` + `DQ_RESULTS`, daily `TASK_DAILY_DQ`, `MART.V_DQ_LATEST`.
- **Power BI**: `powerbi/theme.json` with semantic priority colours, and a Data Health page.
- **Dev experience**: pre-commit hooks, `CONTRIBUTING.md`, taxonomy/reason-code/SQL-vocabulary sync tests.

## [1.0.0] - 2026-11-19
### Added
- **Pipeline and storage**:
  - CFPB complaint ingest (API + bulk CSV)
  - Claude classifier with forced tool use and guardrails, plus a keyword baseline
  - SQLite/Snowflake repositories
  - concurrent, resumable pipeline
- **API**: FastAPI service with classify, ingest, case queue, analyst review, and metrics endpoints.
- **Snowflake SQL**: DDL, `MART` views (aging, recurring issues, trends, model quality), idempotent `MERGE`, DQ checks.
- **Evaluation**: gold-set evaluation with acceptance criteria as code, stratified labeling sampler, UAT scripts, Power BI spec, CI, Docker.
