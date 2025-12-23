"""
Database Session Configuration

SCALE-002: Connection pool tuning for production workloads.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from typing import AsyncGenerator

# Create engine with connection pool tuning
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # Connection pool settings
    pool_size=20,          # Base number of connections to keep open
    max_overflow=10,       # Extra connections allowed under high load
    pool_timeout=30,       # Seconds to wait for a connection before error
    pool_pre_ping=True,    # Check connection health before each use
    pool_recycle=1800,     # Recycle connections after 30 mins (prevents stale)
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        yield session

