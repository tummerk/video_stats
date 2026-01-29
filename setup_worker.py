"""
Quick setup script for NEW_VIDEO worker.

This script helps you:
1. Verify environment configuration
2. Create audio directory
3. Test Instagram connection
4. Add a test account to database
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


def check_env():
    """Check and report on environment configuration."""
    print("=" * 60)
    print("Environment Configuration Check")
    print("=" * 60)

    required = {
        "DATABASE_URL": "PostgreSQL connection string",
        "INSTAGRAM_SESSIONID": "Instagram session cookie",
        "INSTAGRAM_DS_USER_ID": "Instagram user ID cookie",
        "INSTAGRAM_CSRFTOKEN": "Instagram CSRF token",
        "INSTAGRAM_MID": "Instagram MID cookie",
    }

    optional = {
        "WORKER_INTERVAL_HOURS": "6",
        "WORKER_REELS_LIMIT": "50",
        "AUDIO_DIR": "audio",
    }

    all_good = True

    print("\nRequired Variables:")
    for var, description in required.items():
        value = os.getenv(var)
        if value:
            preview = value[:20] + "..." if len(value) > 20 else value
            print(f"  ✓ {var}: {preview}")
        else:
            print(f"  ✗ {var}: NOT SET ({description})")
            all_good = False

    print("\nOptional Variables (using defaults if not set):")
    for var, default in optional.items():
        value = os.getenv(var, default)
        print(f"  • {var}: {value}")

    return all_good


def create_audio_dir():
    """Create audio directory if it doesn't exist."""
    print("\n" + "=" * 60)
    print("Audio Directory Setup")
    print("=" * 60)

    audio_dir = os.getenv("AUDIO_DIR", "audio")

    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
        print(f"✓ Created directory: {audio_dir}/")
    else:
        print(f"✓ Directory exists: {audio_dir}/")

    # Add to .gitignore if not present
    gitignore_path = ".gitignore"
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()
        if audio_dir not in content:
            with open(gitignore_path, "a") as f:
                f.write(f"\n{audio_dir}/\n")
            print(f"✓ Added {audio_dir}/ to .gitignore")
    else:
        print(f"  (No .gitignore found)")


def test_imports():
    """Test that all required modules can be imported."""
    print("\n" + "=" * 60)
    print("Dependency Check")
    print("=" * 60)

    modules = [
        ("instaloader", "Instagram scraper"),
        ("yt_dlp", "YouTube/Instagram downloader"),
        ("whisper", "OpenAI Whisper (transcription)"),
        ("apscheduler", "Task scheduler"),
        ("sqlalchemy", "Database ORM"),
        ("asyncpg", "Async PostgreSQL driver"),
    ]

    all_good = True
    for module, description in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}: {description}")
        except ImportError:
            print(f"  ✗ {module}: NOT INSTALLED ({description})")
            all_good = False

    return all_good


async def test_database():
    """Test database connection."""
    print("\n" + "=" * 60)
    print("Database Connection Test")
    print("=" * 60)

    try:
        from src.database import get_session
        from src.repositories.account_repository import AccountRepository

        async with get_session() as session:
            repo = AccountRepository(session)
            accounts = await repo.get_all()

        print(f"✓ Database connection successful")
        print(f"  Current accounts in database: {len(accounts)}")

        for account in accounts:
            print(f"    - {account.username}")

        return True

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Check DATABASE_URL in .env")
        print("  3. Run: alembic upgrade head")
        return False


async def add_test_account():
    """Optionally add a test account."""
    print("\n" + "=" * 60)
    print("Add Test Account")
    print("=" * 60)

    username = input("Enter Instagram username to add (or press Enter to skip): ").strip()

    if not username:
        print("Skipped.")
        return

    try:
        from src.database import get_session
        from src.repositories.account_repository import AccountRepository

        async with get_session() as session:
            repo = AccountRepository(session)

            # Check if exists
            existing = await repo.get_by_username(username)
            if existing:
                print(f"Account '{username}' already exists in database (id={existing.id})")
            else:
                account = await repo.create(
                    username=username,
                    profile_url=f"https://www.instagram.com/{username}/",
                    followers_count=0
                )
                print(f"✓ Added account '{username}' to database (id={account.id})")

    except Exception as e:
        print(f"✗ Failed to add account: {e}")


def main():
    """Run all setup checks."""
    print("\n🚀 NEW_VIDEO Worker Setup")
    print()

    # Check environment
    env_ok = check_env()

    # Check imports
    imports_ok = test_imports()

    # Create audio directory
    create_audio_dir()

    # Test database
    if env_ok and imports_ok:
        db_ok = asyncio.run(test_database())

        # Optionally add account
        if db_ok:
            asyncio.run(add_test_account())

    # Final summary
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)

    if env_ok and imports_ok:
        print("\n✓ Setup complete! You can now run:")
        print("\n  1. Test configuration:")
        print("     python test_worker.py")
        print("\n  2. Run worker continuously:")
        print("     python worker_new_video.py")
        print("\n  3. Run once (no scheduler):")
        print("     python -c 'import asyncio; from worker_new_video import fetch_and_process_reels; asyncio.run(fetch_and_process_reels())'")
    else:
        print("\n✗ Setup incomplete. Please fix the issues above:")
        if not env_ok:
            print("  • Set missing environment variables in .env")
        if not imports_ok:
            print("  • Install missing dependencies: pip install -r requirements.txt")

    print("\n" + "=" * 60)
    print()


if __name__ == "__main__":
    main()
