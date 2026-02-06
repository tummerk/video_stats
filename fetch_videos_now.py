#!/usr/bin/env python3
"""Manually fetch videos from accounts - for debugging."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.database.session import get_session
from src.repositories.account_repository import AccountRepository
from src.services.instagram_service import InstagramService


async def main():
    """Fetch videos from first account."""
    print("=" * 60)
    print("MANUAL VIDEO FETCH")
    print("=" * 60)

    print(f"\nTest Mode: {settings.test_mode}")
    print(f"Worker Interval: {settings.worker_interval_hours} hours")
    print(f"Reels Limit: {settings.worker_reels_limit}")

    # Init service
    service = InstagramService(db_session_factory=get_session)

    try:
        async with get_session() as session:
            account_repo = AccountRepository(session)
            accounts = await account_repo.get_all()

            print(f"\nFound {len(accounts)} accounts in database")

            if not accounts:
                print("No accounts found!")
                return

            # Fetch from first 3 accounts only
            for account in accounts[:3]:
                print(f"\n{'=' * 60}")
                print(f"Processing: @{account.username} (id={account.id})")
                print('=' * 60)

                try:
                    await service.get_user_recent_videos(
                        user_pk=account.id,
                        username=account.username,
                        limit=2  # Only 2 videos for testing
                    )
                    print(f"✓ Successfully processed @{account.username}")
                except Exception as e:
                    print(f"✗ ERROR for @{account.username}: {type(e).__name__}: {e}")

                await session.commit()

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
