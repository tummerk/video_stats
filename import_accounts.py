"""
Import Instagram accounts from usernames.json file to the database.

Usage:
    python import_accounts.py
"""

import asyncio
import json


async def import_accounts():
    """Import accounts from usernames.json to database."""
    from src.database import get_session
    from src.repositories.account_repository import AccountRepository

    # Load usernames from file
    try:
        with open('usernames.json', 'r', encoding='utf-8') as f:
            usernames = json.load(f)
    except FileNotFoundError:
        print("Error: usernames.json file not found")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in usernames.json: {e}")
        return

    if not isinstance(usernames, list):
        print("Error: usernames.json must contain a JSON array")
        return

    print(f"Found {len(usernames)} usernames in usernames.json")

    async with get_session() as session:
        repo = AccountRepository(session)

        added_count = 0
        skipped_count = 0

        for username in usernames:
            username = username.strip()
            if not username:
                continue

            # Check if exists
            existing = await repo.get_by_username(username)

            if existing:
                skipped_count += 1
                print(f"- Skipped '{username}' (already exists, id={existing.id})")
            else:
                account = await repo.create(
                    username=username,
                    profile_url=f"https://www.instagram.com/{username}/",
                    followers_count=0
                )
                added_count += 1
                print(f"+ Added '{username}' (id={account.id})")

        print(f"\nSummary: {added_count} added, {skipped_count} skipped")


def main():
    """Main entry point."""
    print("Importing accounts from usernames.json...")
    asyncio.run(import_accounts())


if __name__ == "__main__":
    main()
