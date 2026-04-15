FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim as runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY pyproject.toml ./

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "github_popularity_scoring.main:app", "--host", "0.0.0.0", "--port", "8000"]