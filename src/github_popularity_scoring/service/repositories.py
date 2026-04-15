from __future__ import annotations

from datetime import date
from typing import Protocol

from github_popularity_scoring.domain.entities import (
    Repository,
    RepositorySearchCriteria,
    ScoredRepository,
)
from github_popularity_scoring.domain.exceptions import ValidationError
from github_popularity_scoring.domain.scoring import PopularityScorer


class RepositorySearchPort(Protocol):
    """
    A contract for searching repositories.
    It inverts the use case dependency on GitHub-specific search logic.
    """

    async def search_repositories(
        self, criteria: RepositorySearchCriteria
    ) -> list[Repository]:
        """
        Return repositories matching the provided criteria.

        :param criteria: repository search criteria
        :return list[Repository]: list of repositories matching the provided criteria.
        """
        ...


class SearchRepositoriesUseCase:
    _repository_search: RepositorySearchPort
    _scorer: PopularityScorer

    def __init__(
        self, repository_search: RepositorySearchPort, scorer: PopularityScorer
    ) -> None:
        self._repository_search = repository_search
        self._scorer = scorer

    async def execute(
        self, criteria: RepositorySearchCriteria
    ) -> list[ScoredRepository]:
        language = criteria.language

        if not language:
            raise ValidationError("Language not provided")
        if criteria.created_after > date.today():
            raise ValidationError("created_after must not be in future")
        if criteria.limit < 1:
            raise ValidationError("Limit must be greater than 0")

        repositories = await self._repository_search.search_repositories(criteria)

        scored_repositories = [
            ScoredRepository(repository=repo, popularity_score=self._scorer.score(repo))
            for repo in repositories
        ]

        return sorted(
            scored_repositories, key=lambda repo: repo.popularity_score, reverse=True
        )[: criteria.limit]
