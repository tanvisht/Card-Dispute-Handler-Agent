"""Runtime configuration, loaded from environment variables / .env."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    triage_model: str = "claude-sonnet-5-5"
    triage_classifier: Literal["llm", "rules"] = "llm"
    triage_confidence_threshold: float = 0.75
    triage_prompt_version: str = "v2"
    triage_max_narrative_chars: int = 6000

    triage_api_key: str | None = None  # when set, /v1/* requires header X-API-Key

    triage_storage: Literal["sqlite", "snowflake"] = "sqlite"
    triage_sqlite_path: str = "data/triage.db"

    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_password: str | None = None
    snowflake_role: str = "TRIAGE_ROLE"
    snowflake_warehouse: str = "TRIAGE_WH"
    snowflake_database: str = "DISPUTE_TRIAGE"
    snowflake_schema: str = "CORE"


@lru_cache
def get_settings() -> Settings:
    return Settings()
