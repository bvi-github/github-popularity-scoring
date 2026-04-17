from __future__ import annotations
from functools import lru_cache
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from github_popularity_scoring.domain.enums_ import ScoringStrategyName


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )

    github_api_base_url: str = "https://api.github.com"
    github_api_version: str = "2026-03-10"
    github_token: str | None = None
    github_timeout_seconds: float = 10.0
    scanned_repo_limit: int = Field(default=300, ge=1, le=1000)
    result_limit: int = Field(default=10, ge=1, le=1000)
    scoring_strategy: ScoringStrategyName = ScoringStrategyName.BALANCED

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()