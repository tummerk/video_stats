"""Custom exceptions for Instagram service."""


class InstagramServiceError(Exception):
    """Base exception for Instagram service errors."""

    pass


class AuthenticationError(InstagramServiceError):
    """Raised when authentication fails."""

    pass


class RateLimitError(InstagramServiceError):
    """Raised when rate limit is hit."""

    pass


class UserNotFoundError(InstagramServiceError):
    """Raised when user is not found."""

    pass


class VideoNotFoundError(InstagramServiceError):
    """Raised when video is not found."""

    pass


class NetworkError(InstagramServiceError):
    """Raised when network error occurs."""

    pass
