from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Convert postgresql:// to postgresql+asyncpg://
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

async def init_db():
    """Initialize database by creating all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")

async def get_db(local_kw: str = None):
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()