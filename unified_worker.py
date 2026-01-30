"""
Unified worker that combines new video fetching and metrics collection.
Runs three tasks with different intervals.
"""
import asyncio
import logging
import os
import instaloader
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.database.session import get_session
from src.repositories.video_repository import VideoRepository
from src.repositories.metrics_repository import MetricsRepository
from src.repositories.metric_schedule_repository import MetricScheduleRepository
from src.repositories.account_repository import AccountRepository

# Import from existing workers
from worker_new_video import ReelsWorker, AudioDownloadService, TranscriptionService
from worker_new_video import InstagramService as NewVideoInstagramService
from worker_metrics import MetricsScheduler

# Import worker monitor
from admin.services.worker_monitor import WorkerMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExtendedReelsWorker(ReelsWorker):
    """Extended ReelsWorker that creates metric schedules immediately."""

    async def process_account(
        self,
        account_username: str,
        account_repo: AccountRepository,
        video_repo: VideoRepository,
        schedule_repo: MetricScheduleRepository = None,
        metrics_scheduler: MetricsScheduler = None,
        session = None
    ) -> int:
        """
        Process reels for a single account and create metric schedules immediately.

        Returns:
            Number of new videos processed
        """
        from src.models.video import Video

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
            posts = profile.get_reels()

            reel_count = 0
            for post in posts:
                reel_count += 1
                if reel_count > settings.worker_reels_limit:
                    logger.info(f"Reached limit of {settings.worker_reels_limit} reels")
                    break

                # Check if video already exists
                existing = await video_repo.get_by_shortcode(post.shortcode)
                if existing:
                    logger.info(f"Video {post.shortcode} already exists, stopping")
                    break

                post_date_aware = post.date_utc.replace(tzinfo=timezone.utc)

                # 2. Теперь вычитаем (обе даты знают, что они UTC)
                video_age_days = (datetime.now(timezone.utc) - post_date_aware).days

                if video_age_days > 7:
                    logger.info(f"Video {post.shortcode} is {video_age_days} days old (limit: 7), stopping")
                    break

                # Process new reel
                logger.info(f"Processing new reel: {post.shortcode}")

                reel_url = f"https://www.instagram.com/reel/{post.shortcode}/"
                enriched = await self.enrich_reel(reel_url, post.shortcode)

                # Save to database
                video = await video_repo.create_or_update_by_shortcode(
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
                await session.commit()  # Commit immediately after each video

                # Create metric schedules IMMEDIATELY after saving video
                if schedule_repo and metrics_scheduler:
                    try:
                        # Reload video to get all fields
                        video_obj = await video_repo.get_by_shortcode(post.shortcode)
                        if video_obj:
                            await metrics_scheduler.create_schedule_for_video(video_obj, schedule_repo)
                            logger.info(f"Created initial metric schedules for {post.shortcode}")
                    except Exception as e:
                        logger.error(f"Failed to create schedules for {post.shortcode}: {e}")

                # Small delay between reels
                await asyncio.sleep(self.DELAY_BETWEEN_REELS)

            logger.info(f"Processed {processed_count} new reels for {account_username}")

        except Exception as e:
            logger.error(f"Error processing account {account_username}: {e}")
            # Don't raise - continue processing other accounts

        return processed_count


class UnifiedWorker:
    """Unified worker with three scheduled tasks."""

    # Rate limiting
    DELAY_BETWEEN_METRICS = 0.5  # seconds

    def __init__(self):
        # Initialize services from worker_new_video.py
        self.instagram_new = NewVideoInstagramService()
        self.audio_service = AudioDownloadService(settings.audio_dir)
        self.transcription_service = TranscriptionService(model_size="base")

        # Initialize scheduler from worker_metrics.py
        self.metrics_scheduler = MetricsScheduler()

        # Use extended worker that creates metric schedules immediately
        self.reels_worker = ExtendedReelsWorker(
            self.instagram_new,
            self.audio_service,
            self.transcription_service
        )

        # For metrics: simple instaloader WITHOUT login (public data)
        self._public_loader = None

    @property
    def public_loader(self) -> instaloader.Instaloader:
        """Lazy-loaded Instaloader for public metrics (no login)."""
        if self._public_loader is None:
            self._public_loader = instaloader.Instaloader(
                download_videos=False,
                download_comments=False,
                save_metadata=False
            )
        return self._public_loader

    async def fetch_new_videos(self):
        """Fetch new reels from all accounts and create metric schedules immediately (every 6 hours)."""
        logger.info("Starting fetch_new_videos task")

        total_processed = 0

        try:
            async with get_session() as session:
                account_repo = AccountRepository(session)
                video_repo = VideoRepository(session)
                schedule_repo = MetricScheduleRepository(session)

                # Get all accounts
                accounts = await account_repo.get_all()
                logger.info(f"Found {len(accounts)} accounts in database")

                if not accounts:
                    logger.warning("No accounts found in database, skipping")
                    return

                # Process each account with immediate schedule creation
                for account in accounts:
                    count = await self.reels_worker.process_account(
                        account.username,
                        account_repo,
                        video_repo,
                        schedule_repo,
                        self.metrics_scheduler,
                        session
                    )
                    total_processed += count

                    # Delay between accounts
                    await asyncio.sleep(self.reels_worker.DELAY_BETWEEN_ACCOUNTS)

            logger.info(f"Job completed: {total_processed} new reels processed")

        except Exception as e:
            logger.error(f"Error in fetch_new_videos: {e}")

    async def update_metric_schedules(self):
        """Create/update metric schedules for videos (every 1 hour)."""
        logger.info("Checking for videos needing schedule updates...")

        async with get_session() as session:
            video_repo = VideoRepository(session)
            schedule_repo = MetricScheduleRepository(session)

            videos = await video_repo.get_videos_for_schedule_update(limit=100)
            logger.info(f"Found {len(videos)} videos needing schedules")

            for video in videos:
                try:
                    await self.metrics_scheduler.create_schedule_for_video(video, schedule_repo)
                except Exception as e:
                    logger.error(f"Failed to create schedule for {video.shortcode}: {e}")

    async def fetch_metrics_public(self, shortcode: str) -> dict:
        """Fetch metrics without login (public data)."""
        loop = asyncio.get_event_loop()
        post = await loop.run_in_executor(
            None,
            lambda: instaloader.Post.from_shortcode(self.public_loader.context, shortcode)
        )

        return {
            'view_count': post.video_play_count,
            'like_count': post.likes,
            'comment_count': post.comments,
        }

    async def process_scheduled_metrics(self):
        """Execute pending scheduled tasks (every 1 minute)."""
        logger.info("Processing scheduled metrics collection...")

        async with get_session() as session:
            schedule_repo = MetricScheduleRepository(session)
            metrics_repo = MetricsRepository(session)

            pending = await schedule_repo.get_pending_schedules()
            logger.info(f"Found {len(pending)} due schedules")

            for schedule in pending:
                video = schedule.video
                logger.info(f"Processing {schedule.schedule_type} for {video.shortcode}")

                try:
                    # Fetch metrics WITHOUT login
                    metrics_data = await self.fetch_metrics_public(video.shortcode)

                    # Save to database
                    await metrics_repo.create_metrics_snapshot(
                        video_id=video.id,
                        view_count=metrics_data['view_count'] or 0,
                        like_count=metrics_data['like_count'],
                        comment_count=metrics_data['comment_count'],
                        followers_count=0  # Not available without login
                    )

                    # Mark completed
                    await schedule_repo.mark_completed(schedule.id)
                    await session.commit()  # Commit immediately after each metric

                    # Create next schedule
                    await self.metrics_scheduler.create_schedule_for_video(video, schedule_repo)

                    # Rate limiting
                    await asyncio.sleep(self.DELAY_BETWEEN_METRICS)

                except Exception as e:
                    logger.error(f"Failed to process {schedule.id}: {e}")
                    await schedule_repo.mark_failed(schedule.id)


async def update_heartbeat():
    """Update worker heartbeat in database."""
    try:
        pid = os.getpid()
        async with get_session() as session:
            await WorkerMonitor.update_heartbeat(
                session,
                worker_name="unified_worker",
                pid=pid
            )
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to update heartbeat: {e}")


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("STARTING UNIFIED WORKER")
    logger.info("=" * 60)

    worker = UnifiedWorker()
    apsched = AsyncIOScheduler()

    # Job 0: Update heartbeat (every 30 seconds)
    apsched.add_job(
        update_heartbeat,
        'interval',
        seconds=30,
        id='heartbeat'
    )
    logger.info("  - Heartbeat: every 30 seconds")

    # Job 1: Process scheduled metrics (every 1 minute)
    apsched.add_job(
        worker.process_scheduled_metrics,
        'interval',
        minutes=1,
        id='process_metrics'
    )
    logger.info("  - Process metrics: every 1 minute")

    # Job 2: Update schedules (every 1 hour)
    apsched.add_job(
        worker.update_metric_schedules,
        'interval',
        hours=1,
        id='update_schedules'
    )
    logger.info("  - Update schedules: every 1 hour")

    # Job 3: Fetch new videos (every 6 hours)
    apsched.add_job(
        worker.fetch_new_videos,
        'interval',
        hours=settings.worker_interval_hours,
        id='fetch_videos'
    )
    logger.info(f"  - Fetch videos: every {settings.worker_interval_hours} hours")

    apsched.start()
    logger.info("Scheduler started")

    # Initial heartbeat
    await update_heartbeat()

    # Run initial tasks
    logger.info("Running initial tasks...")
    await worker.fetch_new_videos()
    await worker.update_metric_schedules()
    await worker.process_scheduled_metrics()

    logger.info("WORKER IS RUNNING")
    logger.info("Press Ctrl+C to stop")

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")

        # Mark worker as stopped
        try:
            async with get_session() as session:
                await WorkerMonitor.mark_worker_stopped(session, worker_name="unified_worker")
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to mark worker as stopped: {e}")

        apsched.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
