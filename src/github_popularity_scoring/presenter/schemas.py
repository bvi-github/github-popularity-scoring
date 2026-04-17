from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RepositoryPopularityResponse(BaseModel):
    """
    Scored repository schema
    """

    name: str
    language: str | None
    stars: int
    forks: int
    html_url: str
    updated_at: datetime
    popularity_score: float


class SearchRepositoriesResponse(BaseModel):
    """
    /popularity endpoint response schema
    """

    repositories: list[RepositoryPopularityResponse]
    total_count: int
    repositories_scanned: int
