from pathlib import Path

import pytest

from dispute_triage.config import Settings
from dispute_triage.ingest.cfpb import read_jsonl

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings():
    return Settings(triage_classifier="rules", triage_storage="sqlite", triage_sqlite_path=":memory:",
                    anthropic_api_key=None, _env_file=None)


@pytest.fixture
def complaints():
    return read_jsonl(FIX / "sample_complaints.jsonl")
