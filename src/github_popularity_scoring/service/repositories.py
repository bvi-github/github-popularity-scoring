from __future__ import annotations

from datetime import date
from typing import Protocol

from github_popularity_scoring.domain.entities import (
    RepositorySearchCriteria,
    ScoredRepository,
    RepositorySearchResult,
    ScoringRepositoryResult,
)
from github_popularity_scoring.domain.exceptions import ValidationError
from github_popularity_scoring.domain.scoring import PopularityScorer

import heapq
from itertools import count


class RepositorySearchPort(Protocol):
    """
    A contract for searching repositories.
    It inverts the use case dependency on GitHub-specific search logic.
    """

    async def search_repositories(
        self,
        criteria: RepositorySearchCriteria,
    ) -> RepositorySearchResult:
        """
        Return repositories matching the provided criteria.

        :param criteria: repository search criteria
        :return RepositorySearchResult: list of repositories matching the provided criteria.
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
        self,
        criteria: RepositorySearchCriteria,
        result_limit: int,
    ) -> ScoringRepositoryResult:
        language = criteria.language

        if not language:
            raise ValidationError("Language not provided")
        if criteria.created_after > date.today():
            raise ValidationError("created_after must not be in future")

        repo_heap: list[tuple[float, int, ScoredRepository]] = []
        counter = count()

        total_count: int = 0
        repositories_scanned: int = 0

        while True:
            search_results = await self._repository_search.search_repositories(criteria)

            total_count = max(total_count, search_results.total_count)
            repositories_scanned += len(search_results.repositories)

            for repo in search_results.repositories:
                popularity_score = self._scorer.score(repo)

                scored_repo = ScoredRepository(
                    repository=repo,
                    popularity_score=popularity_score,
                )

                if len(repo_heap) < result_limit:
                    heapq.heappush(
                        repo_heap, (popularity_score, next(counter), scored_repo)
                    )
                else:
                    _ = heapq.heappushpop(
                        repo_heap, (popularity_score, next(counter), scored_repo)
                    )

            next_cursor = search_results.next_cursor
            if next_cursor is None:
                break

            criteria.cursor = next_cursor
            criteria.repositories_scanned = repositories_scanned

        scored_repositories = [repo for _, _, repo in sorted(repo_heap, reverse=True)]

        return ScoringRepositoryResult(
            repositories=scored_repositories,
            total_count=total_count,
            repositories_scanned=repositories_scanned,
        )
