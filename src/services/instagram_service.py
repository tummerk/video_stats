"""Instagram service using instagrapi library."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
    RelayRequired,
    FeedbackRequired,
    UserNotFound,
    MediaNotFound,
)

from src.config import settings
from src.services.exceptions import (
    AuthenticationError,
    RateLimitError,
    UserNotFoundError,
    VideoNotFoundError,
    NetworkError,
    InstagramServiceError,
)
from src.services.models import VideoInfo, VideoMetrics, UserVideosResult

logger = logging.getLogger(__name__)


class InstagramService:
    """Service for interacting with Instagram via instagrapi."""

    def __init__(self):
        """Initialize Instagram service with lazy client initialization."""
        self._client: Optional[Client] = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = asyncio.Lock()
        self._authenticated = False

    def _get_client(self) -> Client:
        """Get or create the Instagram client.

        Returns:
            Client: The instagrapi client instance.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if self._client is None:
            self._client = Client()

            # Configure proxy if provided
            if settings.instagram_proxy:
                try:
                    self._client.set_proxy(settings.instagram_proxy)
                    logger.info(f"Configured proxy: {settings.instagram_proxy}")
                except Exception as e:
                    logger.warning(f"Failed to set proxy: {e}")

            # Try to load session from file
            try:
                self._client.load_settings(settings.instagram_settings_file)
                logger.info(f"Loaded session from {settings.instagram_settings_file}")

                # Verify the session is still valid
                try:
                    self._client.get_timeline_feed()
                    self._authenticated = True
                    logger.info("Session is valid")
                    return self._client
                except Exception:
                    logger.info("Session expired, will re-authenticate")
                    self._client = Client()

            except FileNotFoundError:
                logger.info(f"No settings file found at {settings.instagram_settings_file}")
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}")

            # Try sessionid authentication (from env vars)
            if settings.instagram_sessionid and not self._authenticated:
                try:
                    self._client.login_by_sessionid(
                        settings.instagram_sessionid,
                        settings.instagramcsrftoken or "",
                    )
                    self._authenticated = True
                    logger.info("Authenticated via sessionid")

                    # Save session for future use
                    self._client.dump_settings(settings.instagram_settings_file)
                    logger.info(f"Saved session to {settings.instagram_settings_file}")
                    return self._client
                except Exception as e:
                    logger.warning(f"Sessionid authentication failed: {e}")

            # Try username/password authentication
            if settings.instagram_username and settings.instagram_password and not self._authenticated:
                try:
                    self._client.login(settings.instagram_username, settings.instagram_password)
                    self._authenticated = True
                    logger.info(f"Authenticated as {settings.instagram_username}")

                    # Save session for future use
                    self._client.dump_settings(settings.instagram_settings_file)
                    logger.info(f"Saved session to {settings.instagram_settings_file}")
                    return self._client
                except ChallengeRequired as e:
                    logger.error(f"2FA challenge required: {e}")
                    raise AuthenticationError("Two-factor authentication required. Please login via web app first.")
                except LoginRequired as e:
                    logger.error(f"Login required: {e}")
                    raise AuthenticationError("Invalid username or password")
                except Exception as e:
                    logger.error(f"Username/password authentication failed: {e}")
                    raise AuthenticationError(f"Authentication failed: {e}")

            if not self._authenticated:
                raise AuthenticationError(
                    "No valid credentials provided. Please set INSTAGRAM_SESSIONID or INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD."
                )

        return self._client

    async def close(self):
        """Close the service and cleanup resources."""
        if self._client:
            try:
                self._client.dump_settings(settings.instagram_settings_file)
            except Exception as e:
                logger.warning(f"Failed to save settings on close: {e}")
        self._executor.shutdown(wait=True)

    def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool.

        Args:
            func: The function to run.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function.

        Raises:
            InstagramServiceError: If the function fails.
        """
        try:
            return func(*args, **kwargs)
        except LoginRequired as e:
            logger.error(f"Login required: {e}")
            raise AuthenticationError("Authentication required")
        except ChallengeRequired as e:
            logger.error(f"Challenge required: {e}")
            raise AuthenticationError("Two-factor authentication required")
        except RelayRequired as e:
            logger.error(f"Relay required: {e}")
            raise AuthenticationError("Additional verification required")
        except FeedbackRequired as e:
            logger.error(f"Feedback/Rate limit required: {e}")
            raise RateLimitError("Rate limit exceeded")
        except UserNotFound as e:
            logger.error(f"User not found: {e}")
            raise UserNotFoundError(f"User not found: {e}")
        except MediaNotFound as e:
            logger.error(f"Media not found: {e}")
            raise VideoNotFoundError(f"Video not found: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            raise NetworkError(f"Network error: {e}")

    async def get_user_recent_videos(self, username: str, limit: int = 20) -> UserVideosResult:
        """Fetch recent videos from a user.

        Args:
            username: Instagram username to fetch videos from.
            limit: Maximum number of videos to fetch.

        Returns:
            UserVideosResult containing videos and user info.

        Raises:
            UserNotFoundError: If user is not found.
            AuthenticationError: If authentication fails.
            InstagramServiceError: For other errors.
        """
        client = self._get_client()

        def _fetch():
            # Get user info
            user_info = client.user_info_by_username(username)
            if not user_info:
                raise UserNotFoundError(f"User {username} not found")

            user_id = user_info.pk
            followers_count = user_info.follower_count

            # Get user's medias
            medias = client.usertmedias(user_id, amount=limit)

            # Filter for videos only
            videos = []
            for media in medias:
                if media.media_type == 2:  # 2 = video
                    # Get detailed media info for video_url
                    try:
                        media_full = client.media_info(media.pk)
                        video_url = media_full.video_url
                    except Exception:
                        video_url = None

                    video_info = VideoInfo(
                        video_id=str(media.pk),
                        shortcode=media.code,
                        video_url=video_url,
                        published_at=datetime.fromtimestamp(media.taken_at),
                        caption=media.caption_text if hasattr(media, 'caption_text') else None,
                        duration_seconds=media.video_duration if hasattr(media, 'video_duration') else None,
                    )
                    videos.append(video_info)

            return UserVideosResult(
                username=username,
                videos=videos,
                followers_count=followers_count,
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._run_sync, _fetch)

    async def get_post_metrics(self, shortcode: str) -> VideoMetrics:
        """Fetch metrics for a video by shortcode (alias for get_video_metrics).

        Args:
            shortcode: Instagram video shortcode (e.g., 'C1234567890').

        Returns:
            VideoMetrics containing engagement metrics.

        Raises:
            VideoNotFoundError: If video is not found.
            AuthenticationError: If authentication fails.
            InstagramServiceError: For other errors.
        """
        return await self.get_video_metrics(shortcode)

    async def get_video_metrics(self, shortcode: str) -> VideoMetrics:
        """Fetch metrics for a video by shortcode.

        Args:
            shortcode: Instagram video shortcode (e.g., 'C1234567890').

        Returns:
            VideoMetrics containing engagement metrics.

        Raises:
            VideoNotFoundError: If video is not found.
            AuthenticationError: If authentication fails.
            InstagramServiceError: For other errors.
        """
        client = self._get_client()

        def _fetch():
            # Get media by shortcode
            media = client.media_info(code=shortcode)
            if not media:
                raise VideoNotFoundError(f"Video with shortcode {shortcode} not found")

            # Get user info for followers count
            followers_count = None
            try:
                user_info = client.user_info(media.user.pk)
                followers_count = user_info.follower_count
            except Exception as e:
                logger.warning(f"Could not fetch followers count: {e}")

            return VideoMetrics(
                view_count=media.view_count if hasattr(media, 'view_count') else None,
                like_count=media.like_count if hasattr(media, 'like_count') else 0,
                comment_count=media.comment_count if hasattr(media, 'comment_count') else 0,
                save_count=media.play_count if hasattr(media, 'play_count') else None,  # Note: instagrapi may map saves differently
                followers_count=followers_count,
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._run_sync, _fetch)

    async def get_video_info(self, shortcode: str) -> VideoInfo:
        """Fetch detailed information about a video.

        Args:
            shortcode: Instagram video shortcode.

        Returns:
            VideoInfo with detailed video information.

        Raises:
            VideoNotFoundError: If video is not found.
            AuthenticationError: If authentication fails.
            InstagramServiceError: For other errors.
        """
        client = self._get_client()

        def _fetch():
            # Get media by shortcode
            media = client.media_info(code=shortcode)
            if not media:
                raise VideoNotFoundError(f"Video with shortcode {shortcode} not found")

            return VideoInfo(
                video_id=str(media.pk),
                shortcode=media.code,
                video_url=media.video_url if hasattr(media, 'video_url') else None,
                published_at=datetime.fromtimestamp(media.taken_at),
                caption=media.caption_text if hasattr(media, 'caption_text') else None,
                duration_seconds=media.video_duration if hasattr(media, 'video_duration') else None,
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._run_sync, _fetch)

    async def test_connection(self) -> bool:
        """Test if the Instagram session is working.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            client = self._get_client()
            # Try to fetch the timeline feed
            client.get_timeline_feed()
            logger.info("Connection test successful")
            return True
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
