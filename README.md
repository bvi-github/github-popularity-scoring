# GitHub Popularity Scoring

FastAPI backend service that searches GitHub repositories and returns the most popular repositories for a programming language created after a given date.

This is an assigment for a Backend Coding Challenge for a Senior Python Engineer position.

## Initial assignment

### Project overview

The objective of this project is to implement a backend application for scoring repositories on GitHub.

### Initial Information

GitHub provides a public search endpoint wich you can use for fetching repositories. You can find the documentation [here](docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-repositories)

The user should be able to configure the earliest created date and language of repositories

### Task: Popularity Score Assignment

* Develop a scoring algorithm that assigns a popularity score to each repository.
* Factors contributing to the score include stars, forks, and the recency of updates


## What It Does

The service exposes one HTTP endpoint:

```http
GET /api/v1/repositories/popularity?language=Python&created_after=2025-01-01
```

It:

1. Validates the search criteria.
2. Queries GitHub's repository search API.
3. Scans paginated results up to a configured limit.
4. Scores each repository using stars, forks, and recency.
5. Returns the highest-scoring repositories.

## Tech Stack

- Python 3.12
- FastAPI
- httpx async client
- Pydantic / pydantic-settings
- pytest / pytest-asyncio
- Ruff
- basedpyright
- uv
- Docker

## Project Structure

```text
src/github_popularity_scoring/
  main.py                         # ASGI entry point
  domain/                         # Entities, validation errors, scoring logic
  service/                        # Application use cases and ports
  infrastructure/github/          # GitHub API client, DTOs, settings
  presenter/                      # FastAPI routes, schemas, dependencies
tests/
  unit/                           # Domain, use case, dependency, client tests
  integration/                    # HTTP endpoint test with injected fake use case
```

The dependency direction is intentional:

```text
presenter -> service -> domain
presenter -> infrastructure
infrastructure -> service port
```

## Scoring

The default strategy is `balanced`.

```text
score =
  5  * log(1 + stars)
+ 3  * log(1 + forks)
+ 20 * exp(-days_since_update / 365)
```

- log(1 + n) - prevents very large repositories from dominating too aggressively
- stars count more than forks
- recency decays smoothly with exp()

An alternative `momentum` strategy is also available. It favors repositories that combine popularity with recent activity:

```text
score =
  (log(1 + stars) ^ 0.6)
* (log(1 + forks) ^ 0.4)
/ ((1 + days_since_update) ^ 0.5)
```

- stars count more than forks through the larger exponent
- recent updates have a stronger effect because it affects the whole score
- power-law decay - more aggressive penalization at first.

## API

### Get Repository Popularity

```http
GET /api/v1/repositories/popularity
```

Query parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `language` | string | yes | Programming language to search for. |
| `created_after` | date | yes | Earliest repository creation date, formatted as `YYYY-MM-DD`. |

Example:

```bash
curl "http://localhost:8000/api/v1/repositories/popularity?language=Python&created_after=2025-01-01"
```

Example response:

```json
{
  "repositories": [
    {
      "name": "example",
      "language": "Python",
      "stars": 1200,
      "forks": 180,
      "html_url": "https://github.com/example/example",
      "updated_at": "2026-01-01T00:00:00Z",
      "popularity_score": 63.52
    }
  ],
  "total_count": 2500,
  "repositories_scanned": 300
}
```

Error behavior:

- `422` when the language is blank or `created_after` is in the future.
- `502` when GitHub returns an error or the outbound request fails.

## Configuration

Configuration is loaded from environment variables or an optional `.env` file.

| Variable | Default | Description |
| --- | --- | --- |
| `GITHUB_API_BASE_URL` | `https://api.github.com` | GitHub API base URL.|
| `GITHUB_API_VERSION` | `2026-03-10` | GitHub API version header value. |
| `GITHUB_TOKEN` | unset | Optional token for higher GitHub API rate limits. |
| `GITHUB_TIMEOUT_SECONDS` | `10.0` | Timeout for GitHub API requests. |
| `SCANNED_REPO_LIMIT` | `300` | Maximum repositories to scan, capped at GitHub search's 1000-result limit. |
| `RESULT_LIMIT` | `10` | Number of top-scoring repositories returned. |
| `SCORING_STRATEGY` | `balanced` | Supported values: `balanced`, `momentum`. |

Example: see `.env.example`

## Local Development

Install dependencies:

```bash
uv sync
```

Run the API:

```bash
uv run uvicorn --app-dir src github_popularity_scoring.main:app --reload --host 0.0.0.0 --port 8000
```

Open the interactive API docs:

```text
http://localhost:8000/docs
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Run static type checks:

```bash
uv run basedpyright
```

## Docker

Build the image:

```bash
docker build -t github-popularity-scoring .
```

Run the container:

```bash
docker run --rm -p 8000:8000 --env-file .env github-popularity-scoring
```

Without an `.env` file:

```bash
docker run --rm -p 8000:8000 github-popularity-scoring
```

## Design Notes

- The domain layer contains plain dataclasses and scoring strategies.
- The service layer owns the repository search workflow and keeps only the top N results with a heap.
- The GitHub client handles API-specific query construction, DTO validation, pagination links, and error translation.
- FastAPI dependencies assemble runtime objects during application lifespan startup.
- Settings are centralized with `pydantic-settings` and can be overridden through environment variables.

## Known Constraints

- GitHub's search API only exposes up to 1000 results for a query; `SCANNED_REPO_LIMIT` is capped accordingly.
- GitHub Search API has a separate rate limit from the core API:
  - 10 requests/minute anonymous
  - 30 requests/minute with token

### Further improvements

- Implement rate-limit backoff and retry behavior using header's Retry-After / X-RateLimit-Reset when GitHub returns 403 or 429
- Improve scoring computation by fetching repositories several times, each time sorted by different field,
deduplicate results by repo ID, then score the union.
- Further improvement of scoring: separate background service scrapes results into own store;
score is computed locally; the API queries local dataset.
