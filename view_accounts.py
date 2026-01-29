"""View all accounts in the database."""

import asyncio
from src.database import get_session
from src.repositories.account_repository import AccountRepository
from sqlalchemy import select


async def main():
    async with get_session() as session:
        repo = AccountRepository(session)

        # Get all accounts
        accounts = await repo.get_all()

        print(f"\nВсего аккаунтов в базе данных: {len(accounts)}\n")
        print("=" * 70)
        print(f"{'ID':<5} {'Username':<20} {'Followers':<15} {'Profile URL'}")
        print("=" * 70)

        for account in accounts:
            username = account.username or "N/A"
            followers = account.followers_count or 0
            profile_url = account.profile_url or "N/A"

            print(f"{account.id:<5} {username:<20} {followers:<15} {profile_url}")

        print("=" * 70)
        print()


if __name__ == "__main__":
    asyncio.run(main())
