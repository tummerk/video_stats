import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.database.session import get_session
from src.config import settings
from src.models import Video
from src.repositories.video_repository import VideoRepository
from src.repositories.metrics_repository import MetricsRepository
from src.repositories.metric_schedule_repository import MetricScheduleRepository
from src.services.instagram_service import InstagramService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsCollectionService:
    """Service for collecting and saving metrics from Instagram."""

    def __init__(self, instagram_service: InstagramService):
        self.instagram = instagram_service

    async def fetch_metrics(self, shortcode: str) -> dict:
        """Get metrics from Instagram via Instaloader.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Dictionary with view_count, like_count, comment_count, followers_count
        """
        logger.info(f"Fetching metrics for shortcode: {shortcode}")
        return await self.instagram.get_post_metrics(shortcode)

    async def collect_and_save_metrics(
        self,
        video: Video,
        metrics_repo: MetricsRepository
    ) -> bool:
        """Collect metrics from Instagram and save to database.

        Args:
            video: Video object
            metrics_repo: MetricsRepository instance

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch metrics from Instagram
            metrics_data = await self.fetch_metrics(video.shortcode)

            # Create metrics snapshot in database
            await metrics_repo.create_metrics_snapshot(
                video_id=video.id,
                view_count=metrics_data['view_count'] or 0,
                like_count=metrics_data['like_count'],
                comment_count=metrics_data['comment_count'],
                followers_count=metrics_data['followers_count'] or 0
            )

            logger.info(
                f"Saved metrics for video {video.shortcode}: "
                f"views={metrics_data['view_count']}, "
                f"likes={metrics_data['like_count']}, "
                f"comments={metrics_data['comment_count']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to collect metrics for video {video.shortcode}: {e}")
            return False


class MetricsScheduler:
    """Scheduler for creating and managing metric collection schedules."""

    SCHEDULE_INTERVALS = [
        ('60min', timedelta(minutes=60)),
        ('3h', timedelta(hours=3)),
        ('24h', timedelta(hours=24)),
        ('48h', timedelta(hours=48)),
        ('72h', timedelta(hours=72)),
    ]

    async def create_schedule_for_video(
        self,
        video: Video,
        schedule_repo: MetricScheduleRepository
    ):
        """Create metric collection schedule for a video.

        Calculates appropriate schedule based on video's published_at time
        and existing schedules.

        Args:
            video: Video object
            schedule_repo: MetricScheduleRepository instance
        """
        # Get existing schedules for this video
        existing_schedules = await schedule_repo.get_schedules_by_video(video.id)

        # Determine next schedule type and time
        next_schedule = self.calculate_next_schedule_type(
            video.published_at,
            existing_schedules
        )

        if next_schedule is None:
            logger.debug(f"No new schedule needed for video {video.shortcode}")
            return

        schedule_type, scheduled_at = next_schedule

        # Create the schedule
        await schedule_repo.create_schedule(
            video_id=video.id,
            schedule_type=schedule_type,
            scheduled_at=scheduled_at,
            status="pending"
        )

        logger.info(
            f"Created {schedule_type} schedule for video {video.shortcode} "
            f"at {scheduled_at}"
        )

    def calculate_next_schedule_type(
        self,
        published_at: datetime,
        existing_schedules: list
    ) -> Optional[Tuple[str, datetime]]:
        """Determine the next schedule type and time for a video.

        Args:
            published_at: When the video was published
            existing_schedules: List of existing MetricSchedule objects

        Returns:
            Tuple of (schedule_type, scheduled_at) or None if no schedule needed
        """
        now = datetime.utcnow()
        time_since_publish = now - published_at

        # Get existing schedule types
        existing_types = {s.schedule_type for s in existing_schedules}

        # For videos less than 72 hours old
        if time_since_publish < timedelta(hours=72):
            # Find the next interval that hasn't been scheduled yet
            for schedule_type, interval in self.SCHEDULE_INTERVALS:
                if schedule_type not in existing_types:
                    # Calculate when this should be scheduled
                    scheduled_time = published_at + interval

                    # Only create if it's in the future
                    if scheduled_time > now:
                        return (schedule_type, scheduled_time)
                    else:
                        # This interval has passed, skip it
                        logger.debug(
                            f"Skipping {schedule_type} for video published "
                            f"{time_since_publish.total_seconds() / 3600:.1f}h ago"
                        )
            return None

        # For videos older than 72 hours, create daily schedules
        return self._calculate_daily_schedule(published_at, existing_schedules, now)

    def _calculate_daily_schedule(
        self,
        published_at: datetime,
        existing_schedules: list,
        now: datetime
    ) -> Optional[Tuple[str, datetime]]:
        """Calculate the next daily schedule for videos older than 72h.

        Args:
            published_at: When the video was published
            existing_schedules: List of existing MetricSchedule objects
            now: Current time

        Returns:
            Tuple of ('daily', scheduled_at) or None if not needed yet
        """
        # Get the latest daily schedule
        daily_schedules = [
            s for s in existing_schedules
            if s.schedule_type == 'daily' and s.status == 'completed'
        ]

        if daily_schedules:
            # Get the most recent completed daily schedule
            last_daily = max(daily_schedules, key=lambda x: x.scheduled_at)
            last_schedule_time = last_daily.scheduled_at

            # Only create new schedule if 24h have passed since last one
            if now - last_schedule_time < timedelta(hours=24):
                logger.debug(
                    f"Daily schedule too recent for video "
                    f"(last: {last_schedule_time})"
                )
                return None

            # Schedule for 24h after the last daily
            next_time = last_schedule_time + timedelta(hours=24)
            return ('daily', next_time)

        else:
            # No daily schedules exist yet, start daily tracking
            # Schedule for the next round hour
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            return ('daily', next_hour)


class MetricsWorker:
    """Main worker for scheduling and collecting metrics."""

    def __init__(
        self,
        metrics_service: MetricsCollectionService,
        scheduler: MetricsScheduler
    ):
        self.metrics_service = metrics_service
        self.scheduler = scheduler

    async def update_schedules(self):
        """Check for new videos and create schedules.

        Runs every hour to find videos that need metric collection schedules.
        """
        logger.info("Checking for videos needing schedule updates...")

        async with get_session() as session:
            video_repo = VideoRepository(session)
            schedule_repo = MetricScheduleRepository(session)

            # Get videos that need schedules
            videos = await video_repo.get_videos_for_schedule_update(limit=100)

            logger.info(f"Found {len(videos)} videos needing schedules")

            for video in videos:
                try:
                    await self.scheduler.create_schedule_for_video(video, schedule_repo)
                except Exception as e:
                    logger.error(
                        f"Failed to create schedule for video {video.shortcode}: {e}"
                    )

    async def process_scheduled_metrics(self):
        """Execute scheduled metric collection tasks.

        Finds all pending schedules that are due and collects metrics.
        """
        logger.info("Processing scheduled metrics collection...")

        async with get_session() as session:
            schedule_repo = MetricScheduleRepository(session)
            metrics_repo = MetricsRepository(session)

            # Get pending schedules that are due
            pending_schedules = await schedule_repo.get_pending_schedules()

            logger.info(f"Found {len(pending_schedules)} due schedules")

            for schedule in pending_schedules:
                video = schedule.video
                logger.info(
                    f"Processing {schedule.schedule_type} schedule "
                    f"for video {video.shortcode}"
                )

                try:
                    # Collect and save metrics
                    success = await self.metrics_service.collect_and_save_metrics(
                        video, metrics_repo
                    )

                    if success:
                        # Mark schedule as completed
                        await schedule_repo.mark_completed(schedule.id)

                        # Create next schedule if needed
                        await self.scheduler.create_schedule_for_video(
                            video, schedule_repo
                        )
                    else:
                        # Mark schedule as failed
                        await schedule_repo.mark_failed(schedule.id)

                except Exception as e:
                    logger.error(
                        f"Failed to process schedule {schedule.id}: {e}"
                    )
                    await schedule_repo.mark_failed(schedule.id)

    async def run(self):
        """Main worker task.

        Updates schedules and processes scheduled metrics.
        Called by APScheduler every hour.
        """
        logger.info("Worker run started")
        try:
            await self.update_schedules()
            await self.process_scheduled_metrics()
        except Exception as e:
            logger.error(f"Worker run failed: {e}")
        logger.info("Worker run completed")


async def main_async():
    """Main entry point for the metrics worker."""
    logger.info("Starting Instagram Reels Metrics Worker")

    # Initialize services
    instagram_service = InstagramService()
    metrics_service = MetricsCollectionService(instagram_service)
    scheduler = MetricsScheduler()
    worker = MetricsWorker(metrics_service, scheduler)

    # Create APScheduler
    apsched = AsyncIOScheduler()

    # Add hourly job for schedule updates and metric collection
    apsched.add_job(
        worker.run,
        'interval',
        hours=1,
        id='update_and_collect_metrics',
        name='Update schedules and collect metrics'
    )

    # Start scheduler
    apsched.start()
    logger.info("Scheduler started - running every hour")

    # Run immediately on startup
    logger.info("Running initial collection...")
    await worker.run()

    # Keep running
    logger.info("Worker is running. Press Ctrl+C to stop.")

    try:
        # Wait forever
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down worker...")
        apsched.shutdown()
        logger.info("Worker stopped")


def main():
    """Entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")


if __name__ == "__main__":
    main()
