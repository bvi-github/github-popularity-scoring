from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from github_popularity_scoring.domain.entities import (
    Repository,
    RepositorySearchCriteria, RepositorySearchResult,
)
from github_popularity_scoring.domain.scoring import PopularityScorer
from github_popularity_scoring.infrastructure.github.settings import Settings
from github_popularity_scoring.presenter.api import create_app
from github_popularity_scoring.presenter.schemas import SearchRepositoriesResponse
from github_popularity_scoring.service.repositories import (
    RepositorySearchPort,
    SearchRepositoriesUseCase,
)


class FakeRepositorySearch(RepositorySearchPort):
    async def search_repositories(
        self, criteria: RepositorySearchCriteria
    ) -> RepositorySearchResult:

        assert criteria == RepositorySearchCriteria(
            created_after=date(2025, 1, 1),
            language="Python",
        )

        repositories: list[Repository] = [
            Repository(
                name="demo",
                language="Python",
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                stars=10,
                forks=2,
                html_url="https://github.com/demo/demo",
            ),
        ]

        return RepositorySearchResult(
            repositories=repositories,
            total_count=len(repositories),
        )


def test_http_endpoint_returns_scored_repositories() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    use_case = SearchRepositoriesUseCase(
        repository_search=FakeRepositorySearch(),
        scorer=PopularityScorer(
            now_provider=lambda: now,
        ),
    )

    app = create_app(
        use_case=use_case,
        settings=Settings()
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/repositories/popularity",
            params={
                "language": "Python",
                "created_after": "2025-01-01",
                "limit": 1,
            },
        )

    assert response.status_code == 200

    payload = SearchRepositoriesResponse.model_validate(response.json())

    assert payload.repositories[0].name == "demo"
    assert payload.repositories[0].popularity_score > 0


def test_http_endpoint_rejects_future_creation_date() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    use_case = SearchRepositoriesUseCase(
        repository_search=FakeRepositorySearch(),
        scorer=PopularityScorer(now_provider=lambda: now),
    )

    app = create_app(use_case=use_case)

    with TestClient(app) as client:
        response = client.get(
            url="/api/v1/repositories/popularity",
            params={
                "language": "Python",
                "created_after": "2999-01-01",
                "limit": 1,
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "created_after must not be in future"
