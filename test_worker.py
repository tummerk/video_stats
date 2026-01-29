"""
Test script for worker_new_video module.

Run this to verify:
1. Instagram client setup
2. Database connection
3. Account retrieval
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_vars():
    """Test that required environment variables are set."""
    print("Testing environment variables...")

    required_vars = [
        "DATABASE_URL",
        "INSTAGRAM_SESSIONID",
        "INSTAGRAM_DS_USER_ID",
        "INSTAGRAM_CSRFTOKEN",
        "INSTAGRAM_MID"
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            # Show first few chars to confirm it's set
            preview = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✓ {var}: {preview}")

    if missing:
        print(f"\n✗ Missing environment variables: {', '.join(missing)}")
        print("Please set them in your .env file")
        return False

    print("\n✓ All required environment variables are set")
    return True


def test_instaloader_client():
    """Test Instagram client creation."""
    print("\nTesting Instaloader client creation...")

    try:
        from worker_new_video import create_instaloader_client
        L = create_instaloader_client()
        print("✓ Instaloader client created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create Instaloader client: {e}")
        return False


async def test_database_connection():
    """Test database connection and account retrieval."""
    print("\nTesting database connection...")

    try:
        from src.database import get_session
        from src.repositories.account_repository import AccountRepository

        async with get_session() as session:
            account_repo = AccountRepository(session)
            accounts = await account_repo.get_all()
            print(f"✓ Database connection successful")
            print(f"  Found {len(accounts)} accounts in database")

            if accounts:
                for account in accounts[:5]:  # Show first 5
                    print(f"    - {account.username} (id={account.id})")

            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Worker Configuration Test")
    print("=" * 60)

    results = []

    # Test 1: Environment variables
    results.append(("Environment Variables", test_env_vars()))

    # Test 2: Instaloader client
    results.append(("Instaloader Client", test_instaloader_client()))

    # Test 3: Database connection
    results.append(("Database Connection", asyncio.run(test_database_connection())))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All tests passed! Worker is ready to run.")
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")

    print("=" * 60)


if __name__ == "__main__":
    main()
