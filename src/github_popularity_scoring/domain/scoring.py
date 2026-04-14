from __future__ import annotations

from datetime import datetime, timezone
from math import log1p, exp

from typing import Protocol, Optional, Callable

from github_popularity_scoring.domain.entities import Repository


class ScoringStrategy(Protocol):
    """Interface for scoring strategies"""

    def score(self, repository: Repository, now: datetime) -> float:
        """Calculate a popularity score for a repository"""

class BalancedScoringStrategy:
    """Default strategy with balanced wights for stars, forks, and recency"""

    def score(self, repository: Repository, now: datetime) -> float:
        days_since_update = max((now - repository.updated_at).days, 0)

        stars_component = log1p(max(repository.stars, 0)) * 5.0
        forks_component = log1p(max(repository.forks, 0)) * 3.0
        recency_component = exp(-days_since_update / 365.0) * 20.0

        return round(stars_component + forks_component + recency_component, 2)

class PopularityScorer:
    """Scores repositories by delegating to a configured strategy"""

    def __init__(self,
                 strategy: ScoringStrategy | None = None,
                 now_provider: Optional[Callable[[], datetime]] = None,
                 ) -> None:
        self._strategy = strategy or BalancedScoringStrategy()
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def score(self, repository: Repository) -> float:
        now = self._now_provider()
        return self._strategy.score(repository, now=now)