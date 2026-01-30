"""View all videos in the database."""

import asyncio
import sys
import io

# Fix Unicode output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlalchemy import select
from src.database.session import get_session
from src.models.video import Video
from src.models.account import Account


async def view_videos():
    """Display all videos with their account information."""
    async with get_session() as session:
        # Query all videos with account information
        result = await session.execute(
            select(Video, Account)
            .join(Account, Video.account_id == Account.id)
            .order_by(Video.published_at.desc())
        )
        rows = result.all()

        if not rows:
            print("No videos found in the database.")
            return

        print(f"\n{'='*120}")
        print(f"Total videos: {len(rows)}")
        print(f"{'='*120}\n")

        for video, account in rows:
            print(f"ID: {video.id}")
            print(f"Account: @{account.username}")
            print(f"Shortcode: {video.shortcode}")
            print(f"Video ID: {video.video_id}")
            print(f"Published: {video.published_at}")
            print(f"Caption: {video.caption[:100] + '...' if video.caption and len(video.caption) > 100 else video.caption}")
            print(f"Audio URL: {video.audio_url}")
            print(f"Audio File: {video.audio_file_path}")
            print(f"Transcription: {'Yes' if video.transcription else 'No'}")
            if video.transcription:
                print(f"Transcription Preview: {video.transcription[:150]}...")
            print(f"Created: {video.created_at}")
            print(f"Updated: {video.updated_at}")
            print(f"{'-'*120}\n")


if __name__ == "__main__":
    asyncio.run(view_videos())
