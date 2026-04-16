from __future__ import annotations

from contextlib import asynccontextmanager
from typing import cast

import httpx
from fastapi import FastAPI, Request

from github_popularity_scoring.domain.enums_ import ScoringStrategyName
from github_popularity_scoring.domain.scoring import BalancedScoringStrategy, PopularityScorer, ScoringStrategy, \
    MomentumFocusedScoringStrategy
from github_popularity_scoring.infrastructure.github.client import (
    GitHubRepositorySearchClient,
)
from github_popularity_scoring.infrastructure.github.settings import Settings, get_settings
from github_popularity_scoring.service.repositories import SearchRepositoriesUseCase

SCORING_STRATEGIES: dict[ScoringStrategyName, ScoringStrategy] = {
    ScoringStrategyName.BALANCED: BalancedScoringStrategy(),
    ScoringStrategyName.MOMENTUM: MomentumFocusedScoringStrategy(),
}

def build_http_client(settings: Settings) -> httpx.AsyncClient:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-Github-Api_Version": settings.github_api_version,
    }

    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    return httpx.AsyncClient(
        base_url=settings.github_api_base_url,
        headers=headers,
        timeout=settings.github_timeout_seconds,
    )


def build_search_use_case(http_client: httpx.AsyncClient, settings: Settings) -> SearchRepositoriesUseCase:

    repository_search = GitHubRepositorySearchClient(
        http_client=http_client,
        settings=settings,
    )

    repository_search_use_case = SearchRepositoriesUseCase(
        repository_search=repository_search,
        scorer=PopularityScorer(strategy=build_scoring_strategy(settings)),
    )
    return repository_search_use_case

def build_scoring_strategy(settings: Settings) -> ScoringStrategy:
    return SCORING_STRATEGIES[settings.scoring_strategy]

def create_lifespan(
    use_case: SearchRepositoriesUseCase | None = None,
    settings: Settings | None = None,
):
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        app.state.settings = resolved_settings

        if use_case is not None:
            app.state.search_use_case = use_case
            yield
            return

        http_client = build_http_client(resolved_settings)
        app.state.http_client = http_client
        app.state.search_use_case = build_search_use_case(
            http_client=http_client,
            settings=resolved_settings,
        )

        try:
            yield
        finally:
            await http_client.aclose()

    return lifespan


def get_search_use_case(request: Request) -> SearchRepositoriesUseCase:
    app = cast(FastAPI, request.app)
    return cast(SearchRepositoriesUseCase, app.state.search_use_case)

def get_runtime_settings(request: Request) -> Settings:
    app = cast(FastAPI, request.app)
    return cast(Settings, app.state.settings)