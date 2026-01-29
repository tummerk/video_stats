"""
Run both workers (new video and metrics) in a single process.

This is the recommended way to run both workers together.
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from worker_new_video import (
    InstagramService as NewVideoInstagramService,
    AudioDownloadService,
    TranscriptionService,
    ReelsWorker
)
from worker_metrics import (
    InstagramService as MetricsInstagramService,
    MetricsCollectionService,
    MetricsScheduler,
    MetricsWorker
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main_async():
    """Run both workers in a single process."""
    logger.info("=" * 60)
    logger.info("STARTING INSTAGRAM REELS WORKERS")
    logger.info("=" * 60)

    # ========================================================================
    # Initialize New Video Worker
    # ========================================================================
    logger.info("Initializing New Video Worker...")
    instagram_service_new = NewVideoInstagramService()
    audio_service = AudioDownloadService(settings.audio_dir)
    transcription_service = TranscriptionService(model_size="base")
    new_video_worker = ReelsWorker(
        instagram_service_new,
        audio_service,
        transcription_service
    )

    # ========================================================================
    # Initialize Metrics Worker
    # ========================================================================
    logger.info("Initializing Metrics Worker...")
    instagram_service_metrics = MetricsInstagramService()
    metrics_service = MetricsCollectionService(instagram_service_metrics)
    scheduler = MetricsScheduler()
    metrics_worker = MetricsWorker(metrics_service, scheduler)

    # ========================================================================
    # Setup Scheduler
    # ========================================================================
    logger.info("Setting up scheduler...")

    apsched = AsyncIOScheduler()

    # New video worker: every N hours (from config)
    apsched.add_job(
        new_video_worker.run,
        'interval',
        hours=settings.worker_interval_hours,
        id='fetch_new_videos',
        name='Fetch and process new videos'
    )
    logger.info(f"  - New video worker: every {settings.worker_interval_hours} hours")

    # Metrics worker: every hour
    apsched.add_job(
        metrics_worker.run,
        'interval',
        hours=1,
        id='collect_metrics',
        name='Collect metrics and update schedules'
    )
    logger.info("  - Metrics worker: every 1 hour")

    # Start scheduler
    apsched.start()
    logger.info("Scheduler started")
    logger.info("")

    # ========================================================================
    # Run initial tasks
    # ========================================================================
    logger.info("=" * 60)
    logger.info("RUNNING INITIAL TASKS")
    logger.info("=" * 60)

    logger.info("Running initial new video fetch...")
    try:
        await new_video_worker.run()
    except Exception as e:
        logger.error(f"New video worker failed: {e}")

    logger.info("Running initial metrics collection...")
    try:
        await metrics_worker.run()
    except Exception as e:
        logger.error(f"Metrics worker failed: {e}")

    # ========================================================================
    # Keep running
    # ========================================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("WORKERS ARE RUNNING")
    logger.info("=" * 60)
    logger.info(f"New video worker: every {settings.worker_interval_hours} hours")
    logger.info("Metrics worker: every 1 hour")
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    try:
        # Run forever
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        logger.info("")
        logger.info("=" * 60)
        logger.info("SHUTTING DOWN WORKERS")
        logger.info("=" * 60)
        apsched.shutdown()
        logger.info("Scheduler stopped")
        logger.info("Workers stopped")


def main():
    """Entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")


if __name__ == "__main__":
    main()
