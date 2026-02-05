"""
FastAPI dependencies for the admin panel.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from src.database.session import get_session


async def get_db() -> AsyncSession:
    """Get database session for FastAPI dependencies."""
    async with get_session() as session:
        yield session
