from __future__ import annotations

from typing import cast

import httpx

from github_popularity_scoring.domain.entities import (
    Repository,
    RepositorySearchCriteria,
)
from github_popularity_scoring.infrastructure.exceptions import ExternalServiceError
from github_popularity_scoring.infrastructure.github.dto import (
    GitHubRepositoryDTO,
    GitHubSearchRepositoriesResponseDTO,
)
from github_popularity_scoring.service.repositories import RepositorySearchPort


class GitHubRepositorySearchClient(RepositorySearchPort):
    """
    Implementation of GitHub Repository Search client
    """

    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client: httpx.AsyncClient = http_client

    async def search_repositories(
        self, criteria: RepositorySearchCriteria
    ) -> list[Repository]:

        mapper = GitHubRepositoryMapper
        query_builder = GitHubRepositoryQueryBuilder

        query = query_builder.build(criteria)
        per_page = 100  # TODO: get from settings

        try:
            response = await self._http_client.get(
                "/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_page,
                },
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
        return [mapper.to_domain(dto) for dto in payload.items]

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
