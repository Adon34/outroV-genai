import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.services.rag_service import RAGService
from .models import ComponentHealth

async def check_database() -> ComponentHealth:
    """Check PostgreSQL database health"""
    start_time = time.time()
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            break
        response_time = (time.time() - start_time) * 1000

        # Get additional metrics
        async for session in get_db():
            result = await session.execute(text("""
                SELECT
                    count(*) as active_connections,
                    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
                FROM pg_stat_activity
                WHERE state = 'active'
            """))
            row = result.first()
            break

        return ComponentHealth(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "active_connections": row.active_connections,
                "max_connections": row.max_connections,
                "connection_utilization_percent": round((row.active_connections / row.max_connections) * 100, 1)
            },
            last_checked=datetime.now()
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            error_message=str(e),
            last_checked=datetime.now()
        )

async def check_redis() -> ComponentHealth:
    """Check Redis cache health"""
    start_time = time.time()
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        await r.ping()
        response_time = (time.time() - start_time) * 1000

        # Get Redis info
        info = await r.info()
        memory_used = info.get('used_memory', 0)
        max_memory = info.get('maxmemory', 0) or (1024**3)  # 1GB default

        return ComponentHealth(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "memory_used_mb": round(memory_used / (1024**2), 1),
                "memory_used_percent": round((memory_used / max_memory) * 100, 1) if max_memory > 0 else 0,
                "connected_clients": info.get('connected_clients', 0),
                "uptime_seconds": info.get('uptime_in_seconds', 0)
            },
            last_checked=datetime.now()
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            error_message=str(e),
            last_checked=datetime.now()
        )

async def check_chroma() -> ComponentHealth:
    """Check ChromaDB vector database health"""
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.CHROMA_URL}/api/v2/heartbeat")
            response.raise_for_status()
            response_time = (time.time() - start_time) * 1000

            # Try to get collection info
            collections_response = await client.get(f"{settings.CHROMA_URL}/api/v2/collections")
            collections = collections_response.json() if collections_response.status_code == 200 else []

            return ComponentHealth(
                status="healthy",
                response_time_ms=round(response_time, 2),
                details={
                    "collections_count": len(collections),
                    "collections": [c.get('name') for c in collections[:5]]  # First 5 names
                },
                last_checked=datetime.now()
            )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            error_message=str(e),
            last_checked=datetime.now()
        )

async def check_rag_service() -> ComponentHealth:
    """Check RAG service initialization and basic functionality"""
    start_time = time.time()
    try:
        # Try to access the global rag_service from main module
        import sys
        main_module = sys.modules.get('app.main')
        if main_module and hasattr(main_module, 'rag_service'):
            rag_service = main_module.rag_service
        else:
            rag_service = None

        if rag_service is None:
            raise Exception("RAG service not initialized")

        # Basic functionality check - try to get collections
        collections = rag_service.vectorstore._client.list_collections()
        response_time = (time.time() - start_time) * 1000

        return ComponentHealth(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "collections_count": len(collections),
                "initialized": True
            },
            last_checked=datetime.now()
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            error_message=str(e),
            last_checked=datetime.now()
        )

async def check_openai() -> ComponentHealth:
    """Check OpenAI API availability (lightweight check)"""
    start_time = time.time()
    try:
        # Use a simple models list call to check API
        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        models = await client.models.list()
        response_time = (time.time() - start_time) * 1000

        return ComponentHealth(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "models_available": len(models.data),
                "api_accessible": True
            },
            last_checked=datetime.now()
        )
    except Exception as e:
        return ComponentHealth(
            status="degraded" if "rate limit" in str(e).lower() else "unhealthy",
            error_message=str(e),
            last_checked=datetime.now()
        )

async def perform_health_checks() -> Dict[str, ComponentHealth]:
    """Run all health checks concurrently"""
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "chroma": check_chroma(),
        "rag_service": check_rag_service(),
        "openai": check_openai()
    }

    results = await asyncio.gather(*checks.values(), return_exceptions=True)

    health_results = {}
    for name, result in zip(checks.keys(), results):
        if isinstance(result, Exception):
            health_results[name] = ComponentHealth(
                status="unhealthy",
                error_message=str(result),
                last_checked=datetime.now()
            )
        else:
            health_results[name] = result

    return health_results