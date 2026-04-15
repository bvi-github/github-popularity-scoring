from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


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


class SearchRepositoriesRequest(BaseModel):
    language: str = Field(min_length=1, max_length=100)
    created_after: date
    limit: int = Field(default=10, ge=1, le=100)
