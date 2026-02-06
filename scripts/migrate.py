"""Apply migrations - simple version."""
import sys
import os

sys.path.insert(0, '/app/src')

from alembic.config import Config
from alembic import command


def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    print(f"Applying migrations to: {database_url.split('@')[1]}")

    alembic_cfg = Config()
    alembic_cfg.set_main_option('script_location', '/app/alembic')
    alembic_cfg.set_main_option('sqlalchemy.url', database_url)

    try:
        command.upgrade(alembic_cfg, 'head')
        print("\n✅ Migrations applied!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
