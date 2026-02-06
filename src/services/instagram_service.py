"""Instagram service using instagrapi library."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Callable, Any

import yt_dlp
import whisper

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired,
    ChallengeRequired,
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
)
from src.services.models import VideoInfo, VideoMetrics

logger = logging.getLogger(__name__)


class InstagramService:
    """Service for interacting with Instagram via instagrapi."""

    def __init__(self, db_session_factory=None):
        """Initialize Instagram service with optional database access.

        Args:
            db_session_factory: Optional function to create DB sessions.
                If provided, will save videos to database.
        """
        self._client: Optional[Client] = None
        self._executor = ThreadPoolExecutor(max_workers=1)  # Для instagrapi (последовательно)
        self._yt_dlp_executor = ThreadPoolExecutor(max_workers=settings.yt_dlp_max_workers)  # Для yt-dlp (параллельно)
        self._lock = asyncio.Lock()
        self._authenticated = False
        self._db_session_factory = db_session_factory

        logger.info("InstagramService initialized with single-client mode")

        # Store repository classes for lazy instantiation
        if db_session_factory:
            from src.repositories.account_repository import AccountRepository
            from src.repositories.video_repository import VideoRepository
            from src.repositories.metrics_repository import MetricsRepository
            self._account_repository_class = AccountRepository
            self._video_repository_class = VideoRepository
            self._metrics_repository_class = MetricsRepository
        else:
            self._account_repository_class = None
            self._video_repository_class = None
            self._metrics_repository_class = None

        self._audio_dir = Path(settings.audio_dir)
        self._audio_dir.mkdir(parents=True, exist_ok=True)

        # Cache Whisper model (lazy load on first use)
        self._whisper_model = None

    async def _authenticate_client(self) -> None:
        """Authenticate the Instagram client.

        Uses cookies from environment or settings file.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if self._authenticated:
            return

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
            await asyncio.to_thread(self._client.load_settings, settings.instagram_settings_file)
            logger.info(f"Loaded session from {settings.instagram_settings_file}")

            # Verify session is valid
            await asyncio.to_thread(self._client.get_timeline_feed)
            self._authenticated = True
            logger.info("Session is valid")
            return
        except FileNotFoundError:
            logger.info(f"No settings file found at {settings.instagram_settings_file}")
        except Exception as e:
            logger.info(f"Session expired or invalid: {e}")
            self._client = Client()

        # Try sessionid authentication
        if settings.instagram_sessionid:
            try:
                await asyncio.to_thread(
                    self._client.login_by_sessionid,
                    settings.instagram_sessionid
                )
                self._authenticated = True
                logger.info("Authenticated via sessionid")

                # Save session
                await asyncio.to_thread(self._client.dump_settings, settings.instagram_settings_file)
                return
            except Exception as e:
                logger.warning(f"Sessionid authentication failed: {e}")

        # Try username/password authentication
        if settings.instagram_username and settings.instagram_password:
            try:
                await asyncio.to_thread(
                    self._client.login,
                    settings.instagram_username,
                    settings.instagram_password
                )
                self._authenticated = True
                logger.info(f"Authenticated as {settings.instagram_username}")

                # Save session
                await asyncio.to_thread(self._client.dump_settings, settings.instagram_settings_file)
                return
            except ChallengeRequired as e:
                logger.error("2FA challenge required: %s", e)
                raise AuthenticationError("Two-factor authentication required")
            except LoginRequired as e:
                logger.error("Login required: %s", e)
                raise AuthenticationError("Invalid username or password")
            except Exception as e:
                logger.error("Authentication failed: %s", e)
                raise AuthenticationError(f"Authentication failed: {e}")

        raise AuthenticationError(
            "No valid credentials. Please set INSTAGRAM_SESSIONID "
            "or INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD."
        )

    def _get_account_repository(self, session):
        """Get AccountRepository instance for the current session.

        Args:
            session: Active AsyncSession

        Returns:
            AccountRepository instance or None if db not configured
        """
        if self._account_repository_class is None:
            return None
        return self._account_repository_class(session)

    def _get_video_repository(self, session):
        """Get VideoRepository instance for the current session.

        Args:
            session: Active AsyncSession

        Returns:
            VideoRepository instance or None if db not configured
        """
        if self._video_repository_class is None:
            return None
        return self._video_repository_class(session)

    def _get_metrics_repository(self, session):
        """Get MetricsRepository instance for the current session.

        Args:
            session: Active AsyncSession

        Returns:
            MetricsRepository instance or None if db not configured
        """
        if self._metrics_repository_class is None:
            return None
        return self._metrics_repository_class(session)

    async def _execute_instagram_request(self, request_func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute an Instagram API request.

        Args:
            request_func: Function that takes Client as first argument.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function call.

        Raises:
            AuthenticationError: If authentication fails.
            RateLimitError: If rate limit is hit.
            UserNotFoundError: If user is not found.
            VideoNotFoundError: If video is not found.
            NetworkError: For other network errors.
        """
        # Get or create client
        if not self._authenticated:
            await self._authenticate_client()

        # Execute request in thread pool
        try:
            return await asyncio.to_thread(request_func, self._client, *args, **kwargs)
        except LoginRequired as e:
            logger.error("Login required: %s", e)
            raise AuthenticationError("Authentication required")
        except ChallengeRequired as e:
            logger.error("Challenge required: %s", e)
            raise AuthenticationError("Two-factor authentication required")
        except FeedbackRequired as e:
            logger.error("Rate limit: %s", e)
            raise RateLimitError("Rate limit exceeded")
        except UserNotFound as e:
            logger.error("User not found: %s", e)
            raise UserNotFoundError(f"User not found: {e}")
        except MediaNotFound as e:
            logger.error("Media not found: %s", e)
            raise VideoNotFoundError(f"Video not found: {e}")
        except Exception as e:
            logger.exception("Unexpected error: %s", e)
            raise NetworkError(f"Network error: {e}")

    async def close(self):
        """Close the service and cleanup resources."""
        if self._client:
            try:
                await asyncio.to_thread(self._client.dump_settings, settings.instagram_settings_file)
                logger.info("Client session saved")
            except Exception as e:
                logger.warning(f"Failed to save settings on close: {e}")

        self._executor.shutdown(wait=True)
        if hasattr(self, '_yt_dlp_executor'):
            self._yt_dlp_executor.shutdown(wait=True)

    def _get_whisper_model(self):
        """Get or lazy-load Whisper model.

        Returns:
            The Whisper model instance (cached after first load).
        """
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model

    async def get_user_recent_videos(
        self,
        user_pk: int,
        username: str = None,
        limit: int = 20
    ) -> None:
        """Fetch and save recent videos from a user to the database.

        Fetches reels from Instagram, compares with latest video in DB,
        and saves only new videos (not in DB and published within last 7 days).

        For each new video:
        - Downloads audio file (MP3)
        - Transcribes audio using Whisper
        - Saves all data including transcription to DB

        Args:
            user_pk: Instagram user ID (primary key from Instagram).
            username: Optional Instagram username for account creation/lookup.
            limit: Maximum number of videos to fetch from Instagram.

        Returns:
            None (videos are saved directly to database)
        """
        if not self._db_session_factory:
            logger.warning("No database session factory configured, skipping save")
            return

        async with self._db_session_factory() as session:
            account_repo = self._get_account_repository(session)
            video_repo = self._get_video_repository(session)

            if not account_repo or not video_repo:
                logger.warning("Repositories not available, skipping save")
                return

            # Get or create account by Instagram ID (user_pk is now the PK)
            account = await account_repo.get(user_pk)
            if not account:
                # Create account if doesn't exist
                # If username provided, use it; otherwise fetch from Instagram
                if not username:
                    # Fetch username from Instagram using unified helper
                    def _fetch_user_info(client):
                        return client.user_info(user_pk)

                    user_info = await self._execute_instagram_request(_fetch_user_info)

                    if not user_info:
                        raise UserNotFoundError(f"User with user_pk {user_pk} not found")
                    username = user_info.username

                account = await account_repo.create(
                    id=user_pk,  # Instagram user_pk as primary key
                    username=username,
                    profile_url=f"https://www.instagram.com/{username}/",
                    followers_count=None  # Will update when metrics fetched
                )
                logger.info(f"Created new account: {username} (Instagram ID: {user_pk})")
                latest_db_video = None
            else:
                # Get latest video for this account
                latest_db_video = await video_repo.get_latest_by_account_id(account.id)
                if latest_db_video:
                    logger.info(f"Latest DB video for {account.username}: {latest_db_video.shortcode} from {latest_db_video.published_at}")

            # Fetch reels from Instagram using user_pk directly
            def _fetch_clips(client):
                return client.user_clips_v1(user_pk, amount=limit)

            clips = await self._execute_instagram_request(_fetch_clips)

            logger.info(f"Fetched {len(clips)} reels from Instagram for user_pk {user_pk}")

            # Process each reel
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            saved_count = 0

            for clip in clips:
                shortcode = clip.code
                published_at = datetime.fromtimestamp(clip.taken_at)

                # Check if we should stop processing
                if latest_db_video:
                    # Stop if shortcode matches latest DB video
                    if shortcode == latest_db_video.shortcode:
                        logger.info(f"Reached known video {shortcode}, stopping")
                        break

                    # Stop if video is older than 7 days
                    if published_at < seven_days_ago:
                        logger.info(f"Video {shortcode} is older than 7 days ({published_at}), stopping")
                        break

                # Extract metadata, download audio, transcribe using existing method
                reel_url = f"https://www.instagram.com/reels/{shortcode}/"
                video_data = await self._extract_reel_with_audio(reel_url, shortcode)

                # Save to database WITH transcription and audio_file_path
                await video_repo.create_or_update_by_shortcode(
                    shortcode=shortcode,
                    account_id=account.id,
                    video_id=video_data.get('id'),
                    video_url=video_data.get('webpage_url'),
                    published_at=published_at,
                    caption=video_data.get('description'),
                    duration_seconds=int(video_data.get('duration', 0)),
                    audio_file_path=video_data.get('audio_file_path'),
                    transcription=video_data.get('transcription'),
                )

                saved_count += 1
                logger.info(f"Saved video {shortcode} to database (with audio and transcription)")

            logger.info(f"Saved {saved_count} new videos for user_pk {user_pk}")

    def _extract_reel_with_audio_sync(self, reel_url: str, shortcode: str) -> dict:
        """Синхронная версия для выполнения в yt-dlp executor.

        Extract reel metadata, download audio, and transcribe using yt-dlp.

        Args:
            reel_url: Instagram reel URL
            shortcode: Video shortcode for filename

        Returns:
            Dict with: id, webpage_url, timestamp, description, duration,
                       audio_file_path, transcription
        """
        audio_filename = self._audio_dir / f"{shortcode}.mp3"

        # Step 1: Extract metadata
        ydl_opts_meta = {
            'quiet': True,
            'noprogress': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            info = ydl.extract_info(reel_url, download=False)

        # Step 2: Download audio
        ydl_opts_audio = {
            'format': 'bestaudio/best',
            'outtmpl': str(audio_filename.with_suffix('')),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noprogress': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
            ydl.download([reel_url])

        # Step 3: Transcribe audio (using cached model)
        transcription = None
        if audio_filename.exists():
            model = self._get_whisper_model()
            result = model.transcribe(str(audio_filename), fp16=False)
            transcription = result['text']

        return {
            'id': info.get('id'),
            'webpage_url': info.get('webpage_url'),
            'timestamp': info.get('timestamp'),
            'description': info.get('description'),
            'duration': info.get('duration'),
            'audio_file_path': str(audio_filename) if audio_filename.exists() else None,
            'transcription': transcription,
        }

    async def _extract_reel_with_audio(self, reel_url: str, shortcode: str) -> dict:
        """Extract reel metadata, download audio, and transcribe using yt-dlp.

        Запускает синхронные yt-dlp операции в отдельном executor для параллелизма.

        Args:
            reel_url: Instagram reel URL
            shortcode: Video shortcode for filename

        Returns:
            Dict with: id, webpage_url, timestamp, description, duration,
                       audio_file_path, transcription
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._yt_dlp_executor,  # Используем отдельный executor для yt-dlp
            self._extract_reel_with_audio_sync,
            reel_url,
            shortcode
        )

    async def get_video_metrics(self, media_pk: int) -> VideoMetrics:
        """Fetch metrics for a video by media_pk and save to database.

        Also updates the account's followers_count in the accounts table.

        Args:
            media_pk: Instagram media ID (media.pk).

        Returns:
            VideoMetrics containing engagement metrics.

        Raises:
            VideoNotFoundError: If video is not found.
            AuthenticationError: If authentication fails.
            InstagramServiceError: For other errors.
        """
        if not self._db_session_factory:
            logger.warning("No database session factory configured, skipping save")

        def _fetch_metrics(client):
            # Get media by media_pk (not shortcode!)
            media = client.media_info(pk=media_pk)
            if not media:
                raise VideoNotFoundError(f"Video with media_pk {media_pk} not found")

            # Get user info for followers count
            followers_count = None
            try:
                user_info = client.user_info(media.user.pk)
                followers_count = user_info.follower_count
            except Exception as e:
                logger.warning(f"Could not fetch followers count: {e}")

            if hasattr(media, 'play_count') and media.play_count is not None:
                view_count = media.play_count
            elif hasattr(media, 'view_count') and media.view_count is not None:
                view_count = media.view_count
            else:
                view_count = None

            return VideoMetrics(
                view_count=view_count,
                like_count=media.like_count if hasattr(media, 'like_count') else 0,
                comment_count=media.comment_count if hasattr(media, 'comment_count') else 0,
                save_count=None,  # Not available via instagrapi
                followers_count=followers_count,
            )

        metrics = await self._execute_instagram_request(_fetch_metrics)

        # Save to database if configured
        if self._db_session_factory:
            async with self._db_session_factory() as session:
                video_repo = self._get_video_repository(session)
                account_repo = self._get_account_repository(session)
                metrics_repo = self._get_metrics_repository(session)

                if not all([video_repo, account_repo, metrics_repo]):
                    logger.warning("Repositories not available, skipping save")
                    return metrics

                # Find video in database by video_id (which equals media_pk)
                video = await video_repo.get_by_video_id(str(media_pk))
                if not video:
                    logger.warning(f"Video with media_pk {media_pk} not found in database, skipping metrics save")
                    return metrics

                # Get username from video.account relationship
                username = video.account.username

                # Update account followers_count
                if metrics.followers_count is not None:
                    await account_repo.create_or_update_by_username(
                        username=username,
                        followers_count=metrics.followers_count
                    )
                    logger.info(f"Updated followers for {username}: {metrics.followers_count}")

                # Save metrics to database
                await metrics_repo.create_metrics_snapshot(
                    video_id=video.id,
                    view_count=metrics.view_count or 0,
                    like_count=metrics.like_count,
                    comment_count=metrics.comment_count,
                    followers_count=metrics.followers_count or 0,
                    save_count=metrics.save_count,
                )
                logger.info(f"Saved metrics for video_id {video.id} (media_pk: {media_pk})")

        return metrics

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
        def _fetch_info(client):
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

        return await self._execute_instagram_request(_fetch_info)

    async def resolve_username_to_user_pk(self, username: str) -> int:
        """Resolve Instagram username to user_pk.

        Args:
            username: Instagram username (without @)

        Returns:
            Instagram user_pk (integer ID)

        Raises:
            UserNotFoundError: If username not found
            AuthenticationError: If not authenticated
            NetworkError: For network errors
        """
        def _get_user_id(client, username: str) -> int:
            return client.user_id_from_username(username)

        return await self._execute_instagram_request(_get_user_id, username)

    async def test_connection(self) -> bool:
        """Test if the Instagram session is working.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            def _test_conn(client):
                return client.get_timeline_feed()

            await self._execute_instagram_request(_test_conn)
            logger.info("Connection test successful")
            return True
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False