"""Instagram client wrapper with health tracking and error handling."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Any

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    FeedbackRequired,
    UserNotFound,
    MediaNotFound,
)

from src.services.exceptions import (
    AuthenticationError,
    RateLimitError,
    UserNotFoundError as InstaUserNotFound,
    VideoNotFoundError,
    NetworkError,
)

logger = logging.getLogger(__name__)


def create_client(proxy_url: str, cookies_dict: dict, save_path: str) -> Client:
    """Create and configure instagrapi Client with cookies.

    Args:
        proxy_url: Proxy URL (empty string if no proxy).
        cookies_dict: Dictionary of cookies (must include sessionid).
        save_path: Path to save session settings.

    Returns:
        Configured Client instance.
    """
    cl = Client()
    if proxy_url:
        cl.set_proxy(proxy_url)
    cl.set_locale('en_US')
    cl.set_timezone_offset(-5 * 3600)  # New York UTC-5
    cl.set_cookies(cookies_dict)
    cl.dump_settings(save_path)
    return cl


class InstagramClient:
    """Wrapper around instagrapi.Client with health tracking and error handling."""

    def __init__(
        self,
        client_id: int,
        proxy: Optional[str],
        cookies: dict,
        settings_dir: str = "instagram_sessions"
    ):
        """Initialize Instagram client.

        Args:
            client_id: Unique identifier for this client.
            proxy: Optional proxy URL for this client.
            cookies: Dictionary of cookies for authentication.
            settings_dir: Directory to store session settings.
        """
        self.client_id = client_id
        self.proxy = proxy
        self.cookies = cookies
        self._client: Optional[Client] = None
        self._authenticated = False
        self._is_available = True  # Simple availability flag
        self._lock = asyncio.Lock()

        self.settings_dir = Path(settings_dir)
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.settings_dir / f"client_{client_id}_settings.json"

        logger.info(
            f"Initialized InstagramClient {client_id} "
            f"(proxy={proxy or 'none'}, session={self.session_file})"
        )

    async def _authenticate(self) -> None:
        """Authenticate the client using cookies.

        Tries multiple methods in order:
        1. Load settings from session file
        2. Create new client with cookies

        This method is async to avoid blocking the event loop.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if self._authenticated:
            return

        # Try to load session from file
        if self.session_file.exists():
            self._client = Client()
            try:
                # File I/O - run in thread to avoid blocking
                await asyncio.to_thread(self._client.load_settings, str(self.session_file))
                # Verify session is still valid (network call - run in thread)
                await asyncio.to_thread(self._client.get_timeline_feed)
                self._authenticated = True
                logger.info(f"Client {self.client_id}: Loaded valid session")
                return
            except Exception:
                logger.info(f"Client {self.client_id}: Session expired, re-authenticating")

        # Create new client with cookies (file I/O - run in thread)
        self._client = await asyncio.to_thread(
            create_client,
            proxy_url=self.proxy or "",
            cookies_dict=self.cookies,
            save_path=str(self.session_file)
        )
        self._authenticated = True
        logger.info(f"Client {self.client_id}: Authenticated via cookies")

    async def execute_request_async(self, request_func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a request asynchronously with error handling.

        Runs the blocking instagrapi operations in a thread pool to avoid blocking the event loop.
        Also uses a lock to ensure thread-safety when accessing the same client.

        Args:
            request_func: Function to execute (should be a Client method).
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function call.

        Raises:
            AuthenticationError: If authentication fails.
            RateLimitError: If rate limit is hit.
            InstaUserNotFound: If user is not found.
            VideoNotFoundError: If video is not found.
            NetworkError: For other network errors.
        """
        async with self._lock:
            try:
                if not self._authenticated:
                    await self._authenticate()

                result = await asyncio.to_thread(request_func, self._client, *args, **kwargs)
                self._is_available = True
                return result

            except LoginRequired as e:
                logger.error(f"Client {self.client_id}: Cookies invalid")
                self._is_available = False
                raise AuthenticationError(f"Cookies invalid for client {self.client_id}")

            except ChallengeRequired as e:
                logger.error(f"Client {self.client_id}: Challenge required")
                self._is_available = False
                raise AuthenticationError(f"2FA challenge for client {self.client_id}")

            except FeedbackRequired as e:
                logger.error(f"Client {self.client_id}: Rate limit exceeded")
                self._is_available = False
                raise RateLimitError(f"Rate limit for client {self.client_id}")

            except UserNotFound:
                raise InstaUserNotFound(f"User not found")

            except MediaNotFound:
                raise VideoNotFoundError(f"Video not found")

            except Exception as e:
                logger.exception(f"Client {self.client_id}: Unexpected error: {e}")
                self._is_available = False
                raise NetworkError(f"Network error: {e}")

    def execute_request(self, request_func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a request with error handling (sync wrapper).

        DEPRECATED: Use execute_request_async instead.

        This is a synchronous wrapper for backward compatibility only.
        It will raise RuntimeError if called from an async context.

        Args:
            request_func: Function to execute (should be a Client method).
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function call.

        Raises:
            RuntimeError: If called from an async context (event loop already running).
            AuthenticationError: If authentication fails.
            RateLimitError: If rate limit is hit.
            InstaUserNotFound: If user is not found.
            VideoNotFoundError: If video is not found.
            NetworkError: For other network errors.
        """
        import warnings
        warnings.warn(
            "execute_request() is deprecated. Use execute_request_async() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        try:
            loop = asyncio.get_running_loop()
            raise RuntimeError(
                "execute_request() cannot be called from an async context. "
                "Use execute_request_async() instead."
            )
        except RuntimeError:
            # No event loop running, safe to create one
            pass

        return asyncio.run(
            self.execute_request_async(request_func, *args, **kwargs)
        )

    @property
    def is_available(self) -> bool:
        """Check if client is available for requests.

        Returns:
            True if client can accept requests.
        """
        return self._is_available and self._authenticated

    def close(self) -> None:
        """Close the client and save session."""
        if self._client:
            try:
                self._client.dump_settings(str(self.session_file))
                logger.info(f"Client {self.client_id}: Session saved")
            except Exception as e:
                logger.warning(f"Client {self.client_id}: Failed to save session on close: {e}")
