# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# ✅ URL correta para asyncpg (async driver)
# Formato: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL_ASYNC = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
).replace(
    "postgresql+psycopg2://", "postgresql+asyncpg://"
)

logger.info(f"Connecting to database with asyncpg")

# Engine assíncrono com asyncpg
engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Alias para compatibilidade
async_session_maker = AsyncSessionLocal

Base = declarative_base()


async def get_db():
    """Dependency para obter sessão do banco"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Inicializa o banco de dados"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")