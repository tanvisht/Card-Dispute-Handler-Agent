# Contributing

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
make install                     # editable install with dev + snowflake extras
pip install pre-commit && pre-commit install
```

## Workflow
1. Branch from `main`: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
2. Keep changes small and covered by tests. `make test` and `make lint` must pass. CI runs both on Python 3.11 and 3.12.
3. Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`.
4. Open a PR and describe what changed, why, and how you tested it.

## Changing the taxonomy
Root causes live in `src/dispute_triage/taxonomy.py`. When you add or rename one, also update:
- `REASON_CODES` and `ROOT_CAUSE_DESCRIPTIONS` (the tests in `tests/test_taxonomy.py` fail otherwise)
- the vocabulary lists in `sql/snowflake/04_data_quality.sql` and `05_streams_tasks.sql` (checked by `tests/test_sql_files.py`)
- `docs/LABELING_GUIDE.md` and the README taxonomy table

## Changing the prompt
- Edit `src/dispute_triage/classify/prompts.py` and **bump `PROMPT_VERSION`** (and the default in `config.py`).
- Re-run `make evaluate` on the frozen gold set and paste the summary table into the PR.
- Never tune on the gold set itself. Use a separate dev sample (`triage sample --out data/labels/dev.csv`).

## Data rules
- Only public CFPB data. Never commit raw extracts (`data/raw/` is git-ignored) or `.env` files.
- Fixtures in `tests/fixtures/` are synthetic and must stay clearly labeled as such.
