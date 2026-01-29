"""
Add Instagram accounts to the database for the worker to process.

Usage:
    python add_account.py username1 username2 username3
"""

import asyncio
import sys


async def add_accounts(usernames):
    """Add accounts to database."""
    from src.database import get_session
    from src.repositories.account_repository import AccountRepository

    async with get_session() as session:
        repo = AccountRepository(session)

        for username in usernames:
            username = username.strip()
            if not username:
                continue

            # Check if exists
            existing = await repo.get_by_username(username)

            if existing:
                print(f"✓ Account '{username}' already exists (id={existing.id})")
            else:
                account = await repo.create(
                    username=username,
                    profile_url=f"https://www.instagram.com/{username}/",
                    followers_count=0
                )
                print(f"✓ Added account '{username}' (id={account.id})")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python add_account.py username1 username2 ...")
        print("\nExample:")
        print("  python add_account.py instagram_user1 instagram_user2")
        sys.exit(1)

    usernames = sys.argv[1:]
    print(f"Adding {len(usernames)} account(s) to database...")
    asyncio.run(add_accounts(usernames))


if __name__ == "__main__":
    main()
