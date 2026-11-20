"""Static checks on the Snowflake scripts (no Snowflake connection needed)."""
from pathlib import Path

import pytest

from dispute_triage.taxonomy import RootCause

SQL = Path(__file__).resolve().parents[1] / "sql" / "snowflake"


def test_scripts_are_numbered_in_run_order():
    names = sorted(p.name for p in SQL.glob("*.sql"))
    assert names[0].startswith("00_") and any(n.startswith("05_") for n in names)


@pytest.mark.parametrize("fname", ["04_data_quality.sql", "05_streams_tasks.sql"])
def test_dq_vocabulary_matches_taxonomy(fname):
    text = (SQL / fname).read_text()
    for rc in RootCause:
        assert f"'{rc.value}'" in text, f"{rc.value} missing from {fname}"


def test_stream_task_and_dq_view_defined():
    text = (SQL / "05_streams_tasks.sql").read_text()
    for obj in ("STREAM RAW_COMPLAINTS_STREAM", "TASK TASK_DAILY_DQ", "PROCEDURE SP_RUN_DQ_CHECKS",
                "VIEW MART.V_DQ_LATEST"):
        assert obj in text
