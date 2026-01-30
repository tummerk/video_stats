# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Instagram Reels Data Tracker - A Python application that scrapes Instagram Reels data, downloads audio, transcribes it using OpenAI Whisper, and tracks metrics (views, likes, comments) over time in PostgreSQL.

**Main Entry Point**: `run_workers.py` - Runs both workers (new video discovery and metrics collection) on a schedule.

## Common Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with:
# - DATABASE_URL (PostgreSQL connection)
# - INSTAGRAM_* cookies (get from browser DevTools - see QUICKSTART.md)

# Create database
createdb -U postgres reels

# Run migrations
alembic upgrade head

# Run setup wizard (interactive)
python setup_worker.py

# Test configuration
python test_worker.py
```

### Running Workers
```bash
# Run both workers continuously (RECOMMENDED)
python run_workers.py

# Run individual workers
python worker_new_video.py    # Fetches new reels every 6 hours
python worker_metrics.py      # Collects metrics every hour
```

### Account Management
```bash
# Add Instagram accounts to track
python add_account.py username1 username2

# View all accounts in database
python view_accounts.py
```

### Database Operations
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision -m "description"
alembic revision --autogenerate -m "description"

# Rollback migration
alembic downgrade -1

# Check migration status
alembic current
alembic history
```

### Testing
```bash
# Test database functionality
python test_database.py

# Test worker configuration
python test_worker.py
```

## Utility Scripts

Root directory contains several utility scripts:

- **`run_workers.py`** - Main entry point that runs both workers (new video + metrics) with APScheduler
- **`worker_new_video.py`** - Standalone new video discovery worker (can be run independently)
- **`worker_metrics.py`** - Standalone metrics collection worker (can be run independently)
- **`add_account.py`** - Add Instagram accounts to track (accepts multiple usernames as arguments)
- **`view_accounts.py`** - List all accounts in the database
- **`setup_worker.py`** - Interactive setup wizard for initial configuration
- **`test_worker.py`** - Test worker configuration and connectivity
- **`test_database.py`** - Test database operations
- **`audio.py`** - Legacy audio download script (likely deprecated)
- **`metric.py`** - Legacy metrics script (likely deprecated)

## Architecture

### Worker System

The application uses a dual-worker architecture with APScheduler:

**`run_workers.py`** - Main entry point that orchestrates both workers:
- **New Video Worker** (`worker_new_video.py`): Fetches latest reels every 6 hours (configurable)
  - Downloads audio using yt-dlp
  - Transcribes using OpenAI Whisper
  - Stops processing when encountering existing videos (smart processing)
- **Metrics Worker** (`worker_metrics.py`): Collects performance metrics every hour
  - Updates view counts, likes, comments for existing videos
  - Manages collection schedules via `metric_schedules` table

### Clean Architecture Pattern

The application follows a layered architecture with clear separation of concerns:

```
src/
├── config.py              # Pydantic settings from environment
├── database/              # Database infrastructure layer
│   ├── base.py           # SQLAlchemy DeclarativeBase
│   ├── connection.py     # Async engine and session factory
│   ├── session.py        # AsyncSession context manager
│   └── utils.py          # Database utilities
├── models/               # Domain models (SQLAlchemy 2.0 with Mapped[])
│   ├── base.py           # BaseModel with id, created_at, updated_at
│   ├── account.py        # Instagram accounts
│   ├── video.py          # Reels/videos with transcriptions
│   ├── metrics.py        # Performance metrics over time
│   └── metric_schedule.py # Metrics scheduling
├── repositories/         # Data access layer (Repository pattern)
│   ├── base.py           # Generic BaseRepository with CRUD
│   ├── account_repository.py
│   ├── video_repository.py
│   ├── metrics_repository.py
│   └── metric_schedule_repository.py
└── services/             # Business logic layer
    └── instagram_service.py
```

### Key Patterns

**SQLAlchemy 2.0 Async**: All database operations use async/await patterns with `AsyncSession` and `asyncpg` driver.

**Repository Pattern**: Each entity has a dedicated repository inheriting from `BaseRepository[ModelType]` providing generic CRUD operations.

**Session Management**: Use `async with get_session() as session:` context manager for database operations.

**Model Relationships**:
- `Account (1) ──< (N) Video (1) ──< (N) Metrics`
- `Video (1) ──< (N) MetricSchedule` - For scheduled metrics collection
- All models extend `BaseModel` with auto-timestamps
- Use `Mapped[column_type]` annotations for typed columns

### Database Schema

**accounts**: Instagram profiles (username, profile_url, followers_count)
**videos**: Reels with transcription (video_id, shortcode, caption, audio_url, transcription, audio_file_path)
**metrics**: Performance tracking (view_count, like_count, comment_count, measured_at)
**metric_schedules**: Scheduling for metrics collection (schedule_type, scheduled_at, status)

Indexes on `shortcode`, `video_id` (unique), `(account_id, published_at)`, and `(video_id, measured_at)` for queries.

## Configuration

### Environment Variables (`.env`)
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/reels

# Worker Configuration
WORKER_INTERVAL_HOURS=6     # New video worker interval
WORKER_REELS_LIMIT=50       # Max reels to fetch per account
AUDIO_DIR=audio             # Directory for audio files

# Instagram Cookies (required for scraping)
INSTAGRAM_SESSIONID=your_sessionid_here
INSTAGRAM_DS_USER_ID=your_ds_user_id_here
INSTAGRAM_CSRFTOKEN=your_csrftoken_here
INSTAGRAM_MID=your_mid_here
```

### Getting Instagram Cookies

1. Open Instagram in browser
2. Press F12 (DevTools)
3. Application > Cookies > instagram.com
4. Copy: sessionid, ds_user_id, csrftoken, mid

## External Dependencies

- **Instaloader**: Instagram data scraping
- **yt-dlp**: Audio downloading from Instagram URLs
- **OpenAI Whisper**: Audio transcription
- **APScheduler**: Job scheduling for workers
- **PostgreSQL + asyncpg**: Async database operations
- **Alembic**: Database migrations
- **Pydantic**: Configuration management

## Development Notes

- Workers use service classes for business logic separation (see `worker_*.py` files)
- Workers automatically create accounts that don't exist in the database
- Smart processing: New video worker stops when encountering existing videos
- All database operations must be async
- Use `select().where()` syntax, not legacy query API
- Models use `Mapped` type annotations from SQLAlchemy 2.0
- FFmpeg required for audio transcription (Whisper dependency)
- Two separate `InstagramService` classes: one in `worker_new_video.py`, another in `src/services/instagram_service.py` (metrics worker uses the shared service)
- Whisper model is a singleton in `TranscriptionService` to avoid reloading between transcriptions
- Use `asyncio.run_in_executor()` for blocking I/O operations (instaloader, yt-dlp, whisper)
- Tenacity library provides retry logic with exponential backoff for network operations

## Code Patterns

### Repository Usage
```python
async with get_session() as session:
    repo = VideoRepository(session)
    video = await repo.get_by_shortcode(shortcode)
    # or create: await repo.create(**kwargs)
```

### Service Layer Pattern
Workers are structured with service classes:
- `InstagramService`: Handles all Instagram API interactions
- `AudioDownloadService`: Downloads audio using yt-dlp
- `TranscriptionService`: Transcribes audio using Whisper (singleton model)
- `MetricsCollectionService`: Fetches and saves metrics
- `MetricsScheduler`: Manages metric collection schedules

### Async/Sync Bridge
Use `loop.run_in_executor()` for blocking calls:
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, blocking_function, args)
```

## Documentation

- **QUICKSTART.md** - Quick reference for daily operations
- **WORKER_README.md** - Comprehensive worker documentation
- **DATABASE_SETUP.md** - Database setup and migration guide
- **IMPLEMENTATION_SUMMARY.md** - Implementation details
