"""Simple script to apply alembic migrations."""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine


async def apply_migrations():
    """Apply all pending alembic migrations."""
    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"Connecting to: {database_url.split('@')[1] if '@' in database_url else database_url}")

    # Change to app directory
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(app_dir)

    # Create alembic config
    alembic_cfg = Config(os.path.join(app_dir, 'alembic.ini'))

    # Set sqlalchemy.url
    alembic_cfg.set_main_option('sqlalchemy.url', database_url)

    try:
        # Run migrations
        command.upgrade(alembic_cfg, 'head')
        print("\n✅ Migrations applied successfully!")
    except Exception as e:
        print(f"\n❌ Error applying migrations: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(apply_migrations())
