from __future__ import annotations
from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )

    github_api_base_url: str = "https://api.github.com"
    github_api_version: str = "2026-03-10"
    github_token: str | None = None
    github_timeout_seconds: float = 10.0
    default_result_limit: int = Field(default=10, ge=1, le=100)
    max_result_limit: int = Field(default=50, ge=1, le=100)
    scoring_strategy: Literal["balanced", "momentum"] = "balanced"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()