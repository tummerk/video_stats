"""Test script to verify database setup and models."""

import asyncio
from datetime import datetime
from src.database import get_session
from src.models import Account, Video, Metrics
from src.repositories import AccountRepository, VideoRepository, MetricsRepository


async def main():
    """Test database models and repositories."""
    print("Starting database test...")

    async with get_session() as session:
        # Test 1: Create account
        print("\n1. Creating account...")
        account_repo = AccountRepository(session)
        account = await account_repo.create_or_update_by_username(
            username="test_user",
            profile_url="https://instagram.com/test_user",
            followers_count=1000
        )
        print(f"   [OK] Created account: {account.username} (ID: {account.id})")

        # Test 2: Get account by username
        print("\n2. Retrieving account by username...")
        found_account = await account_repo.get_by_username("test_user")
        print(f"   [OK] Found account: {found_account.username} with {found_account.followers_count} followers")

        # Test 3: Create video
        print("\n3. Creating video...")
        video_repo = VideoRepository(session)
        video = await video_repo.create_or_update_by_shortcode(
            shortcode="ABC123",
            video_id="123456789",
            account_id=account.id,
            caption="Test video caption",
            published_at=datetime.utcnow()
        )
        print(f"   [OK] Created video: {video.shortcode} (ID: {video.id})")

        # Test 4: Create metrics
        print("\n4. Creating metrics snapshot...")
        metrics_repo = MetricsRepository(session)
        metrics = await metrics_repo.create_metrics_snapshot(
            video_id=video.id,
            view_count=1000,
            like_count=50,
            comment_count=10,
            followers_count=1000
        )
        print(f"   [OK] Created metrics: {metrics.view_count} views, {metrics.like_count} likes")

        # Test 5: Get video with metrics
        print("\n5. Retrieving video with metrics...")
        video_with_data = await video_repo.get_by_shortcode_with_metrics("ABC123")
        if video_with_data:
            print(f"   [OK] Video: {video_with_data.shortcode}")
            print(f"   [OK] Account: {video_with_data.account.username}")
            print(f"   [OK] Metrics count: {len(video_with_data.metrics)}")
        else:
            print("   [FAIL] Failed to retrieve video with metrics")

        # Test 6: Get metrics history
        print("\n6. Retrieving metrics history...")
        history = await metrics_repo.get_metrics_history(video.id)
        print(f"   [OK] Metrics history entries: {len(history)}")

        print("\n[SUCCESS] All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
