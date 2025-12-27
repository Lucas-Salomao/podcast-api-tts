"""
Database connection and session management.
Uses SQLAlchemy with asyncpg for async PostgreSQL operations.
"""

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Build database URL from environment variables
def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "podcast")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    sslmode = os.getenv("DB_SSLMODE", "prefer")
    
    # asyncpg uses postgresql+asyncpg:// scheme
    url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
    
    # Add SSL mode if required
    if sslmode == "require":
        url += "?ssl=require"
    
    return url


# Create async engine
DATABASE_URL = get_database_url()
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    # Supabase uses pgbouncer which doesn't support prepared statements
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Get a database session for dependency injection."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables if they don't exist."""
    # Import models to register them with Base.metadata
    from app.db import models  # noqa: F401
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] Database tables created/verified")


async def close_database():
    """Close database connections."""
    await engine.dispose()
    logger.info("[DB] Database connections closed")
