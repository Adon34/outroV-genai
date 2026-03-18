# backend/app/main.py
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.routers import auth, users, chat, meals, workouts
from app.health.router import router as health_router
from app.services.rag_service import RAGService

# Prometheus metrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

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
app.include_router(health_router, tags=["health"])

@app.get("/")
async def root():
    return {"message": "Diet & Training Chatbot API"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)