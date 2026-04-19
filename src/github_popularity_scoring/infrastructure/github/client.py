from __future__ import annotations

from typing import cast

import httpx

from github_popularity_scoring.domain.entities import (
    Repository,
    RepositorySearchCriteria,
    RepositorySearchResult,
    RepositorySearchCursor,
)
from github_popularity_scoring.infrastructure.exceptions import ExternalServiceError
from github_popularity_scoring.infrastructure.github.dto import (
    GitHubRepositoryDTO,
    GitHubSearchRepositoriesResponseDTO,
)
from github_popularity_scoring.infrastructure.github.settings import Settings
from github_popularity_scoring.service.repositories import RepositorySearchPort

_GITHUB_SEARCH_CAP = 1000
_REPOS_PER_PAGE = 100


class GitHubRepositorySearchClient(RepositorySearchPort):
    """
    Implementation of GitHub Repository Search client
    """

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings):
        self._http_client: httpx.AsyncClient = http_client
        self._settings: Settings = settings

    async def search_repositories(
        self, criteria: RepositorySearchCriteria
    ) -> RepositorySearchResult:

        mapper = GitHubRepositoryMapper
        query_builder = GitHubRepositoryQueryBuilder

        query = query_builder.build(criteria)

        search_endpoint = "/search/repositories"
        endpoint_params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": _REPOS_PER_PAGE,
            "page": 1,
        }

        if criteria.cursor is not None:
            search_endpoint = criteria.cursor.value
            endpoint_params = None

        # TODO: consider rate limits
        #   Rate limits for /search/repositories:
        #       - Anonymous: 10 requests/minute
        #       - with token: 30 requests/minute

        try:
            response = await self._http_client.get(
                url=search_endpoint,
                params=endpoint_params,
            )
            response = response.raise_for_status()
        except httpx.HTTPStatusError as exp:
            raise ExternalServiceError(
                self._build_error_message(exp.response),
            ) from exp
        except httpx.HTTPError as exp:
            raise ExternalServiceError(
                "GitHub request failed before a response was received"
            ) from exp

        payload = GitHubSearchRepositoriesResponseDTO.model_validate(response.json())
        repositories = [mapper.to_domain(dto) for dto in payload.items]

        repositories_scanned = criteria.repositories_scanned + len(repositories)
        scanned_repo_limit = min(self._settings.scanned_repo_limit, _GITHUB_SEARCH_CAP)

        next_url = response.links.get("next", {}).get("url")
        next_cursor = None

        if repositories_scanned < scanned_repo_limit and next_url is not None:
            next_cursor = RepositorySearchCursor(value=next_url)

        return RepositorySearchResult(
            repositories=repositories,
            total_count=payload.total_count,
            next_cursor=next_cursor,
        )

    @staticmethod
    def _build_error_message(response: httpx.Response) -> str:
        message = "GitHub search request failed"
        payload: object | None

        try:
            payload = cast(object, response.json())
        except ValueError:
            payload = None

        if isinstance(payload, dict) and "message" in payload:
            payload_message = cast(object, payload["message"])

            if isinstance(payload_message, str):
                message = f"{message}: {payload_message}"

        return f"{message} (status {response.status_code})"


class GitHubRepositoryMapper:
    """
    Maps GitHub repository DTO to domain
    """

    @staticmethod
    def to_domain(dto: GitHubRepositoryDTO) -> Repository:
        return Repository(
            name=dto.name,
            language=dto.language,
            stars=dto.stargazers_count,
            forks=dto.forks_count,
            html_url=dto.html_url,
            updated_at=dto.updated_at,
        )


class GitHubRepositoryQueryBuilder:
    @staticmethod
    def build(criteria: RepositorySearchCriteria) -> str:
        return (
            f'language:"{criteria.language}" '
            f"created:>={criteria.created_after.isoformat()}"
        )
