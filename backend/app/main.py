# backend/app/main.py
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.health.router import router as health_router
from app.services.rag_service import RAGService
from app.agents.orchestrator import ModernOrchestrator
from app.routers import auth, users, chat, meals, workouts

# Prometheus metrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton para serviços globais
rag_service = None
orchestrator = None
chat_openai = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    global rag_service, orchestrator, chat_openai
    
    # ============================================
    # STARTUP
    # ============================================
    logger.info("🚀 Inicializando aplicação...")
    
    # 1. Inicializa banco de dados
    logger.info("📦 Inicializando banco de dados...")
    await init_db()
    
    # 2. Inicializa RAG Service
    logger.info("🧠 Inicializando RAG Service...")
    rag_service = RAGService()
    await rag_service.initialize()
    
    # 3. Inicializa LLM (ChatOpenAI)
    logger.info("🤖 Configurando modelo de linguagem...")
    from langchain_openai import ChatOpenAI
    chat_openai = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        streaming=True,
        timeout=30,
        max_retries=2,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    # 4. Inicializa Orquestrador Moderno
    logger.info("🎯 Inicializando Orquestrador de Agents...")
    orchestrator = ModernOrchestrator(
        llm=chat_openai,
        db_session_factory=AsyncSessionLocal,
        rag_service=rag_service
    )
    
    # 5. Log de serviços inicializados
    logger.info("✅ Aplicação inicializada com sucesso!")
    logger.info(f"   - RAG Service: {rag_service.__class__.__name__}")
    logger.info(f"   - Orchestrator: {orchestrator.__class__.__name__}")
    logger.info(f"   - LLM Model: {settings.OPENAI_MODEL}")
    
    yield
    
    # ============================================
    # SHUTDOWN
    # ============================================
    logger.info("🛑 Finalizando aplicação...")
    
    if rag_service:
        await rag_service.close()
        logger.info("   - RAG Service finalizado")
    
    if orchestrator:
        logger.info("   - Orchestrator finalizado")
    
    logger.info("👋 Aplicação finalizada com sucesso!")


# ============================================
# FASTAPI APP CONFIGURATION
# ============================================

app = FastAPI(
    title="Diet & Training AI Platform",
    description="""
    ## API Inteligente para Nutrição e Treinos Personalizados
    
    ### Funcionalidades:
    - **Chat Inteligente**: Conversas contextuais com IA
    - **Planos de Treino**: Sugestões personalizadas baseadas no perfil
    - **Dietas**: Recomendações nutricionais adaptadas
    - **Perfil do Usuário**: Gestão completa de dados de saúde
    
    ### Tecnologias:
    - LangChain + LangGraph para agents
    - RAG com ChromaDB
    - Streaming para respostas em tempo real
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================
# ROTAS PRINCIPAIS
# ============================================

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(meals.router, prefix="/meals", tags=["meals"])
app.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
app.include_router(health_router, prefix="/health", tags=["health"])

# ============================================
# MODELOS PYDANTIC
# ============================================

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.responses import StreamingResponse
import json


class ChatRequest(BaseModel):
    """Request model para chat"""
    message: str
    user_id: int
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Response model para chat"""
    action: str
    message: str
    sources: List[Dict] = []
    confidence: float = 0.0
    user_id: int


# ============================================
# ENDPOINTS PRINCIPAIS
# ============================================

@app.get("/")
async def root():
    return {
        "message": "Diet & Training AI Platform v2.0",
        "version": "2.0.0",
        "status": "online",
        "features": {
            "rag": True,
            "agents": True,
            "streaming": True,
            "structured_output": True
        },
        "endpoints": {
            "chat": "/chat/send",
            "chat_stream": "/chat/stream",
            "status": "/api/v1/status",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.post("/chat/send", response_model=ChatResponse)
async def chat_send(request: ChatRequest):
    """
    Envia mensagem para o agente inteligente.
    """
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        result = await orchestrator.process_message(
            message=request.message,
            user_id=request.user_id,
            chat_history=request.history,
            thread_id=request.conversation_id
        )
        
        return ChatResponse(
            action=result.get("action", "chat"),
            message=result.get("message", ""),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            user_id=request.user_id
        )
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Envia mensagem com streaming de resposta.
    """
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    async def event_generator():
        try:
            async for event in orchestrator.process_message_streaming(
                message=request.message,
                user_id=request.user_id,
                chat_history=request.history,
                thread_id=request.conversation_id
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
                
            yield f"data: {json.dumps({'type': 'end', 'complete': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Erro no streaming: {e}")
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/chat/conversation/{thread_id}")
async def get_conversation_state(thread_id: str):
    """Recupera o estado de uma conversa anterior."""
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    state = await orchestrator.get_conversation_state(thread_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "thread_id": thread_id,
        "state": state,
        "has_checkpoint": True
    }


@app.delete("/chat/conversation/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reseta uma conversa."""
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    success = await orchestrator.reset_conversation(thread_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset conversation")
    
    return {
        "thread_id": thread_id,
        "reset": True,
        "message": "Conversation reset successfully"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health/live")
async def health_live():
    """Liveness probe para Docker/Kubernetes"""
    return {"status": "alive"}

@app.get("/health/ready")
async def health_ready():
    """Readiness probe para Docker/Kubernetes"""
    global orchestrator, rag_service
    
    if orchestrator and rag_service:
        return {"status": "ready"}
    else:
        return {"status": "not ready"}, 503


@app.get("/health/detailed")
async def detailed_health():
    """Health check detalhado."""
    global orchestrator, rag_service
    
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "components": {
            "orchestrator": {
                "status": "healthy" if orchestrator else "unavailable",
                "type": "LangGraph"
            },
            "rag_service": {
                "status": "healthy" if rag_service else "unavailable",
                "type": "ChromaDB"
            },
            "api": {
                "status": "healthy",
                "endpoints": "/chat/send, /chat/stream"
            }
        },
        "features": {
            "streaming": True,
            "structured_output": True,
            "checkpointing": True
        }
    }
    
    if not orchestrator or not rag_service:
        health_status["status"] = "degraded"
        health_status["error"] = "Critical components unavailable"
    
    return health_status





# backend/app/main.py

'''

from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.routers import auth, users, chat, meals, workouts
from app.health.router import router as health_router
from app.services.rag_service import RAGService
from app.agents.orchestrator import ModernOrchestrator
from app.agents import ModernProfileAgent, ModernWorkoutAgent, ModernDietAgent

# Prometheus metrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton para serviços globais
rag_service = None
orchestrator = None
chat_openai = None  # Será inicializado após config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    global rag_service, orchestrator, chat_openai
    
    # ============================================
    # STARTUP
    # ============================================
    logger.info("🚀 Inicializando aplicação...")
    
    # 1. Inicializa banco de dados
    logger.info("📦 Inicializando banco de dados...")
    await init_db()
    
    # 2. Inicializa RAG Service (versão refatorada)
    logger.info("🧠 Inicializando RAG Service...")
    rag_service = RAGService()
    await rag_service.initialize()
    
    # 3. Inicializa LLM (ChatOpenAI)
    logger.info("🤖 Configurando modelo de linguagem...")
    from langchain_openai import ChatOpenAI
    chat_openai = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.7,
        streaming=True,  # ✅ Habilitado para melhor UX
        timeout=30,
        max_retries=2,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    # 4. Inicializa Orquestrador Moderno
    logger.info("🎯 Inicializando Orquestrador de Agents...")
    from app.database import async_session_maker
    orchestrator = ModernOrchestrator(
        llm=chat_openai,
        db_session_factory=async_session_maker,
        rag_service=rag_service
    )
    
    # 5. Log de serviços inicializados
    logger.info("✅ Aplicação inicializada com sucesso!")
    logger.info(f"   - RAG Service: {rag_service.__class__.__name__}")
    logger.info(f"   - Orchestrator: {orchestrator.__class__.__name__}")
    logger.info(f"   - LLM Model: {settings.OPENAI_MODEL}")
    
    yield
    
    # ============================================
    # SHUTDOWN
    # ============================================
    logger.info("🛑 Finalizando aplicação...")
    
    if rag_service:
        await rag_service.close()
        logger.info("   - RAG Service finalizado")
    
    if orchestrator:
        logger.info("   - Orchestrator finalizado")
    
    logger.info("👋 Aplicação finalizada com sucesso!")


# ============================================
# FASTAPI APP CONFIGURATION
# ============================================

app = FastAPI(
    title="Diet & Training AI Platform",
    description="""
    ## API Inteligente para Nutrição e Treinos Personalizados
    
    ### Funcionalidades:
    - **Chat Inteligente**: Conversas contextuais com IA
    - **Planos de Treino**: Sugestões personalizadas baseadas no perfil
    - **Dietas**: Recomendações nutricionais adaptadas
    - **Perfil do Usuário**: Gestão completa de dados de saúde
    
    ### Tecnologias:
    - LangChain + LangGraph para agents
    - RAG com ChromaDB
    - Streaming para respostas em tempo real
    """,
    version="2.0.0",  # Versão atualizada com agents modernos
    lifespan=lifespan
)

# CORS Configuration
origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================
# ROTAS PRINCIPAIS
# ============================================

# Rotas existentes (preservadas)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(meals.router, prefix="/meals", tags=["meals"])
app.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
app.include_router(health_router, prefix="/health", tags=["health"])


# ============================================
# NOVAS ROTAS PARA AGENTS MODERNOS
# ============================================

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.responses import StreamingResponse
import json
import asyncio


class ChatRequest(BaseModel):
    """Request model para chat"""
    message: str
    user_id: int
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Response model para chat"""
    action: str
    message: str
    sources: List[Dict] = []
    confidence: float = 0.0
    user_id: int


@app.get("/")
async def root():
    return {
        "message": "Diet & Training AI Platform v2.0",
        "version": "2.0.0",
        "status": "online",
        "features": {
            "rag": True,
            "agents": True,
            "streaming": True,
            "structured_output": True
        },
        "endpoints": {
            "chat": "/chat/send",
            "chat_stream": "/chat/stream",
            "health": "/health",
            "metrics": "/metrics"
        }
    }


@app.post("/chat/send", response_model=ChatResponse)
async def chat_send(request: ChatRequest):
    """
    Envia mensagem para o agente inteligente.
    
    Utiliza o orquestrador moderno com LangGraph para:
    - Classificação automática de intenção
    - Roteamento para agentes especializados
    - Contexto personalizado via RAG
    """
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        # Processa mensagem com o orquestrador moderno
        result = await orchestrator.process_message(
            message=request.message,
            user_id=request.user_id,
            chat_history=request.history,
            thread_id=request.conversation_id
        )
        
        return ChatResponse(
            action=result.get("action", "chat"),
            message=result.get("message", ""),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            user_id=request.user_id
        )
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Envia mensagem com streaming de resposta (UX premium).
    
    Retorna Server-Sent Events (SSE) com tokens parciais da resposta.
    """
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    async def event_generator():
        """Gera eventos SSE com streaming"""
        try:
            # Processa com streaming
            async for event in orchestrator.process_message_streaming(
                message=request.message,
                user_id=request.user_id,
                chat_history=request.history,
                thread_id=request.conversation_id
            ):
                # Formata como SSE
                yield f"data: {json.dumps(event, default=str)}\n\n"
                
            # Evento final
            yield f"data: {json.dumps({'type': 'end', 'complete': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Erro no streaming: {e}")
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Desabilita buffering no nginx
        }
    )


@app.get("/chat/conversation/{thread_id}")
async def get_conversation_state(thread_id: str):
    """
    Recupera o estado de uma conversa anterior.
    Útil para retomar conversas interrompidas.
    """
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    state = await orchestrator.get_conversation_state(thread_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "thread_id": thread_id,
        "state": state,
        "has_checkpoint": True
    }


@app.delete("/chat/conversation/{thread_id}")
async def reset_conversation(thread_id: str):
    """Reseta uma conversa (limpa checkpoint)"""
    global orchestrator
    
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    success = await orchestrator.reset_conversation(thread_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset conversation")
    
    return {
        "thread_id": thread_id,
        "reset": True,
        "message": "Conversation reset successfully"
    }


# ============================================
# ROTA DE MÉTRICAS (PROMETHEUS)
# ============================================

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint para monitoramento"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============================================
# HEALTH CHECK DETALHADO
# ============================================

@app.get("/health/detailed")
async def detailed_health():
    """Health check detalhado com status de cada componente"""
    global orchestrator, rag_service
    
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "components": {
            "orchestrator": {
                "status": "healthy" if orchestrator else "unavailable",
                "type": "LangGraph"
            },
            "rag_service": {
                "status": "healthy" if rag_service else "unavailable",
                "type": "ChromaDB + OpenAI"
            },
            "api": {
                "status": "healthy",
                "endpoints": "/chat/send, /chat/stream"
            }
        },
        "features": {
            "streaming": True,
            "structured_output": True,
            "checkpointing": True
        }
    }
    
    # Verifica se algum componente crítico está indisponível
    if not orchestrator or not rag_service:
        health_status["status"] = "degraded"
        health_status["error"] = "Critical components unavailable"
    
    return health_status


'''