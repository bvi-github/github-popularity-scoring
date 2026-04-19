from copy import deepcopy
from datetime import date, datetime, timezone

import pytest

from github_popularity_scoring.domain.entities import (
    Repository,
    RepositorySearchCriteria,
    RepositorySearchCursor,
    RepositorySearchResult,
)
from github_popularity_scoring.domain.exceptions import ValidationError
from github_popularity_scoring.domain.scoring import PopularityScorer
from github_popularity_scoring.service.repositories import (
    RepositorySearchPort,
    SearchRepositoriesUseCase,
)


class FakeRepositorySearch(RepositorySearchPort):
    def __init__(self, repositories: list[Repository]):
        self._repositories: list[Repository] = repositories
        self.criteria: RepositorySearchCriteria | None = None

    async def search_repositories(
        self, criteria: RepositorySearchCriteria
    ) -> RepositorySearchResult:
        self.criteria = criteria
        return RepositorySearchResult(
            repositories=self._repositories,
            total_count=len(self._repositories),
            next_cursor=None,
        )


class PagedFakeRepositorySearch(RepositorySearchPort):
    def __init__(self, pages: list[RepositorySearchResult]):
        self._pages = pages
        self.criteria_calls: list[RepositorySearchCriteria] = []

    async def search_repositories(
        self, criteria: RepositorySearchCriteria
    ) -> RepositorySearchResult:
        self.criteria_calls.append(deepcopy(criteria))
        return self._pages.pop(0)


def build_repository(
    name: str,
    stars: int,
    forks: int,
    updated_at: datetime,
) -> Repository:
    return Repository(
        name=name,
        stars=stars,
        forks=forks,
        updated_at=updated_at,
        language="Python",
        html_url="https://example.com",
    )


@pytest.mark.asyncio
async def test_use_case_scores_sorts_and_limits_results() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    repositories = [
        build_repository(
            name="older",
            stars=100,
            forks=10,
            updated_at=datetime(2025, 1, 5, tzinfo=timezone.utc),
        ),
        build_repository(
            name="recent-popular",
            stars=500,
            forks=10,
            updated_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
        ),
        build_repository(
            name="small",
            stars=10,
            forks=1,
            updated_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
        ),
    ]

    repository_search = FakeRepositorySearch(repositories)

    use_case = SearchRepositoriesUseCase(
        repository_search=repository_search,
        scorer=PopularityScorer(now_provider=lambda: now),
    )

    search_criteria = RepositorySearchCriteria(
        language="Python",
        created_after=date(2025, 1, 1),
    )

    result = await use_case.execute(
        criteria=search_criteria,
        result_limit=2,
    )

    assert repository_search.criteria == RepositorySearchCriteria(
        created_after=date(2025, 1, 1),
        language="Python",
    )
    assert [repo.repository.name for repo in result.repositories] == [
        "recent-popular",
        "older",
    ]


@pytest.mark.asyncio
async def test_use_case_scores_top_results_across_paginated_search() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first_page_cursor = RepositorySearchCursor(
        value="https://api.github.com/search/repositories?page=2"
    )
    repository_search = PagedFakeRepositorySearch(
        pages=[
            RepositorySearchResult(
                repositories=[
                    build_repository(
                        name="page-one-low",
                        stars=10,
                        forks=1,
                        updated_at=now,
                    ),
                    build_repository(
                        name="page-one-middle",
                        stars=30,
                        forks=1,
                        updated_at=now,
                    ),
                ],
                total_count=4,
                next_cursor=first_page_cursor,
            ),
            RepositorySearchResult(
                repositories=[
                    build_repository(
                        name="page-two-highest",
                        stars=100,
                        forks=1,
                        updated_at=now,
                    ),
                    build_repository(
                        name="page-two-second",
                        stars=50,
                        forks=1,
                        updated_at=now,
                    ),
                ],
                total_count=4,
                next_cursor=None,
            ),
        ],
    )

    use_case = SearchRepositoriesUseCase(
        repository_search=repository_search,
        scorer=PopularityScorer(now_provider=lambda: now),
    )

    result = await use_case.execute(
        criteria=RepositorySearchCriteria(
            language="Python",
            created_after=date(2025, 1, 1),
        ),
        result_limit=2,
    )

    assert [repo.repository.name for repo in result.repositories] == [
        "page-two-highest",
        "page-two-second",
    ]
    assert result.total_count == 4
    assert result.repositories_scanned == 4
    assert len(repository_search.criteria_calls) == 2
    assert repository_search.criteria_calls[0].cursor is None
    assert repository_search.criteria_calls[0].repositories_scanned == 0
    assert repository_search.criteria_calls[1].cursor == first_page_cursor
    assert repository_search.criteria_calls[1].repositories_scanned == 2


@pytest.mark.asyncio
async def test_use_case_returns_all_results_when_limit_exceeds_available_repositories() -> (
    None
):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repository_search = FakeRepositorySearch(
        [
            build_repository(
                name="first",
                stars=10,
                forks=1,
                updated_at=now,
            ),
            build_repository(
                name="second",
                stars=20,
                forks=1,
                updated_at=now,
            ),
        ]
    )
    use_case = SearchRepositoriesUseCase(
        repository_search=repository_search,
        scorer=PopularityScorer(now_provider=lambda: now),
    )

    result = await use_case.execute(
        criteria=RepositorySearchCriteria(
            language="Python",
            created_after=date(2025, 1, 1),
        ),
        result_limit=10,
    )

    assert [repo.repository.name for repo in result.repositories] == ["second", "first"]
    assert result.repositories_scanned == 2


@pytest.mark.asyncio
async def test_use_case_reject_blank_language():
    use_case = SearchRepositoriesUseCase(
        repository_search=FakeRepositorySearch([]), scorer=PopularityScorer()
    )

    with pytest.raises(ValidationError, match="Language not provided"):
        _ = await use_case.execute(
            criteria=RepositorySearchCriteria(
                language="   ",
                created_after=date(2025, 1, 1),
            ),
            result_limit=2,
        )


@pytest.mark.asyncio
async def test_use_case_reject_future_created_after():
    use_case = SearchRepositoriesUseCase(
        repository_search=FakeRepositorySearch([]), scorer=PopularityScorer()
    )

    with pytest.raises(ValidationError, match="created_after must not be in future"):
        _ = await use_case.execute(
            criteria=RepositorySearchCriteria(
                language="python",
                created_after=date(2999, 1, 1),
            ),
            result_limit=2,
        )
