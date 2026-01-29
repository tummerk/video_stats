"""
Worker for fetching and processing new Instagram Reels every 6 hours.

Refactored version with:
- Proper async/sync separation
- Service layer for external dependencies
- Singleton Whisper model
- Retry logic
- Clean architecture
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union, Iterator
from concurrent.futures import ThreadPoolExecutor

import instaloader
import yt_dlp
import whisper
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.config import settings
from src.database import get_session
from src.repositories.account_repository import AccountRepository
from src.repositories.video_repository import VideoRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Services
# ============================================================================

class InstagramService:
    """Service for Instagram API interactions."""

    def __init__(self) -> None:
        self._client: Optional[instaloader.Instaloader] = None

    def _create_client(self) -> instaloader.Instaloader:
        """Create configured Instaloader instance."""
        L = instaloader.Instaloader(
            download_videos=False,
            download_comments=False,
            save_metadata=False
        )

        cookies = {
            "sessionid": settings.instagram_sessionid,
            "ds_user_id": settings.instagram_ds_user_id,
            "csrftoken": settings.instagramcsrftoken,
            "mid": settings.instagram_mid,
        }

        for name, value in cookies.items():
            if value:
                L.context._session.cookies.set(
                    name,
                    value,
                    domain=".instagram.com",
                    path="/",
                    secure=True
                )

        logger.info("Instaloader client created")
        return L

    @property
    def client(self) -> instaloader.Instaloader:
        """Lazy load Instaloader client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    async def get_profile(self, username: str) -> instaloader.Profile:
        """Get Instagram profile asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: instaloader.Profile.from_username(self.client.context, username)
        )


class AudioDownloadService:
    """Service for downloading audio from Instagram Reels."""

    def __init__(self, audio_dir: Union[str, Path]):
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audio_download")

    async def download_audio(self, url: str, shortcode: str) -> Dict[str, Optional[str]]:
        """
        Download audio from Instagram Reel.

        Returns:
            Dict with video_url, audio_url, audio_file_path
        """
        audio_filename = self.audio_dir / f"{shortcode}.mp3"

        def _download() -> Dict[str, Optional[str]]:
            ydl_opts = {
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

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not audio_filename.exists():
                raise FileNotFoundError(f"Failed to download audio for {shortcode}")

            # Extract URLs
            with yt_dlp.YoutubeDL({'quiet': True, 'noprogress': True}) as ydl:
                info = ydl.extract_info(url, download=False)

            # Extract direct video URL from formats
            video_url = None
            if info.get('formats'):
                # Get the best quality video format
                video_format = next((f for f in info['formats'] if f.get('vcodec') != 'none'), None)
                if video_format:
                    video_url = video_format.get('url')

            return {
                "video_url": video_url,
                "audio_url": video_url,  # Same URL for Instagram reels
                "audio_file_path": str(audio_filename)
            }

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, _download)
            logger.info(f"Downloaded audio for {shortcode}")
            return result
        except Exception as e:
            logger.error(f"Error downloading audio for {shortcode}: {e}")
            if audio_filename.exists():
                audio_filename.unlink()
            return {
                "video_url": None,
                "audio_url": None,
                "audio_file_path": None
            }


class TranscriptionService:
    """Service for audio transcription using Whisper."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model: Optional[whisper.Whisper] = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")

    def _load_model(self) -> whisper.Whisper:
        """Load Whisper model (cached)."""
        if self._model is None:
            logger.info(f"Loading Whisper model '{self.model_size}'...")
            self._model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded")
        return self._model

    async def transcribe(self, audio_path: Union[str, Path]) -> Optional[str]:
        """Transcribe audio file asynchronously."""
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        def _transcribe() -> str:
            model = self._load_model()
            result = model.transcribe(str(audio_path), fp16=False)
            return result['text']

        try:
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(self.executor, _transcribe)
            logger.info(f"Transcribed {audio_path}")
            return transcription
        except Exception as e:
            logger.error(f"Error transcribing {audio_path}: {e}")
            return None


# ============================================================================
# Worker
# ============================================================================

class ReelsWorker:
    """Worker for processing Instagram Reels."""

    # Rate limiting delays
    DELAY_BETWEEN_ACCOUNTS = 2  # seconds
    DELAY_BETWEEN_REELS = 0.5  # seconds

    def __init__(
        self,
        instagram_service: InstagramService,
        audio_service: AudioDownloadService,
        transcription_service: TranscriptionService
    ):
        self.instagram = instagram_service
        self.audio = audio_service
        self.transcription = transcription_service

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def enrich_reel(self, url: str, shortcode: str) -> Dict[str, Optional[str]]:
        """
        Download audio and transcribe with retry logic.

        Returns:
            Dict with video_url, audio_url, audio_file_path, transcription
        """
        # Download audio
        audio_data = await self.audio.download_audio(url, shortcode)

        result = {
            "video_url": audio_data["video_url"],
            "audio_url": audio_data["audio_url"],
            "audio_file_path": audio_data["audio_file_path"],
            "transcription": None
        }

        # Transcribe if audio was downloaded
        if audio_data["audio_file_path"]:
            transcription = await self.transcription.transcribe(audio_data["audio_file_path"])
            result["transcription"] = transcription

        return result

    async def process_account(
        self,
        account_username: str,
        account_repo: AccountRepository,
        video_repo: VideoRepository
    ) -> int:
        """
        Process reels for a single account.

        Returns:
            Number of new videos processed
        """
        processed_count = 0

        try:
            logger.info(f"Processing account: {account_username}")

            # Get Instagram profile
            profile = await self.instagram.get_profile(account_username)

            # Ensure account exists in database
            account = await account_repo.create_or_update_by_username(
                username=account_username,
                profile_url=f"https://www.instagram.com/{profile.username}/",
                followers_count=profile.followers
            )
            logger.info(f"Account {account_username} ensured in DB (id={account.id})")

            # Fetch and process reels (get_posts returns an iterator)
            posts = profile.get_posts()

            reel_count = 0
            for post in posts:
                # Filter only reels (video posts)
                if not (post.is_video and post.typename == 'GraphVideo'):
                    continue

                reel_count += 1
                if reel_count > settings.worker_reels_limit:
                    logger.info(f"Reached limit of {settings.worker_reels_limit} reels")
                    break

                # Check if video already exists
                existing = await video_repo.get_by_shortcode(post.shortcode)
                if existing:
                    logger.info(f"Video {post.shortcode} already exists, stopping")
                    break

                # Process new reel
                logger.info(f"Processing new reel: {post.shortcode}")

                reel_url = f"https://www.instagram.com/reel/{post.shortcode}/"
                enriched = await self.enrich_reel(reel_url, post.shortcode)

                # Save to database
                await video_repo.create_or_update_by_shortcode(
                    shortcode=post.shortcode,
                    video_id=post.shortcode,
                    video_url=enriched.get('video_url'),
                    published_at=post.date_utc,
                    caption=post.caption,
                    duration_seconds=post.video_duration,
                    audio_url=enriched.get('audio_url'),
                    audio_file_path=enriched.get('audio_file_path'),
                    transcription=enriched.get('transcription'),
                    account_id=account.id
                )

                processed_count += 1
                logger.info(f"Saved reel {post.shortcode} to database")

                # Small delay between reels
                await asyncio.sleep(self.DELAY_BETWEEN_REELS)

            logger.info(f"Processed {processed_count} new reels for {account_username}")

        except Exception as e:
            logger.error(f"Error processing account {account_username}: {e}")
            raise

        return processed_count

    async def run(self) -> None:
        """Main processing logic."""
        logger.info("Starting ReelsWorker job")

        total_processed = 0

        try:
            async with get_session() as session:
                account_repo = AccountRepository(session)
                video_repo = VideoRepository(session)

                # Get all accounts
                accounts = await account_repo.get_all()
                logger.info(f"Found {len(accounts)} accounts in database")

                if not accounts:
                    logger.warning("No accounts found in database, skipping")
                    return

                # Process each account
                for account in accounts:
                    count = await self.process_account(
                        account.username,
                        account_repo,
                        video_repo
                    )
                    total_processed += count

                    # Delay between accounts
                    await asyncio.sleep(self.DELAY_BETWEEN_ACCOUNTS)

            logger.info(f"Job completed: {total_processed} new reels processed")

        except Exception as e:
            logger.error(f"Error in ReelsWorker.run: {e}")


# ============================================================================
# Entry Point
# ============================================================================

async def main_async() -> None:
    """Async main function."""
    logger.info("Starting NEW_VIDEO worker")
    logger.info(f"Interval: {settings.worker_interval_hours} hours")
    logger.info(f"Reels limit: {settings.worker_reels_limit}")
    logger.info(f"Audio dir: {settings.audio_dir}")

    # Initialize services
    instagram_service = InstagramService()
    audio_service = AudioDownloadService(settings.audio_dir)
    transcription_service = TranscriptionService(model_size="base")
    worker = ReelsWorker(instagram_service, audio_service, transcription_service)

    # Create scheduler
    scheduler = AsyncIOScheduler()

    # Add job
    scheduler.add_job(
        worker.run,
        'interval',
        hours=settings.worker_interval_hours
    )

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")

    # Run once immediately
    logger.info("Running initial fetch...")
    await worker.run()

    # Keep running
    try:
        logger.info("Worker is running. Press Ctrl+C to stop.")
        await asyncio.Future()  # Run forever
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down worker...")
        scheduler.shutdown()
        logger.info("Worker stopped")


def main() -> None:
    """Main entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
