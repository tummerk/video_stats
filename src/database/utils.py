from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import engine
from src.database.base import Base


async def init_database() -> None:
    """Initialize database database.

    This function creates all tables. Note: It's recommended to use
    Alembic migrations instead in production.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def test_connection() -> bool:
    """Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def close_database() -> None:
    """Close database connections."""
    await engine.dispose()
