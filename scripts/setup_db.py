"""Quick database setup - create all tables."""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://user:passd@postgres:5432/reels"


async def setup():
    engine = create_async_engine(DB_URL, echo=True)

    async with engine.begin() as conn:
        # Accounts
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                username VARCHAR(150) UNIQUE NOT NULL,
                profile_url VARCHAR(512),
                followers_count INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Videos
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                video_id VARCHAR(100) UNIQUE NOT NULL,
                shortcode VARCHAR(50) UNIQUE NOT NULL,
                video_url VARCHAR(1024),
                published_at TIMESTAMP WITH TIME ZONE NOT NULL,
                caption TEXT,
                duration_seconds INTEGER,
                audio_url VARCHAR(1024),
                audio_file_path VARCHAR(1024),
                transcription TEXT,
                account_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """))

        # Metrics
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS metrics (
                id SERIAL PRIMARY KEY,
                video_id INTEGER NOT NULL,
                view_count BIGINT NOT NULL,
                like_count INTEGER NOT NULL,
                comment_count INTEGER NOT NULL,
                save_count INTEGER,
                followers_count INTEGER NOT NULL,
                measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """))

        # Metric schedules
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS metric_schedules (
                id SERIAL PRIMARY KEY,
                video_id INTEGER NOT NULL,
                schedule_type VARCHAR(20) NOT NULL,
                scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                completed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos(id)
            )
        """))

        # Worker heartbeats
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                id SERIAL PRIMARY KEY,
                worker_name VARCHAR(255) UNIQUE NOT NULL,
                last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL,
                status VARCHAR(50) DEFAULT 'running',
                pid INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

    print("\n✅ All tables created!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup())
