"""Import Instagram usernames from JSON file to database.

Simple script to add all usernames from usernames.json to database.
The worker will fetch user_pk automatically on first run.
"""
import asyncio
import json
from pathlib import Path

from src.database.session import get_session
from src.repositories.account_repository import AccountRepository


async def import_accounts():
    """Import accounts from usernames.json to database."""
    # Read usernames from JSON
    usernames_file = Path(__file__).parent / "usernames.json"

    with open(usernames_file, 'r', encoding='utf-8') as f:
        usernames = json.load(f)

    print(f"Found {len(usernames)} usernames in file")
    print("=" * 60)

    async with get_session() as session:
        account_repo = AccountRepository(session)

        added = 0
        skipped = 0
        errors = []

        for username in usernames:
            try:
                # Check if account already exists
                existing = await account_repo.get_by_username(username)

                if existing:
                    skipped += 1
                    print(f"⏭️  SKIP: {username} (already exists)")
                else:
                    # Create account with username only
                    # user_pk will be fetched later by worker
                    await account_repo.create(
                        username=username,
                        profile_url=f"https://www.instagram.com/{username}/",
                        followers_count=0,
                    )
                    added += 1
                    print(f"✅ ADD: {username}")

            except Exception as e:
                errors.append((username, str(e)))
                print(f"❌ ERROR: {username} - {e}")

        # Commit all changes
        await session.commit()

        print("\n" + "=" * 60)
        print("IMPORT SUMMARY:")
        print(f"  ✅ Added:   {added}")
        print(f"  ⏭️  Skipped: {skipped}")
        print(f"  ❌ Errors:  {len(errors)}")

        if errors:
            print("\nErrors:")
            for username, error in errors:
                print(f"  - {username}: {error}")

        print("\n" + "=" * 60)
        print("NEXT STEP: Run worker to fetch user_pk for all accounts")
        print("  python unified_worker.py")


if __name__ == "__main__":
    asyncio.run(import_accounts())
