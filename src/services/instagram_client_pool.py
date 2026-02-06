"""Instagram client pool with round-robin selection and health tracking."""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Callable, Any

from src.services.instagram_client import InstagramClient
from src.services.exceptions import InstagramServiceError

logger = logging.getLogger(__name__)


class InstagramClientPool:
    """Pool of Instagram clients with round-robin selection and automatic error recovery."""

    def __init__(
        self,
        cookies_dir: str = "cookies",
        proxies_file: str = "proxies.txt",
        settings_dir: str = "instagram_sessions"
    ):
        """Initialize Instagram client pool.

        Args:
            cookies_dir: Directory containing cookie JSON files.
            proxies_file: File containing proxy URLs (one per line).
            settings_dir: Directory to store session settings.
        """
        self._clients: List[InstagramClient] = []
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._settings_dir = settings_dir

        # Load cookies and proxies
        cookies_files = self._load_cookies_files(cookies_dir)
        proxies = self._load_proxies(proxies_file)

        # 1 client = 1 pair (cookies + proxy)
        pool_size = min(len(cookies_files), len(proxies))
        if pool_size == 0:
            raise InstagramServiceError(
                "No clients created. Check cookies directory and proxies file."
            )

        for i in range(pool_size):
            cookies = self._load_cookies_from_file(cookies_files[i])
            proxy = proxies[i]

            client = InstagramClient(
                client_id=i,
                proxy=proxy,
                cookies=cookies,
                settings_dir=settings_dir
            )
            self._clients.append(client)

        logger.info(f"Initialized pool with {pool_size} clients")

    def _load_cookies_files(self, cookies_dir: str) -> List[str]:
        """Find all .json files in cookies directory.

        Args:
            cookies_dir: Path to cookies directory.

        Returns:
            List of cookie file paths.

        Raises:
            InstagramServiceError: If directory not found or no JSON files.
        """
        cookies_path = Path(cookies_dir)
        if not cookies_path.exists():
            raise InstagramServiceError(f"Cookies directory not found: {cookies_dir}")

        cookies_files = sorted(cookies_path.glob("*.json"))
        if not cookies_files:
            raise InstagramServiceError(f"No JSON files found in {cookies_dir}")

        logger.info(f"Found {len(cookies_files)} cookies files")
        return [str(f) for f in cookies_files]

    def _load_proxies(self, proxies_file: str) -> List[str]:
        """Load proxies from file.

        Args:
            proxies_file: Path to proxies file.

        Returns:
            List of proxy URLs.
        """
        proxies = []
        proxy_path = Path(proxies_file)

        if proxy_path.exists():
            with open(proxy_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        proxies.append(line)
            logger.info(f"Loaded {len(proxies)} proxies")
        else:
            logger.warning(f"Proxies file not found: {proxies_file}")

        return proxies

    def _load_cookies_from_file(self, cookies_file: str) -> dict:
        """Load cookies from JSON file.

        Args:
            cookies_file: Path to cookies JSON file.

        Returns:
            Dictionary of cookies.

        Raises:
            InstagramServiceError: If failed to load cookies.
        """
        try:
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)

            if 'sessionid' not in cookies:
                logger.warning(f"No sessionid in {cookies_file}")

            return cookies
        except Exception as e:
            raise InstagramServiceError(f"Failed to load cookies from {cookies_file}: {e}")

    async def get_next_client(self) -> InstagramClient:
        """Get the next available client using round-robin selection.

        Skips clients that are not available.

        Returns:
            Available InstagramClient instance.

        Raises:
            InstagramServiceError: If no available clients after checking all.
        """
        async with self._lock:
            max_attempts = len(self._clients)
            attempts = 0

            while attempts < max_attempts:
                client = self._clients[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._clients)

                if client.is_available:
                    logger.debug(f"Selected client {client.client_id} for request")
                    return client

                logger.debug(f"Client {client.client_id} is not available, skipping")
                attempts += 1

            # No available clients
            available_count = sum(1 for c in self._clients if c.is_available)
            raise InstagramServiceError(
                f"No available clients in pool ({available_count}/{len(self._clients)} available)"
            )

    async def execute_request(
        self,
        request_func: Callable[..., Any],
        *args,
        max_retries: int = 2,
        **kwargs
    ) -> Any:
        """Execute a request with automatic retry logic.

        Tries to execute the request using available clients. If a client fails,
        automatically retries with the next available client.

        Args:
            request_func: Function to execute (Client method).
            *args: Positional arguments for the function.
            max_retries: Maximum number of retries with different clients.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function call.

        Raises:
            InstagramServiceError: If all retries fail.
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                client = await self.get_next_client()
                result = await client.execute_request_async(request_func, *args, **kwargs)
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Request attempt {attempt + 1}/{max_retries + 1} failed: {e}"
                )
                if attempt < max_retries:
                    # Wait a bit before retrying
                    await asyncio.sleep(0.5)

        # All retries failed
        logger.error(f"All {max_retries + 1} attempts failed")
        raise InstagramServiceError(f"Request failed after {max_retries + 1} attempts: {last_error}")

    def get_pool_status(self) -> dict:
        """Get the current status of the pool.

        Returns:
            Dictionary with pool status information.
        """
        clients_info = []
        for client in self._clients:
            client_info = {
                "client_id": client.client_id,
                "is_available": client.is_available,
                "proxy": client.proxy or "none",
                "authenticated": client._authenticated,
            }
            clients_info.append(client_info)

        return {
            "pool_size": len(self._clients),
            "available_clients": sum(1 for c in self._clients if c.is_available),
            "clients": clients_info,
        }

    async def close_all(self) -> None:
        """Close all clients and save their sessions."""
        logger.info("Closing all clients in pool")
        for client in self._clients:
            try:
                client.close()
            except Exception as e:
                logger.warning(f"Error closing client {client.client_id}: {e}")

        logger.info("All clients closed")
