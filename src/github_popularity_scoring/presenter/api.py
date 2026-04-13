from __future__ import (annotations)

from importlib.metadata import version
from fastapi import APIRouter
from fastapi import FastAPI

router = APIRouter(tags=['repositories'], prefix='/api/v1/repositories')

@router.get("/")
async def index() -> dict[str, str]:
    return {"Hello": "World"}

def create_app() -> FastAPI:

    app = FastAPI(
        title="GitHub Popularity Scoring API",
        version=version("github-popularity-scoring"),
    )

    app.include_router(router)

    return app