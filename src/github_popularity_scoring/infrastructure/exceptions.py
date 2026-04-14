from __future__ import annotations

from github_popularity_scoring.domain.exceptions import ApplicationError


class ExternalServiceError(ApplicationError):
    """Raised when an external dependency cannot satisfy a request."""
