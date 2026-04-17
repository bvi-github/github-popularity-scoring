from __future__ import annotations

from datetime import date

from github_popularity_scoring.version import __version__
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status

from github_popularity_scoring.domain.entities import RepositorySearchCriteria
from github_popularity_scoring.domain.exceptions import ValidationError
from github_popularity_scoring.infrastructure.exceptions import ExternalServiceError
from github_popularity_scoring.infrastructure.github.settings import Settings
from github_popularity_scoring.presenter.dependencies import (
    create_lifespan,
    get_search_use_case, get_runtime_settings,
)
from github_popularity_scoring.presenter.schemas import (
    RepositoryPopularityResponse,
    SearchRepositoriesResponse,
)
from github_popularity_scoring.service.repositories import SearchRepositoriesUseCase

router = APIRouter(tags=["repositories"], prefix="/api/v1/repositories")


@router.get(
    path="/popularity",
    response_model=SearchRepositoriesResponse,
)
async def get_repository_popularity(
    created_after: Annotated[
        date,
        Query(description="Earliest repository creation date"),
    ],
    language: Annotated[
        str,
        Query(description="Programming language to search for", min_length=1, max_length=100),
    ],
    use_case: Annotated[SearchRepositoriesUseCase, Depends(get_search_use_case)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> SearchRepositoriesResponse:


    criteria = RepositorySearchCriteria(
        created_after=created_after,
        language=language,
    )

    try:
        scored_results = await use_case.execute(criteria, settings.result_limit)
    except ValidationError as exp:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exp)
        ) from exp
    except ExternalServiceError as exp:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exp)
        ) from exp

    return SearchRepositoriesResponse(
        repositories=[
            RepositoryPopularityResponse(
                name=item.repository.name,
                language=item.repository.language,
                stars=item.repository.stars,
                forks=item.repository.forks,
                html_url=item.repository.html_url,
                updated_at=item.repository.updated_at,
                popularity_score=item.popularity_score,
            )
            for item in scored_results.repositories
        ],
        total_count=scored_results.total_count,
        repositories_scanned=scored_results.repositories_scanned,
    )


def create_app(
    use_case: SearchRepositoriesUseCase | None = None,
    settings: Settings| None = None,
) -> FastAPI:

    app = FastAPI(
        title="GitHub Popularity Scoring API",
        version=__version__,
        lifespan=create_lifespan(use_case=use_case, settings=settings),
    )

    app.include_router(router)

    return app
