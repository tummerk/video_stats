# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Instagram Reels Data Tracker - A Python application that scrapes Instagram Reels data, downloads audio, transcribes it using OpenAI Whisper, and tracks metrics (views, likes, comments) over time in PostgreSQL.

## Common Commands

### Database Operations
```bash
# Create database
createdb -U postgres reels

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

### Application Entry Points
```bash
# Audio processing - downloads audio from Instagram Reel and transcribes using Whisper
python audio.py

# Metrics collection - scrapes Instagram metrics using Instaloader
python metric.py

# Test database functionality
python test_database.py

# Test Instagram API with cookies
python test.py
```

### Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with PostgreSQL credentials:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/reels
```

## Architecture

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
│   └── metrics.py        # Performance metrics over time
└── repositories/         # Data access layer (Repository pattern)
    ├── base.py           # Generic BaseRepository with CRUD
    ├── account_repository.py
    ├── video_repository.py
    └── metrics_repository.py
```

### Key Patterns

**SQLAlchemy 2.0 Async**: All database operations use async/await patterns with `AsyncSession` and `asyncpg` driver.

**Repository Pattern**: Each entity has a dedicated repository inheriting from `BaseRepository[ModelType]` providing generic CRUD operations.

**Session Management**: Use `async with get_session() as session:` context manager for database operations.

**Model Relationships**:
- `Account (1) ──< (N) Video (1) ──< (N) Metrics`
- All models extend `BaseModel` with auto-timestamps
- Use `Mapped[column_type]` annotations for typed columns

### Database Schema

**accounts**: Instagram profiles (username, profile_url, followers_count)
**videos**: Reels with transcription (video_id, shortcode, caption, audio_url, transcription)
**metrics**: Performance tracking (view_count, like_count, comment_count, measured_at)

Indexes on `shortcode`, `video_id` (unique), and `(account_id, published_at)` for queries.

## External Dependencies

- **Instaloader**: Instagram data scraping (configured with `TARGET_USERNAME`, `MY_USERNAME`)
- **yt-dlp**: Audio downloading from Instagram URLs
- **OpenAI Whisper**: Audio transcription
- **PostgreSQL + asyncpg**: Async database operations
- **Alembic**: Database migrations

## Development Notes

- Scripts `audio.py` and `metric.py` are standalone entry points, not integrated with the repository layer yet
- Database configuration loaded from `.env` via `src/config.py`
- All database operations must be async
- Use `select().where()` syntax, not legacy query API
- Models use `Mapped` type annotations from SQLAlchemy 2.0
