from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Repository:
    name: str
    language: str | None
    updated_at: datetime
    stars: int
    forks: int
    html_url: str


@dataclass
class RepositorySearchCursor:
    value: str


@dataclass
class RepositorySearchResult:
    repositories: list[Repository]
    total_count: int
    next_cursor: RepositorySearchCursor | None = None


@dataclass
class RepositorySearchCriteria:
    language: str
    created_after: date
    repositories_scanned: int = 0
    cursor: RepositorySearchCursor | None = None

    def __post_init__(self):
        object.__setattr__(self, "language", self.language.strip())


@dataclass
class ScoredRepository:
    repository: Repository
    popularity_score: float


@dataclass
class ScoringRepositoryResult:
    repositories: list[ScoredRepository]
    total_count: int
    repositories_scanned: int
