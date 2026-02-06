"""
Environment Checker for unified_worker.py

This script verifies that all necessary components are properly configured
before running the unified worker.
"""
import asyncio
import os
import sys
from pathlib import Path

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ{Colors.END} {text}")

def check_env_file():
    """Check if .env file exists and has required variables."""
    print_header("Checking .env file")

    env_path = Path('.env')
    if not env_path.exists():
        print_error(".env file not found!")
        print_info("Copy .env.example to .env and fill in your values:")
        print("  cp .env.example .env")
        return False

    print_success(".env file exists")

    # Load and check required variables
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = {
        'DATABASE_URL': 'Database connection string',
    }

    optional_vars = {
        'INSTAGRAM_SESSIONID': 'Instagram session ID',
        'INSTAGRAM_USERNAME': 'Instagram username',
        'INSTAGRAM_PASSWORD': 'Instagram password',
        'INSTAGRAM_PROXY': 'Instagram proxy (optional)',
    }

    all_good = True

    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value in [f'{var.lower()}_here', f'your_{var.lower()}_here', '']:
            print_error(f"{var} is not set ({description})")
            all_good = False
        else:
            print_success(f"{var} is set")

    # Check optional variables
    has_auth = False
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value and value not in [f'your_{var.lower()}_here', '', ' ']:
            print_success(f"{var} is set")
            if var in ['INSTAGRAM_SESSIONID', 'INSTAGRAM_USERNAME', 'INSTAGRAM_PASSWORD']:
                has_auth = True
        else:
            print_info(f"{var} is not set ({description})")

    if not has_auth:
        print_warning("No Instagram authentication method configured!")
        print_info("Set at least one of: INSTAGRAM_SESSIONID or INSTAGRAM_USERNAME/PASSWORD")

    return all_good

def check_dependencies():
    """Check if required Python packages are installed."""
    print_header("Checking Python dependencies")

    required_packages = [
        'sqlalchemy',
        'asyncpg',
        'instagrapi',
        'yt_dlp',
        'apscheduler',
        'dotenv',
        'pydantic_settings',
    ]

    all_installed = True
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            all_installed = False

    if not all_installed:
        print_info("\nInstall missing packages with:")
        print("  pip install sqlalchemy asyncpg instagrapi yt-dlp apscheduler python-dotenv pydantic-settings")

    return all_installed

def check_directories():
    """Check if required directories exist."""
    print_header("Checking directories")

    # Get audio_dir from .env
    from dotenv import load_dotenv
    load_dotenv()
    audio_dir = os.getenv('AUDIO_DIR', 'audio')

    if Path(audio_dir).exists():
        print_success(f"Directory '{audio_dir}' exists")
    else:
        print_warning(f"Directory '{audio_dir}' does not exist")
        print_info(f"Creating directory: {audio_dir}")
        try:
            Path(audio_dir).mkdir(parents=True, exist_ok=True)
            print_success(f"Created directory '{audio_dir}'")
        except Exception as e:
            print_error(f"Failed to create directory: {e}")
            return False

    return True

async def check_database():
    """Check database connection and tables."""
    print_header("Checking database connection")

    try:
        from src.database.session import get_session
        from src.repositories.account_repository import AccountRepository
        from sqlalchemy import text

        async with get_session() as session:
            # Test basic connection
            result = await session.execute(text("SELECT 1"))
            print_success("Database connection successful")

            # Check for required tables
            tables_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """
            result = await session.execute(text(tables_query))
            tables = [row[0] for row in result.fetchall()]

            required_tables = ['accounts', 'videos', 'metrics', 'metric_schedules']
            missing_tables = [t for t in required_tables if t not in tables]

            if missing_tables:
                print_warning(f"Missing tables: {', '.join(missing_tables)}")
                print_info("Run migrations to create tables:")
                print("  alembic upgrade head")
                return False

            print_success(f"All required tables exist: {', '.join(required_tables)}")

            # Check for accounts
            account_repo = AccountRepository(session)
            accounts = await account_repo.get_all()

            if not accounts:
                print_warning("No accounts found in database")
                print_info("Add accounts using admin interface or directly in database")
                return False

            print_success(f"Found {len(accounts)} account(s) in database")
            for account in accounts[:5]:  # Show first 5
                print(f"  - {account.username} (ID: {account.id})")

            if len(accounts) > 5:
                print(f"  ... and {len(accounts) - 5} more")

            return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        print_info("Check your DATABASE_URL in .env file")
        print_info("Make sure PostgreSQL is running")
        return False

def check_worker_imports():
    """Check if unified_worker can be imported."""
    print_header("Checking unified_worker imports")

    try:
        from unified_worker import UnifiedWorker
        print_success("unified_worker.py imports successfully")
        return True
    except ImportError as e:
        print_error(f"Failed to import unified_worker: {e}")
        return False
    except Exception as e:
        print_error(f"Error importing unified_worker: {e}")
        return False

def main():
    """Run all checks."""
    print_header("Environment Checker for unified_worker.py")

    checks = [
        ("Environment file", check_env_file),
        ("Python dependencies", check_dependencies),
        ("Directories", check_directories),
        ("Worker imports", check_worker_imports),
        ("Database", asyncio.run(check_database),
    ]

    results = []
    for name, result in checks:
        # For async checks, result is already the return value
        if asyncio.iscoroutine(result):
            pass  # Already handled above
        else:
            results.append((name, result))

    # Database check returns a coroutine
    # Re-run database check properly
    db_result = asyncio.run(check_database())
    results.append(("Database", db_result))

    # Summary
    print_header("Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: FAILED")

    print(f"\n{Colors.BOLD}Passed: {passed}/{total}{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed! You can run unified_worker.py{Colors.END}")
        print("Run: python unified_worker.py")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some checks failed. Please fix the issues above.{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
