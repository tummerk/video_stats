from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import settings

# Create async engine with proper pooling
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,          # Maximum connections in pool
    max_overflow=10,      # Additional connections when needed
    pool_recycle=3600,    # Recycle connections after 1 hour
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
