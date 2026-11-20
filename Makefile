.PHONY: install test lint fetch run sample evaluate run-api demo
install:   ; pip install -e ".[dev,snowflake]"
test:      ; pytest -q --cov=dispute_triage
lint:      ; ruff check src tests
fetch:     ; triage fetch --limit 5000 --since 2023-01-01
run:       ; triage run --input data/raw/complaints.jsonl
sample:    ; triage sample -n 300
evaluate:  ; triage evaluate --gold data/labels/gold_labels.csv
run-api:   ; uvicorn dispute_triage.api.main:app --reload
demo:      ; TRIAGE_CLASSIFIER=rules triage run --input tests/fixtures/sample_complaints.jsonl
