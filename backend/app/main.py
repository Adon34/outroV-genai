# backend/app/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.routers import auth, users, chat, meals, workouts
from app.services.rag_service import RAGService

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton para RAG Service
rag_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global rag_service
    logger.info("Inicializando banco de dados...")
    await init_db()
    
    logger.info("Inicializando RAG Service...")
    rag_service = RAGService()
    await rag_service.initialize()
    
    yield
    
    # Shutdown
    logger.info("Finalizando aplicação...")
    if rag_service:
        await rag_service.close()

app = FastAPI(title="Diet & Training Chatbot", version="1.0.0", lifespan=lifespan)

# CORS
origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["http://localhost", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(meals.router, prefix="/meals", tags=["meals"])
app.include_router(workouts.router, prefix="/workouts", tags=["workouts"])

@app.get("/")
async def root():
    return {"message": "Diet & Training Chatbot API"}

from app.database import AsyncSessionLocal
import httpx
import redis.asyncio as redis
import asyncio

async def check_database() -> bool:
    """Check database connectivity"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return True
    except Exception:
        return False

async def check_redis() -> bool:
    """Check Redis connectivity"""
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        await r.ping()
        return True
    except Exception:
        return False

async def check_chroma() -> bool:
    """Check ChromaDB connectivity"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.CHROMA_URL}/api/v1/heartbeat")
            return response.status_code == 200
    except Exception:
        return False

@app.get("/health")
async def health_check():
    """Detailed health check"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "chroma": await check_chroma(),
        "rag_service": rag_service is not None
    }

    all_healthy = all(checks.values())
    status = "healthy" if all_healthy else "degraded"

    return {
        "status": status,
        "timestamp": asyncio.get_event_loop().time(),
        **checks
    }