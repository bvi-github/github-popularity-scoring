from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubRepositoryDTO(BaseModel):
    name: str
    language: str | None = None
    stargazers_count: int = Field(ge=0)
    forks_count: int = Field(ge=0)
    updated_at: datetime
    html_url: str


class GitHubSearchRepositoriesResponseDTO(BaseModel):
    total_count: int = Field(ge=0)
    incomplete_results: bool
    items: list[GitHubRepositoryDTO]
