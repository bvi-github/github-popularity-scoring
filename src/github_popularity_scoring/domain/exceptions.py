from __future__ import annotations


class ApplicationError(Exception):
    """
    Base application exception.
    """


class ValidationError(ApplicationError):
    """
    Raised when user input cannot be processed safely.
    """
