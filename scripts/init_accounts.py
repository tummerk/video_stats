"""
Initialize database with Instagram accounts from JSON file.

This script resolves Instagram usernames to user_pk values and creates accounts in the database.
"""
import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import get_session
from src.repositories.account_repository import AccountRepository
from src.services.instagram_service import InstagramService
from src.config import settings


async def resolve_username_to_user_pk(instagram_service: InstagramService, username: str) -> int:
    """Resolve Instagram username to user_pk.

    Args:
        instagram_service: Authenticated InstagramService instance
        username: Instagram username (without @)

    Returns:
        Instagram user_pk (integer ID)

    Raises:
        Exception: If user not found or resolution fails
    """
    # Use instagrapi's user_id_from_username method
    def _get_user_id(client, username: str) -> int:
        return client.user_id_from_username(username)

    user_pk = await instagram_service._execute_instagram_request(_get_user_id, username)
    return user_pk


async def init_accounts_from_json(json_file: str):
    """Initialize accounts from JSON file.

    JSON format:
    [
        {"username": "instagram_user1"},
        {"username": "instagram_user2", "user_pk": 123456789},
        ...
    ]

    If user_pk is provided, it will be used directly.
    If only username is provided, it will be resolved via Instagram API.

    Args:
        json_file: Path to JSON file with accounts
    """
    # Load accounts from JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        accounts_data = json.load(f)

    print(f"Loaded {len(accounts_data)} accounts from {json_file}")

    # Initialize Instagram service
    instagram_service = InstagramService()

    try:
        # Authenticate
        print("Authenticating with Instagram...")
        await instagram_service._authenticate_client()
        print("✓ Authenticated successfully")

        # Process accounts
        async with get_session() as session:
            account_repo = AccountRepository(session)

            results = {"created": 0, "skipped": 0, "errors": []}

            for idx, account_data in enumerate(accounts_data, 1):
                username = account_data.get("username")
                user_pk = account_data.get("user_pk")

                if not username:
                    results["errors"].append(f"{idx}: Missing username")
                    continue

                try:
                    # Check if account already exists
                    existing = await account_repo.get_by_username(username)
                    if existing:
                        print(f"[{idx}/{len(accounts_data)}] Skipping {username} (already exists)")
                        results["skipped"] += 1
                        continue

                    # Resolve user_pk if not provided
                    if not user_pk:
                        print(f"[{idx}/{len(accounts_data)}] Resolving user_pk for @{username}...")
                        user_pk = await resolve_username_to_user_pk(instagram_service, username)
                        print(f"  → Resolved to user_pk: {user_pk}")

                    # Create account with user_pk as ID
                    await account_repo.create(
                        id=user_pk,
                        username=username,
                        profile_url=f"https://www.instagram.com/{username}/",
                        followers_count=0
                    )

                    print(f"  ✓ Created account: @{username} (ID: {user_pk})")
                    results["created"] += 1

                    # Rate limiting: 1 second between requests
                    await asyncio.sleep(1)

                except Exception as e:
                    error_msg = f"{username}: {str(e)}"
                    print(f"  ✗ Error: {error_msg}")
                    results["errors"].append(error_msg)

            # Commit all changes
            await session.commit()

        # Print summary
        print("\n" + "="*60)
        print("INITIALIZATION COMPLETE")
        print("="*60)
        print(f"Created:  {results['created']}")
        print(f"Skipped:  {results['skipped']}")
        print(f"Errors:   {len(results['errors'])}")

        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")

    finally:
        await instagram_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize Instagram accounts in database")
    parser.add_argument("json_file", help="Path to JSON file with accounts")
    args = parser.parse_args()

    if not Path(args.json_file).exists():
        print(f"Error: File not found: {args.json_file}")
        sys.exit(1)

    asyncio.run(init_accounts_from_json(args.json_file))
