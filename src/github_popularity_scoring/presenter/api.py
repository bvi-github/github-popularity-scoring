from __future__ import annotations

from datetime import date
from importlib.metadata import version
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status

from github_popularity_scoring.domain.entities import RepositorySearchCriteria
from github_popularity_scoring.domain.exceptions import ValidationError
from github_popularity_scoring.infrastructure.exceptions import ExternalServiceError
from github_popularity_scoring.presenter.dependencies import (
    create_lifespan,
    get_search_use_case,
)
from github_popularity_scoring.presenter.schemas import (
    RepositoryPopularityResponse,
    SearchRepositoriesRequest,
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
        Query(description="Programming language to search for"),
    ],
    use_case: Annotated[SearchRepositoriesUseCase, Depends(get_search_use_case)],
    limit: Annotated[
        int | None,
        Query(ge=1, description="Maximum repositories to return"),
    ] = None,
) -> SearchRepositoriesResponse:

    resolved_limit = limit or 10  # TODO: get default limit from settings

    # TODO: set a cap for a limit (from settings?), test it, raise an error if greater

    request_model = SearchRepositoriesRequest(
        created_after=created_after,
        language=language,
        limit=resolved_limit,
    )

    criteria = RepositorySearchCriteria(
        created_after=request_model.created_after,
        language=request_model.language,
        limit=request_model.limit,
    )

    try:
        scored_repositories = await use_case.execute(criteria)
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
            for item in scored_repositories
        ],
    )


def create_app(
    use_case: SearchRepositoriesUseCase | None = None,
) -> FastAPI:

    app = FastAPI(
        title="GitHub Popularity Scoring API",
        version=version("github-popularity-scoring"),
        lifespan=create_lifespan(use_case=use_case),
    )

    app.include_router(router)

    return app
