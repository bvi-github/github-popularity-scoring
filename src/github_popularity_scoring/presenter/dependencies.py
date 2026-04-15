from __future__ import annotations

from contextlib import asynccontextmanager
from typing import cast

import httpx
from fastapi import FastAPI, Request

from github_popularity_scoring.domain.scoring import PopularityScorer
from github_popularity_scoring.infrastructure.github.client import (
    GitHubRepositorySearchClient,
)
from github_popularity_scoring.service.repositories import SearchRepositoriesUseCase


def build_http_client() -> httpx.AsyncClient:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-Github-Api_Version": "2026-03-10",  # TODO: move github api version to settings
    }

    # TODO: add Authorization token (from settings?)

    return httpx.AsyncClient(
        base_url="https://api.github.com",  # TODO: move base_url to settings
        headers=headers,
        timeout=10.0,  # TODO: move timeout to settings
    )


def build_search_use_case(http_client: httpx.AsyncClient) -> SearchRepositoriesUseCase:

    repository_search = GitHubRepositorySearchClient(
        http_client=http_client,
    )

    repository_search_use_case = SearchRepositoriesUseCase(
        repository_search=repository_search,
        scorer=PopularityScorer(),  # TODO select scoring strategy from settings?
    )
    return repository_search_use_case


def create_lifespan(
    use_case: SearchRepositoriesUseCase | None = None,
):

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        if use_case is not None:
            app.state.search_use_case = use_case
            yield
            return

        http_client = build_http_client()
        app.state.http_client = http_client
        app.state.search_use_case = build_search_use_case(
            http_client=http_client,
        )

        try:
            yield
        finally:
            await http_client.aclose()

    return lifespan


def get_search_use_case(request: Request) -> SearchRepositoriesUseCase:
    app = cast(FastAPI, request.app)
    return cast(SearchRepositoriesUseCase, app.state.search_use_case)
