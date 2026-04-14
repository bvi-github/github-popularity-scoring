from datetime import date

import httpx
import pytest

from github_popularity_scoring.domain.entities import RepositorySearchCriteria
from github_popularity_scoring.infrastructure.github.client import (
    GitHubRepositorySearchClient,
)


@pytest.mark.asyncio
async def test_search_repositories_maps_github_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/repositories"
        assert request.url.params["q"] == 'language:"Python" created_at:>=2025-01-01'
        assert request.url.params["sort"] == "stars"
        assert request.url.params["order"] == "desc"
        assert request.url.params["per_page"] == "100"  # TODO: get it from settings

        return httpx.Response(
            status_code=200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [
                    {
                        "name": "demo",
                        "html_url": "https://github.com/example/demo",
                        "language": "Python",
                        "stargazers_count": 10,
                        "forks_count": 2,
                        "updated_at": "2025-12-01T00:00:00Z",
                    },
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        base_url="https://api.github.com",
        transport=transport,
    ) as http_client:
        client = GitHubRepositorySearchClient(
            http_client=http_client,
        )

        result = await client.search_repositories(
            criteria=RepositorySearchCriteria(
                language="Python",
                created_after=date(2025, 1, 1),
            )
        )

        assert len(result) == 1
        assert result[0].name == "demo"
        assert result[0].stars == 10


@pytest.mark.asyncio
async def test_search_repositories_error_wrapper() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=403,
            json={"message": "API rate limit exceeded"},
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        base_url="https://api.github.com",
        transport=transport,
    ) as http_client:
        client = GitHubRepositorySearchClient(
            http_client=http_client,
        )

        with pytest.raises(Exception) as exc:
            _ = await client.search_repositories(
                criteria=RepositorySearchCriteria(
                    language="Python",
                    created_after=date(2025, 1, 1),
                )
            )

    assert "GitHub search request failed" in str(exc.value)
