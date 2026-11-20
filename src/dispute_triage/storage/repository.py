"""Storage layer. SQLite for local dev/tests, Snowflake for the shared warehouse.

Both backends expose the same tables (see sql/snowflake/01_tables.sql):
  RAW_COMPLAINTS, CLASSIFICATIONS, REVIEW_DECISIONS, CASES
"""
from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from ..config import Settings, get_settings
from ..models import Classification, Complaint, ReviewDecision

COMPLAINT_COLS = list(Complaint.model_fields)
CLASS_COLS = [c for c in Classification.model_fields]


def complaints_df(complaints: list[Complaint]) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump(mode="json") for c in complaints], columns=COMPLAINT_COLS)


def classifications_df(items: list[Classification]) -> pd.DataFrame:
    rows = []
    for c in items:
        d = c.model_dump(mode="json")
        d["review_reasons"] = json.dumps(d["review_reasons"])
        rows.append(d)
    return pd.DataFrame(rows, columns=CLASS_COLS)


class Repository(ABC):
    @abstractmethod
    def upsert_complaints(self, complaints: list[Complaint]) -> int: ...
    @abstractmethod
    def insert_classifications(self, items: list[Classification]) -> int: ...
    @abstractmethod
    def record_review(self, complaint_id: str, decision: ReviewDecision) -> None: ...
    @abstractmethod
    def query(self, sql: str, params: tuple = ()) -> list[dict]: ...
    @abstractmethod
    def unclassified_ids(self) -> list[str]: ...


SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS raw_complaints (
  complaint_id TEXT PRIMARY KEY, date_received TEXT, product TEXT, sub_product TEXT, issue TEXT,
  sub_issue TEXT, narrative TEXT, company TEXT, state TEXT, submitted_via TEXT,
  company_response TEXT, timely TEXT, date_sent_to_company TEXT,
  loaded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS classifications (
  complaint_id TEXT, root_cause TEXT, visa_reason_code TEXT, mastercard_reason_code TEXT,
  reason_code_label TEXT, priority TEXT, is_fraud INTEGER, confidence REAL, rationale TEXT,
  evidence_quote TEXT, needs_human_review INTEGER, review_reasons TEXT, classifier TEXT,
  prompt_version TEXT, classified_at TEXT);
CREATE TABLE IF NOT EXISTS review_decisions (
  complaint_id TEXT, reviewer TEXT, root_cause TEXT, priority TEXT, notes TEXT,
  reviewed_at TEXT DEFAULT CURRENT_TIMESTAMP);
-- Latest classification per complaint, with human override applied and case status derived.
CREATE VIEW IF NOT EXISTS v_cases AS
WITH latest AS (
  SELECT * FROM (SELECT c.*, ROW_NUMBER() OVER (PARTITION BY complaint_id ORDER BY classified_at DESC) rn
                 FROM classifications c) WHERE rn = 1),
rev AS (
  SELECT * FROM (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY complaint_id ORDER BY reviewed_at DESC) rn
                 FROM review_decisions r) WHERE rn = 1)
SELECT r.complaint_id, r.date_received, r.company, r.state, r.issue, r.sub_issue,
       COALESCE(rev.root_cause, l.root_cause) AS root_cause,
       COALESCE(rev.priority, l.priority)     AS priority,
       l.root_cause AS model_root_cause, l.priority AS model_priority,
       l.visa_reason_code, l.mastercard_reason_code, l.is_fraud, l.confidence,
       l.needs_human_review, l.review_reasons, l.rationale, l.classifier,
       CASE WHEN rev.complaint_id IS NOT NULL THEN 'REVIEWED'
            WHEN l.needs_human_review = 1 THEN 'PENDING_REVIEW'
            ELSE 'AUTO_TRIAGED' END AS case_status,
       CAST(julianday('now') - julianday(r.date_received) AS INTEGER) AS age_days
FROM raw_complaints r JOIN latest l USING (complaint_id) LEFT JOIN rev USING (complaint_id);
"""


class SQLiteRepository(Repository):
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SQLITE_DDL)

    def upsert_complaints(self, complaints):
        df = complaints_df(complaints)
        cols = ",".join(COMPLAINT_COLS)
        ph = ",".join("?" * len(COMPLAINT_COLS))
        self.conn.executemany(f"INSERT OR REPLACE INTO raw_complaints ({cols}) VALUES ({ph})",
                              df.where(df.notna(), None).values.tolist())
        self.conn.commit()
        return len(df)

    def insert_classifications(self, items):
        df = classifications_df(items)
        df["is_fraud"] = df["is_fraud"].astype(int)
        df["needs_human_review"] = df["needs_human_review"].astype(int)
        cols = ",".join(CLASS_COLS)
        ph = ",".join("?" * len(CLASS_COLS))
        self.conn.executemany(f"INSERT INTO classifications ({cols}) VALUES ({ph})",
                              df.where(df.notna(), None).values.tolist())
        self.conn.commit()
        return len(df)

    def record_review(self, complaint_id, decision):
        self.conn.execute(
            "INSERT INTO review_decisions (complaint_id, reviewer, root_cause, priority, notes) VALUES (?,?,?,?,?)",
            (complaint_id, decision.reviewer, decision.root_cause.value, decision.priority.value, decision.notes))
        self.conn.commit()

    def query(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def unclassified_ids(self):
        return [r["complaint_id"] for r in self.query(
            "SELECT complaint_id FROM raw_complaints WHERE complaint_id NOT IN (SELECT complaint_id FROM classifications)")]

    def get_complaint(self, complaint_id: str) -> Complaint | None:
        rows = self.query("SELECT * FROM raw_complaints WHERE complaint_id = ?", (complaint_id,))
        if not rows:
            return None
        rows[0].pop("loaded_at", None)
        return Complaint.model_validate(rows[0])


class SnowflakeRepository(Repository):
    """Writes via write_pandas into staging tables, then MERGE (idempotent loads)."""

    def __init__(self, s: Settings):
        import snowflake.connector  # optional dependency
        self.conn = snowflake.connector.connect(
            account=s.snowflake_account, user=s.snowflake_user, password=s.snowflake_password,
            role=s.snowflake_role, warehouse=s.snowflake_warehouse,
            database=s.snowflake_database, schema=s.snowflake_schema)

    def _write(self, df: pd.DataFrame, table: str) -> int:
        from snowflake.connector.pandas_tools import write_pandas
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]
        ok, _, nrows, _ = write_pandas(self.conn, df, table, overwrite=False, quote_identifiers=False)
        if not ok:
            raise RuntimeError(f"write_pandas into {table} failed")
        return nrows

    def upsert_complaints(self, complaints):
        n = self._write(complaints_df(complaints), "STG_COMPLAINTS")
        self.conn.cursor().execute("CALL SP_MERGE_COMPLAINTS()")  # see sql/snowflake/03_procedures.sql
        return n

    def insert_classifications(self, items):
        return self._write(classifications_df(items), "CLASSIFICATIONS")

    def record_review(self, complaint_id, decision):
        self.conn.cursor().execute(
            "INSERT INTO REVIEW_DECISIONS (COMPLAINT_ID, REVIEWER, ROOT_CAUSE, PRIORITY, NOTES) VALUES (%s,%s,%s,%s,%s)",
            (complaint_id, decision.reviewer, decision.root_cause.value, decision.priority.value, decision.notes))

    def query(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def unclassified_ids(self):
        return [r["complaint_id"] for r in self.query(
            "SELECT COMPLAINT_ID FROM RAW_COMPLAINTS WHERE COMPLAINT_ID NOT IN (SELECT COMPLAINT_ID FROM CLASSIFICATIONS)")]

    def get_complaint(self, complaint_id):
        rows = self.query("SELECT * FROM RAW_COMPLAINTS WHERE COMPLAINT_ID = ?", (complaint_id,))
        if not rows:
            return None
        rows[0].pop("loaded_at", None)
        return Complaint.model_validate(rows[0])


def get_repository(settings: Settings | None = None) -> Repository:
    s = settings or get_settings()
    if s.triage_storage == "snowflake":
        return SnowflakeRepository(s)
    return SQLiteRepository(s.triage_sqlite_path)
