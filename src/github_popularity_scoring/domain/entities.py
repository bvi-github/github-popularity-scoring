from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Repository:
    name: str
    language: str
    updated_at: datetime
    stars: int
    forks: int
    html_url: str


@dataclass
class RepositorySearchCriteria:
    language: str
    created_after: date
    limit: int = 10

    def __post_init__(self):
        object.__setattr__(self, "language", self.language.strip())


@dataclass
class ScoredRepository:
    repository: Repository
    popularity_score: float
