"""
Quick start script for unified_worker.py

This script helps you quickly set up and start the worker with proper error handling.
"""
import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")

def check_env():
    """Check if .env exists."""
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("\nPlease create .env file first:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("2. Edit .env and set at minimum:")
        print("   - DATABASE_URL (e.g., postgresql+asyncpg://user:pass@localhost:5432/dbname)")
        print("   - INSTAGRAM_SESSIONID or INSTAGRAM_USERNAME/PASSWORD")
        print("\nRun this script again after configuring .env")
        return False
    return True

def install_dependencies():
    """Install required dependencies."""
    print_header("Installing dependencies")

    dependencies = [
        "sqlalchemy",
        "asyncpg",
        "psycopg2-binary",
        "instagrapi",
        "yt-dlp",
        "apscheduler",
        "python-dotenv",
        "pydantic-settings",
    ]

    print(f"Installing: {', '.join(dependencies)}\n")

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", *dependencies
        ])
        print("\n✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to install dependencies: {e}")
        return False

def check_directories():
    """Create required directories."""
    from dotenv import load_dotenv
    load_dotenv()

    audio_dir = os.getenv('AUDIO_DIR', 'audio')

    if not Path(audio_dir).exists():
        print(f"Creating directory: {audio_dir}")
        Path(audio_dir).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {audio_dir}/")
    else:
        print(f"✅ Directory {audio_dir}/ exists")

def run_database_migrations():
    """Ask user if they want to run migrations."""
    print_header("Database migrations")

    response = input("Do you want to run database migrations? (y/n): ").lower().strip()

    if response == 'y':
        try:
            print("Running: alembic upgrade head")
            subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
            print("✅ Migrations completed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Migration failed: {e}")
            print("You may need to install alembic: pip install alembic")
            return False
    else:
        print("⚠️  Skipping migrations")
        print("If you get database errors, run: alembic upgrade head")
        return True

def test_import():
    """Test if unified_worker can be imported."""
    print_header("Testing imports")

    try:
        from unified_worker import UnifiedWorker
        print("✅ unified_worker.py imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure all dependencies are installed:")
        print("  pip install sqlalchemy asyncpg instagrapi yt-dlp apscheduler python-dotenv pydantic-settings")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def start_worker():
    """Start the worker."""
    print_header("Starting unified_worker.py")

    print("🚀 Starting worker...")
    print("Press Ctrl+C to stop\n")

    try:
        subprocess.run([sys.executable, "unified_worker.py"])
    except KeyboardInterrupt:
        print("\n\n👋 Worker stopped by user")
    except Exception as e:
        print(f"\n❌ Error running worker: {e}")
        return False

    return True

def main():
    """Main setup and start flow."""
    print_header("Unified Worker Quick Start")

    # Step 1: Check .env
    if not check_env():
        return 1

    # Step 2: Ask about dependencies
    print_header("Dependencies check")
    deps_response = input("Install/update dependencies? (y/n): ").lower().strip()

    if deps_response == 'y':
        if not install_dependencies():
            return 1

    # Step 3: Create directories
    check_directories()

    # Step 4: Run migrations
    if not run_database_migrations():
        return 1

    # Step 5: Test imports
    if not test_import():
        return 1

    # Step 6: Ask if ready to start
    print_header("Ready to start")
    print("✅ All checks passed!")
    print("\nThe worker will:")
    print("  • Fetch new videos every 6 hours")
    print("  • Update metric schedules every 1 hour")
    print("  • Collect metrics every 1 minute")
    print("\nMake sure:")
    print("  • PostgreSQL is running")
    print("  • Database exists")
    print("  • At least one Instagram account is in the database")

    start_response = input("\nStart the worker now? (y/n): ").lower().strip()

    if start_response == 'y':
        start_worker()
    else:
        print("\nTo start the worker manually, run:")
        print("  python unified_worker.py")
        print("\nOr with logging:")
        print("  python unified_worker.py 2>&1 | tee worker.log")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
        sys.exit(1)
