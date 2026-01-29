# PostgreSQL Database Setup Guide

## Overview

This project uses PostgreSQL with SQLAlchemy 2.0 async patterns and Alembic for database migrations.

## Prerequisites

1. **PostgreSQL Database**: Ensure PostgreSQL is installed and running
2. **Python Dependencies**: Already installed in your environment
   - sqlalchemy==2.0.46
   - asyncpg==0.31.0
   - alembic==1.18.2
   - python-dotenv==1.2.1

## Setup Instructions

### 1. Create `.env` File

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### 2. Configure Database URL

Edit the `.env` file with your PostgreSQL credentials:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/instagram_tracker
```

Replace:
- `username`: Your PostgreSQL username
- `password`: Your PostgreSQL password
- `localhost`: Your database host (change if needed)
- `5432`: Your PostgreSQL port (change if needed)
- `instagram_tracker`: Your database name

### 3. Create Database

Create the database in PostgreSQL:

```bash
# Using psql
psql -U postgres
CREATE DATABASE instagram_tracker;
\q

# Or using createdb
createdb -U postgres instagram_tracker
```

### 4. Run Migrations

Apply all database migrations:

```bash
alembic upgrade head
```

### 5. Verify Setup

Run the test script to verify everything works:

```bash
python test_database.py
```

## Database Schema

### Tables

#### `accounts`
- `id` - Primary key (auto-increment)
- `username` - Unique Instagram username
- `profile_url` - Profile link (nullable)
- `followers_count` - Current follower count
- `created_at`, `updated_at` - Timestamps

#### `videos`
- `id` - Primary key (auto-increment)
- `video_id` - Instagram video ID (unique)
- `shortcode` - Instagram shortcode (unique)
- `video_url` - Download link (nullable)
- `published_at` - Publication datetime
- `caption` - Video description (nullable)
- `duration_seconds` - Video duration (nullable)
- `audio_url` - Audio source URL (nullable)
- `audio_file_path` - Local audio file path (nullable)
- `transcription` - Text transcription (nullable)
- `account_id` - Foreign key to accounts
- `created_at`, `updated_at` - Timestamps

**Indexes:**
- `shortcode` (unique)
- `video_id` (unique)
- `(account_id, published_at)` - For querying account's videos

#### `metrics`
- `id` - Primary key (auto-increment)
- `video_id` - Foreign key to videos
- `view_count` - View count (BigInteger)
- `like_count` - Like count
- `comment_count` - Comment count
- `save_count` - Save count (nullable)
- `followers_count` - Followers at collection time
- `measured_at` - Measurement timestamp
- `created_at` - Timestamp

**Indexes:**
- `(video_id, measured_at)` - For metrics history queries

## Relationships

```
Account (1) ──< (N) Video (1) ──< (N) Metrics
```

## Migration Commands

### Create a New Migration

```bash
alembic revision -m "description of changes"
```

### Auto-Generate Migration from Models

```bash
alembic revision --autogenerate -m "description"
```

### Apply Migrations

```bash
# Apply all migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>
```

### Rollback Migrations

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all
alembic downgrade base
```

### View Migration History

```bash
alembic history
```

### View Current Version

```bash
alembic current
```

## Testing

### Run Database Tests

```bash
python test_database.py
```

This will:
1. Create a test account
2. Create a test video
3. Create test metrics
4. Test all relationships
5. Verify repository methods

### Verify Database Schema

```sql
-- Check tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Check indexes
SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';

-- Check foreign keys
SELECT
    constraint_name,
    table_name,
    column_name,
    foreign_table_name
FROM information_schema.key_column_usage
WHERE table_schema = 'public';
```

## Project Structure

```
src/
├── config.py                 # Configuration management
├── database/
│   ├── __init__.py          # Database exports
│   ├── base.py              # SQLAlchemy base
│   ├── connection.py        # Engine and session factory
│   ├── session.py           # Session context manager
│   └── utils.py             # Database utilities
├── models/
│   ├── __init__.py          # Model exports
│   ├── base.py              # Base model with common fields
│   ├── account.py           # Account model
│   ├── video.py             # Video model
│   └── metrics.py           # Metrics model
└── repositories/
    ├── __init__.py          # Repository exports
    ├── base.py              # Base repository
    ├── account_repository.py # Account repository
    ├── video_repository.py   # Video repository
    └── metrics_repository.py # Metrics repository

alembic/
├── versions/                # Migration files
│   └── 001_initial.py       # Initial migration
├── env.py                   # Alembic environment
└── script.py.mako           # Migration template
```

## Usage Example

```python
import asyncio
from datetime import datetime
from src.database import get_session
from src.repositories import AccountRepository, VideoRepository, MetricsRepository


async def main():
    async with get_session() as session:
        # Create account
        account_repo = AccountRepository(session)
        account = await account_repo.create_or_update_by_username(
            username="instagram_user",
            profile_url="https://instagram.com/instagram_user",
            followers_count=5000
        )

        # Create video
        video_repo = VideoRepository(session)
        video = await video_repo.create_or_update_by_shortcode(
            shortcode="ABC123",
            video_id="123456789",
            account_id=account.id,
            caption="Amazing reel!",
            published_at=datetime.utcnow()
        )

        # Create metrics
        metrics_repo = MetricsRepository(session)
        metrics = await metrics_repo.create_metrics_snapshot(
            video_id=video.id,
            view_count=10000,
            like_count=500,
            comment_count=50,
            followers_count=5000
        )

        # Get video with metrics
        video_data = await video_repo.get_by_shortcode_with_metrics("ABC123")
        print(f"Video: {video_data.caption}")
        print(f"Views: {video_data.metrics[0].view_count}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Connection Issues

If you get connection errors:

1. Verify PostgreSQL is running:
   ```bash
   pg_ctl status
   ```

2. Check your `.env` file has correct credentials

3. Ensure database exists:
   ```bash
   psql -U postgres -l
   ```

### Migration Issues

If migrations fail:

1. Check current migration status:
   ```bash
   alembic current
   ```

2. View migration history:
   ```bash
   alembic history
   ```

3. If stuck, reset to base:
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

### Import Errors

If you get import errors:

1. Ensure you're running from the project root
2. Check that all dependencies are installed:
   ```bash
   pip list
   ```

## Next Steps

1. Set up your PostgreSQL database
2. Configure the `.env` file
3. Run migrations: `alembic upgrade head`
4. Test with: `python test_database.py`
5. Start building your application!
