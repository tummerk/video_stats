"""
Unified worker that combines new video fetching and metrics collection.
Runs three tasks with different intervals.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.database.session import get_session
from src.repositories.video_repository import VideoRepository
from src.repositories.metrics_repository import MetricsRepository
from src.repositories.metric_schedule_repository import MetricScheduleRepository
from src.repositories.account_repository import AccountRepository
from src.services.instagram_service import InstagramService
from admin.services.worker_monitor import WorkerMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsScheduler:
    """Metrics scheduler based on fixed milestones from publication time."""

    # Fixed milestones from publication time
    MILESTONES = [
        {"hours": 1, "type": "1h"},
        {"hours": 3, "type": "3h"},
        {"hours": 24, "type": "24h"},
        {"hours": 48, "type": "48h"},
        {"hours": 72, "type": "72h"},
    ]

    DAILY_MILESTONE_HOURS = 72  # After this, use daily schedule

    def _calculate_next_full_hour(self, dt: datetime) -> datetime:
        """Calculate the next full hour.

        Examples:
            12:34 -> 13:00
            12:03 -> 13:00
        """
        next_hour = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour

    def _get_milestone_times(self, published_at: datetime) -> List[dict]:
        """Calculate all milestone times from publication."""
        milestones = []
        for milestone in self.MILESTONES:
            milestone_time = published_at + timedelta(hours=milestone["hours"])
            milestones.append({
                'time': milestone_time,
                'type': milestone['type']
            })
        return milestones

    def _get_next_milestone(self, published_at: datetime, now: datetime) -> Optional[dict]:
        """Find the next milestone that hasn't passed yet.

        Returns:
            milestone (dict): next milestone for collection
            None: all milestones passed -> use daily schedule

        IMPORTANT: None does NOT mean "don't collect metrics"! It means switch to daily.
        """
        milestones = self._get_milestone_times(published_at)
        for milestone in milestones:
            if milestone['time'] > now:  # Strict comparison
                return milestone
        return None  # All milestones passed -> switch to daily

    async def _get_daily_schedule_time(
        self,
        video,
        schedule_repo: MetricScheduleRepository,
        now: datetime
    ) -> tuple[datetime, str]:
        """Calculate time for daily collection (>72h).

        - First daily: next full hour
        - Subsequent daily: same time as previous daily
        """
        # Check for optimized method
        if hasattr(schedule_repo, 'get_last_daily_schedule'):
            latest_daily = await schedule_repo.get_last_daily_schedule(video.id)
        else:
            # Fallback: get all completed schedules and filter
            completed_schedules = await schedule_repo.get_schedules_by_video(
                video.id, status='completed'
            )
            daily_schedules = [
                s for s in completed_schedules if s.schedule_type == 'daily'
            ]
            latest_daily = max(daily_schedules, key=lambda s: s.scheduled_at) if daily_schedules else None

        if latest_daily:
            # NOT the first daily - use the same time
            next_time = latest_daily.scheduled_at + timedelta(days=1)
            return next_time, 'daily'
        else:
            # FIRST daily - next full hour
            next_time = self._calculate_next_full_hour(now)
            return next_time, 'daily'

    async def create_schedule_for_video(self, video, schedule_repo: MetricScheduleRepository):
        """Create metric collection schedule based on fixed milestones.

        Logic:
        1. Calculate milestones: 1h, 3h, 24h, 48h, 72h from publication
        2. Find next milestone that hasn't passed yet
        3. If all milestones passed (>72h): use daily
           - First daily: next full hour
           - Subsequent daily: same time as previous daily

        IMPORTANT: ANY video in DB WILL get metrics! After 72h - daily.
        """
        from src.models.metric_schedule import MetricSchedule

        now = datetime.now(timezone.utc)
        published_at = video.published_at.replace(tzinfo=timezone.utc)
        video_age = now - published_at
        hours_since_publication = video_age.total_seconds() / 3600

        # Check for existing pending schedule
        existing_schedules = await schedule_repo.get_pending_schedules_by_video(video.id)
        if existing_schedules:
            logger.debug(f"Video {video.shortcode} already has pending schedules")
            return

        # Determine next schedule
        if hours_since_publication < self.DAILY_MILESTONE_HOURS:
            # Find next milestone
            next_milestone = self._get_next_milestone(published_at, now)

            if next_milestone:
                # Use milestone (1h, 3h, 24h, 48h, 72h)
                scheduled_at = next_milestone['time']
                schedule_type = next_milestone['type']
            else:
                # All milestones passed -> switch to daily
                # This happens when video_age is between 72h and next schedule creation
                scheduled_at, schedule_type = await self._get_daily_schedule_time(
                    video, schedule_repo, now
                )
        else:
            # Video older than 72 hours -> IMMEDIATELY use daily
            # ANY video older than 72h WILL get metrics daily!
            scheduled_at, schedule_type = await self._get_daily_schedule_time(
                video, schedule_repo, now
            )

        # Create schedule
        await schedule_repo.create_schedule(
            video_id=video.id,
            schedule_type=schedule_type,
            scheduled_at=scheduled_at,
            status="pending"
        )

        # Logging with age information
        age_str = f"{int(hours_since_publication)}h"
        if hours_since_publication >= 24:
            age_str = f"{int(hours_since_publication // 24)}d"

        logger.info(
            f"Created schedule for {video.shortcode} (age: {age_str}) "
            f"at {scheduled_at} (type: {schedule_type})"
        )


class UnifiedWorker:
    """Unified worker with three scheduled tasks."""

    # Rate limiting
    DELAY_BETWEEN_ACCOUNTS = 10  # seconds
    DELAY_BETWEEN_METRICS = 0.5  # seconds

    def __init__(self):
        """Initialize the unified worker."""
        self.instagram_service = InstagramService(db_session_factory=get_session)
        self.metrics_scheduler = MetricsScheduler()
        self.fetch_count = 0  # Счётчик запусков fetch_new_videos
        self.schedule_count = 0  # Счётчик запусков update_metric_schedules
        self.metrics_count = 0  # Счётчик запусков process_scheduled_metrics

    async def update_heartbeat(self):
        """Update worker heartbeat in database."""
        try:
            async with get_session() as session:
                await WorkerMonitor.update_heartbeat(
                    session,
                    worker_name="unified_worker",
                    pid=os.getpid()
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")

    async def fetch_new_videos(self):
        """Fetch new reels from all accounts (every 6 hours)."""
        self.fetch_count += 1
        logger.info(f"Starting fetch_new_videos task (Run #{self.fetch_count})")
        if settings.test_mode:
            logger.warning("⚠️  TEST MODE - Using reduced delays!")

        try:
            async with get_session() as session:
                account_repo = AccountRepository(session)
                schedule_repo = MetricScheduleRepository(session)

                # Get all accounts
                accounts = await account_repo.get_all()
                logger.info(f"Found {len(accounts)} accounts in database")

                if not accounts:
                    logger.warning("No accounts found in database, skipping")
                    return

                total_processed = 0
                for account in accounts:
                    try:
                        logger.info(f"Processing account: {account.username} (id={account.id})")

                        # Use InstagramService to fetch recent videos
                        # Account.id = user_pk
                        await self.instagram_service.get_user_recent_videos(
                            user_pk=account.id,
                            username=account.username,
                            limit=settings.worker_reels_limit
                        )

                        total_processed += 1

                        # Create metric schedules for newly added videos
                        video_repo = VideoRepository(session)
                        # Get recent videos for this account that might need schedules
                        videos = await video_repo.get_videos_for_schedule_update(limit=100)

                        for video in videos:
                            if video.account_id == account.id:
                                try:
                                    await self.metrics_scheduler.create_schedule_for_video(video, schedule_repo)
                                except Exception as e:
                                    logger.error(f"Failed to create schedule for {video.shortcode}: {e}")

                    except Exception as e:
                        logger.error(f"Error processing account {account.username}: {e}")
                        # Continue with next account

                    # Delay between accounts (reduced in test mode)
                    delay = 1 if settings.test_mode else self.DELAY_BETWEEN_ACCOUNTS
                    await asyncio.sleep(delay)

                await session.commit()
                logger.info(f"Job completed: processed {total_processed} accounts")

        except Exception as e:
            logger.error(f"Error in fetch_new_videos: {e}")

    async def update_metric_schedules(self):
        """Create/update metric schedules for videos (every 1 hour)."""
        self.schedule_count += 1
        logger.info(f"Checking for videos needing schedule updates (Run #{self.schedule_count})...")

        try:
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

                await session.commit()

        except Exception as e:
            logger.error(f"Error in update_metric_schedules: {e}")

    async def fetch_metrics_public(self, video_id: str) -> dict:
        """Fetch metrics using InstagramService.

        Args:
            video_id: Video ID (media_pk as string)

        Returns:
            Dict with view_count, like_count, comment_count, followers_count
        """
        # Video.video_id = media_pk
        media_pk = int(video_id)

        metrics = await self.instagram_service.get_video_metrics(media_pk)

        return {
            'view_count': metrics.view_count,
            'like_count': metrics.like_count,
            'comment_count': metrics.comment_count,
            'followers_count': metrics.followers_count,
        }

    async def process_scheduled_metrics(self):
        """Execute pending scheduled tasks (every 1 minute)."""
        self.metrics_count += 1
        logger.info(f"Processing scheduled metrics collection (Run #{self.metrics_count})...")

        try:
            async with get_session() as session:
                schedule_repo = MetricScheduleRepository(session)
                metrics_repo = MetricsRepository(session)

                pending = await schedule_repo.get_pending_schedules()
                logger.info(f"Found {len(pending)} due schedules")

                for schedule in pending:
                    video = schedule.video
                    logger.info(f"Processing {schedule.schedule_type} for {video.shortcode}")

                    try:
                        # Fetch metrics using InstagramService
                        # Video.video_id is the media_pk
                        metrics_data = await self.fetch_metrics_public(video.video_id)

                        # Save to database
                        await metrics_repo.create_metrics_snapshot(
                            video_id=video.id,
                            view_count=metrics_data['view_count'] or 0,
                            like_count=metrics_data['like_count'],
                            comment_count=metrics_data['comment_count'],
                            followers_count=metrics_data['followers_count'] or 0
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
                        await session.commit()

        except Exception as e:
            logger.error(f"Error in process_scheduled_metrics: {e}")


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("STARTING UNIFIED WORKER")
    logger.info("=" * 60)

    # Check if test mode is enabled
    test_mode = settings.test_mode

    if test_mode:
        logger.warning("⚠️  TEST MODE ENABLED - Short intervals for testing!")
        logger.warning("⚠️  Set TEST_MODE=false in .env for production use")

    worker = UnifiedWorker()
    apsched = AsyncIOScheduler()

    # Job 1: Process scheduled metrics
    if test_mode:
        metrics_interval = 10  # 10 seconds in test mode
        logger.info("  - Process metrics: every 10 seconds (TEST MODE)")
    else:
        metrics_interval = 60  # 1 minute in production
        logger.info("  - Process metrics: every 1 minute")

    apsched.add_job(
        worker.process_scheduled_metrics,
        'interval',
        seconds=metrics_interval,
        id='process_metrics'
    )

    # Job 2: Update schedules
    if test_mode:
        schedules_interval = 30  # 30 seconds in test mode
        logger.info("  - Update schedules: every 30 seconds (TEST MODE)")
    else:
        schedules_interval = 86400  # 24 hours in production
        logger.info("  - Update schedules: every 24 hours")

    apsched.add_job(
        worker.update_metric_schedules,
        'interval',
        seconds=schedules_interval,
        id='update_schedules'
    )

    # Job 3: Fetch new videos
    if test_mode:
        videos_interval = 10  # 10 seconds in test mode
        logger.info(f"  - Fetch videos: every 10 seconds (TEST MODE)")
    else:
        videos_interval = settings.worker_interval_hours * 3600  # hours to seconds
        logger.info(f"  - Fetch videos: every {settings.worker_interval_hours} hours")

    apsched.add_job(
        worker.fetch_new_videos,
        'interval',
        seconds=videos_interval,
        id='fetch_videos'
    )

    # Job 4: Update heartbeat (every 30 seconds)
    heartbeat_interval = 30  # 30 seconds
    logger.info(f"  - Update heartbeat: every {heartbeat_interval} seconds")

    apsched.add_job(
        worker.update_heartbeat,
        'interval',
        seconds=heartbeat_interval,
        id='update_heartbeat'
    )

    apsched.start()
    logger.info("Scheduler started")

    # Run initial tasks
    logger.info("Running initial tasks...")
    await worker.update_heartbeat()  # Initial heartbeat
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

        await worker.instagram_service.close()
        apsched.shutdown()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
