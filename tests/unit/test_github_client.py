from datetime import date

import httpx
import pytest

from github_popularity_scoring.domain.entities import (
    RepositorySearchCriteria,
    RepositorySearchCursor,
)
from github_popularity_scoring.infrastructure.exceptions import ExternalServiceError
from github_popularity_scoring.infrastructure.github.client import (
    GitHubRepositorySearchClient,
)
from github_popularity_scoring.infrastructure.github.settings import Settings


@pytest.mark.asyncio
async def test_search_repositories_maps_github_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/repositories"
        assert request.url.params["q"] == 'language:"Python" created:>=2025-01-01'
        assert request.url.params["sort"] == "stars"
        assert request.url.params["order"] == "desc"
        assert request.url.params["per_page"] == "100"

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
            settings=Settings(),
        )

        result = await client.search_repositories(
            criteria=RepositorySearchCriteria(
                language="Python",
                created_after=date(2025, 1, 1),
            ),
        )

        repos_list = result.repositories

        assert len(repos_list) == 1
        assert result.total_count == 1
        assert result.next_cursor is None
        assert repos_list[0].name == "demo"
        assert repos_list[0].html_url == "https://github.com/example/demo"
        assert repos_list[0].language == "Python"
        assert repos_list[0].stars == 10
        assert repos_list[0].forks == 2
        assert repos_list[0].updated_at.isoformat() == "2025-12-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_search_repositories_returns_next_cursor_from_github_link_header() -> (
    None
):
    next_url = "https://api.github.com/search/repositories?q=demo&page=2"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"Link": f'<{next_url}>; rel="next"'},
            json={
                "total_count": 2,
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
            settings=Settings(scanned_repo_limit=200),
        )

        result = await client.search_repositories(
            criteria=RepositorySearchCriteria(
                language="Python",
                created_after=date(2025, 1, 1),
            ),
        )

    assert result.next_cursor == RepositorySearchCursor(value=next_url)


@pytest.mark.asyncio
async def test_search_repositories_stops_pagination_at_scanned_repo_limit() -> None:
    next_url = "https://api.github.com/search/repositories?q=demo&page=2"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"Link": f'<{next_url}>; rel="next"'},
            json={
                "total_count": 2,
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
            settings=Settings(scanned_repo_limit=1),
        )

        result = await client.search_repositories(
            criteria=RepositorySearchCriteria(
                language="Python",
                created_after=date(2025, 1, 1),
            ),
        )

    assert result.next_cursor is None


@pytest.mark.asyncio
async def test_search_repositories_uses_cursor_url_without_rebuilding_query() -> None:
    cursor_url = "https://api.github.com/search/repositories?q=cursor&page=2"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == cursor_url

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
            settings=Settings(),
        )

        result = await client.search_repositories(
            criteria=RepositorySearchCriteria(
                language="Python",
                created_after=date(2025, 1, 1),
                cursor=RepositorySearchCursor(value=cursor_url),
            ),
        )

    assert result.repositories[0].name == "demo"


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
            settings=Settings(),
        )

        with pytest.raises(ExternalServiceError) as exc:
            _ = await client.search_repositories(
                criteria=RepositorySearchCriteria(
                    language="Python",
                    created_after=date(2025, 1, 1),
                )
            )

    assert "GitHub search request failed" in str(exc.value)
