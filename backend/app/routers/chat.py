# backend/app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import logging
from datetime import datetime

from app.services.rag_service import RAGService
from app.database import AsyncSessionLocal
from app.models import User, Conversation, Message
from app.utils.auth import get_current_user
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Importações dos agents modernos
from app.agents.orchestrator import ModernOrchestrator
from app.agents.profile_agent import ModernProfileAgent
from app.agents.workout_agent import ModernWorkoutAgent
from app.agents.diet_agent import ModernDietAgent

router = APIRouter()
logger = logging.getLogger(__name__)

# Instâncias globais
rag_service = None
orchestrator = None
rag_service_initialized = False


# ============================================
# DEPENDÊNCIAS E INICIALIZAÇÃO
# ============================================

async def get_rag_service():
    """Obtém ou inicializa o RAG Service moderno"""
    global rag_service, rag_service_initialized
    
    if rag_service is None:
        logger.info("Inicializando RAG Service...")
        rag_service = RAGService()
        await rag_service.initialize()
        rag_service_initialized = True
        logger.info("RAG Service initialized successfully")
    elif not rag_service_initialized:
        logger.info("Reinicializando RAG Service...")
        await rag_service.initialize()
        rag_service_initialized = True
    
    return rag_service


async def get_orchestrator():
    """Obtém ou cria o orquestrador moderno (LangGraph)"""
    global orchestrator
    
    if orchestrator is None:
        logger.info("Inicializando Modern Orchestrator com LangGraph...")
        
        # Obtém RAG service
        rag = await get_rag_service()
        
        # Importações necessárias
        from langchain_openai import ChatOpenAI
        from app.config import settings
        
        # Cria LLM com streaming habilitado
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            streaming=True,  # ✅ Essencial para WebSocket
            timeout=30,
            max_retries=2,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Cria orquestrador moderno
        orchestrator = ModernOrchestrator(
            llm=llm,
            db_session_factory=AsyncSessionLocal,
            rag_service=rag
        )
        
        logger.info("Modern Orchestrator initialized successfully with LangGraph")
    
    return orchestrator


# ============================================
# MODELOS PYDANTIC
# ============================================

class ChatRequest(BaseModel):
    """Request model para chat"""
    message: str = Field(..., description="Mensagem do usuário", min_length=1)
    conversation_id: Optional[int] = Field(None, description="ID da conversa existente")
    auto_create: bool = Field(True, description="Usar agentes para processamento inteligente")
    stream: bool = Field(False, description="Habilitar streaming de resposta")


class ChatResponse(BaseModel):
    """Response model para chat"""
    answer: str = Field(..., description="Resposta do assistente")
    conversation_id: int = Field(..., description="ID da conversa")
    sources: List[Dict] = Field(default_factory=list, description="Fontes utilizadas")
    action: Optional[str] = Field(None, description="Ação executada pelo agente")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Dados da ação")
    confidence: float = Field(0.0, description="Confiança da resposta")
    requires_professional: bool = Field(False, description="Recomenda consultar profissional")


class WebSocketMessage(BaseModel):
    """Model para mensagens WebSocket"""
    message: str
    auto_create: bool = True
    conversation_id: Optional[int] = None


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

async def get_or_create_conversation(
    db: AsyncSession,
    user_id: int,
    conversation_id: Optional[int],
    message_preview: str
) -> Conversation:
    """Obtém ou cria uma conversa para o usuário"""
    
    if conversation_id:
        # Busca conversa existente
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        
        return conversation
    
    # Cria nova conversa
    title = message_preview[:50] + "..." if len(message_preview) > 50 else message_preview
    conversation = Conversation(
        user_id=user_id,
        title=title,
        created_at=datetime.utcnow()
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


async def get_chat_history(
    db: AsyncSession,
    conversation_id: int,
    limit: int = 10
) -> List[Dict[str, str]]:
    """Recupera histórico da conversa"""
    
    # ✅ Selecionar apenas as colunas que existem
    stmt = select(
        Message.role, 
        Message.content, 
        Message.created_at
    ).where(
        Message.conversation_id == conversation_id
    ).order_by(desc(Message.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    messages = result.all()
    
    # Retorna em ordem cronológica
    return [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(messages)
    ]


def format_agent_response(
    agent_result: Dict[str, Any],
    conversation_id: int
) -> ChatResponse:
    """Formata a resposta do agente para o formato padrão"""
    
    action = agent_result.get("action", "chat")
    action_data = agent_result.get("action_data")
    response_text = agent_result.get("message", agent_result.get("answer", ""))
    
    # Adiciona informações extras baseadas na ação
    if action == "profile_updated" and action_data:
        response_text += f"\n\n📊 **Dados atualizados:**\n"
        response_text += "\n".join([f"- {k}: {v}" for k, v in action_data.items()])
    
    elif action == "workout_created" and action_data:
        workout = action_data
        response_text += f"\n\n💪 **Detalhes do treino:**\n"
        response_text += f"- Nome: {workout.get('name', 'Personalizado')}\n"
        response_text += f"- Duração: {workout.get('estimated_duration_minutes', 45)} minutos\n"
        response_text += f"- Dificuldade: {workout.get('difficulty', 'intermediário')}\n\n"
        
        if workout.get('exercises'):
            response_text += "**Exercícios:**\n"
            for ex in workout.get('exercises', [])[:5]:
                response_text += f"  • {ex.get('name')}: {ex.get('sets', 3)}x{ex.get('reps', 12)}\n"
    
    elif action == "meal_added" and action_data:
        response_text += f"\n\n🍽️ **Refeição registrada com sucesso!**"
    
    return ChatResponse(
        answer=response_text,
        conversation_id=conversation_id,
        sources=agent_result.get("sources", []),
        action=action,
        action_data=action_data,
        confidence=agent_result.get("confidence", 0.8),
        requires_professional=agent_result.get("requires_professional", False)
    )


# ============================================
# ENDPOINTS REST
# ============================================

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    rag: RAGService = Depends(get_rag_service),
    agent_orchestrator: ModernOrchestrator = Depends(get_orchestrator)
):
    """
    Envia mensagem para o assistente AI com processamento baseado em agentes.
    """
    try:
        async with AsyncSessionLocal() as db:
            # 1. Obtém ou cria conversa
            conversation = await get_or_create_conversation(
                db=db,
                user_id=current_user.id,
                conversation_id=request.conversation_id,
                message_preview=request.message
            )
            
            # 2. Salva mensagem do usuário
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                created_at=datetime.utcnow()
            )
            db.add(user_message)
            await db.commit()
            
            # 3. Recupera histórico da conversa
            chat_history = await get_chat_history(db, conversation.id)
            
            # 4. Processa com o orquestrador moderno
            if request.auto_create:
                # ✅ CORREÇÃO: Descomentar o user_id
                agent_result = await agent_orchestrator.process_message(
                    message=request.message,
                    user_id=current_user.id,  # ← DESCOMENTADO!
                    chat_history=chat_history,
                    db=db,
                    thread_id=f"conv_{conversation.id}"
                )
                
                response_text = agent_result.get("message", agent_result.get("answer", ""))
                
            else:
                # Fallback para RAG tradicional
                # ✅ CORREÇÃO: Adicionar user_id no generate_response
                response = await rag.generate_response(
                    user_id=current_user.id,  # ← ADICIONAR!
                    message=request.message,
                    conversation_history=chat_history,
                    use_cache=True
                )
                response_text = response["answer"]
                agent_result = {
                    "action": "chat",
                    "sources": response.get("sources", []),
                    "confidence": response.get("confidence", 0.8)
                }
            
            # 5. Salva resposta do assistente
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                message_metadata={
                    "action": agent_result.get("action", "chat"),
                    "action_data": agent_result.get("action_data"),
                    "sources": agent_result.get("sources", []),
                    "confidence": agent_result.get("confidence", 0.0),
                    "agent_version": "langgraph_v2"
                },
                created_at=datetime.utcnow()
            )
            db.add(assistant_message)
            await db.commit()
            
            # 6. Formata e retorna resposta
            return format_agent_response(agent_result, conversation.id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: ModernOrchestrator = Depends(get_orchestrator)
):
    """
    Envia mensagem com streaming de resposta via SSE.
    Experiência premium com resposta em tempo real.
    """
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        try:
            async with AsyncSessionLocal() as db:
                # Obtém ou cria conversa
                conversation = await get_or_create_conversation(
                    db=db,
                    user_id=current_user.id,
                    conversation_id=request.conversation_id,
                    message_preview=request.message
                )
                
                # Salva mensagem do usuário
                user_message = Message(
                    conversation_id=conversation.id,
                    role="user",
                    content=request.message,
                    created_at=datetime.utcnow()
                )
                db.add(user_message)
                await db.commit()
                
                # Recupera histórico
                chat_history = await get_chat_history(db, conversation.id)
                
                # Stream da resposta do agente
                full_response = ""
                
                async for event in agent_orchestrator.process_message_streaming(
                    message=request.message,
                    user_id=current_user.id,
                    chat_history=chat_history,
                    thread_id=f"conv_{conversation.id}"
                ):
                    # Envia evento para o cliente
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                    
                    # Acumula resposta completa
                    if event.get("type") == "node_complete" and event.get("partial_response"):
                        full_response += event.get("partial_response", "")
                
                # Salva resposta completa no banco
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_response,
                    message_metadata={
                        "agent_version": "langgraph_v2",
                        "streaming": True
                    },
                    created_at=datetime.utcnow()
                )
                db.add(assistant_message)
                await db.commit()
                
                # Evento final
                yield f"data: {json.dumps({'type': 'end', 'complete': True, 'conversation_id': conversation.id})}\n\n"
                
        except Exception as e:
            logger.error(f"Erro no streaming: {e}", exc_info=True)
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


# ============================================
# WEB SOCKET ENDPOINT
# ============================================

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str
):
    """
    WebSocket para chat em tempo real com suporte a streaming.
    
    Características:
    - Conexão persistente
    - Respostas token-by-token
    - Suporte a múltiplas mensagens
    """
    await websocket.accept()
    
    try:
        # Valida usuário via token
        user = await get_current_user(token)
        rag = await get_rag_service()
        agent_orchestrator = await get_orchestrator()
        
        async with AsyncSessionLocal() as db:
            # Verifica se conversa existe e pertence ao usuário
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                await websocket.send_json({"error": "Conversa não encontrada"})
                await websocket.close()
                return
            
            logger.info(f"WebSocket conectado: user={user.id}, conversation={conversation_id}")
            
            # Loop principal do WebSocket
            while True:
                # Recebe mensagem do cliente
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                user_message_text = message_data.get("message", "")
                auto_create = message_data.get("auto_create", True)
                
                if not user_message_text:
                    await websocket.send_json({"error": "Mensagem vazia"})
                    continue
                
                # Salva mensagem do usuário
                user_message = Message(
                    conversation_id=conversation.id,
                    role="user",
                    content=user_message_text,
                    created_at=datetime.utcnow()
                )
                db.add(user_message)
                await db.commit()
                
                # Recupera histórico
                chat_history = await get_chat_history(db, conversation.id)
                
                # Processa com o orquestrador
                if auto_create:
                    # Usa o orquestrador moderno
                    result = await agent_orchestrator.process_message(
                        message=user_message_text,
                        user_id=user.id,
                        chat_history=chat_history,
                        db=db,
                        thread_id=f"conv_{conversation.id}"
                    )
                    
                    response_text = result.get("message", result.get("answer", ""))
                    action = result.get("action", "chat")
                    action_data = result.get("action_data")
                    sources = result.get("sources", [])
                    confidence = result.get("confidence", 0.0)
                    
                else:
                    # Fallback RAG tradicional
                    response = await rag.generate_response(
                        user_id=user.id,
                        message=user_message_text,
                        conversation_history=chat_history,
                        use_cache=True
                    )
                    response_text = response["answer"]
                    action = "chat"
                    action_data = None
                    sources = response.get("sources", [])
                    confidence = response.get("confidence", 0.0)
                
                # Salva resposta do assistente
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response_text,
                    message_metadata={
                        "action": action,
                        "action_data": action_data,
                        "sources": sources,
                        "confidence": confidence,
                        "agent_version": "langgraph_v2"
                    },
                    created_at=datetime.utcnow()
                )
                db.add(assistant_message)
                await db.commit()
                
                # Envia resposta via WebSocket
                await websocket.send_json({
                    "answer": response_text,
                    "action": action,
                    "action_data": action_data,
                    "sources": sources,
                    "confidence": confidence,
                    "conversation_id": conversation.id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Cliente desconectado da conversa {conversation_id}")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close()
        except:
            pass


# ============================================
# WEB SOCKET COM STREAMING (VERSÃO AVANÇADA)
# ============================================

@router.websocket("/ws/stream/{conversation_id}")
async def websocket_stream_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str
):
    """
    WebSocket avançado com streaming token-by-token.
    
    Envia cada token da resposta conforme é gerado,
    proporcionando experiência de digitação em tempo real.
    """
    await websocket.accept()
    
    try:
        user = await get_current_user(token)
        agent_orchestrator = await get_orchestrator()
        
        async with AsyncSessionLocal() as db:
            # Verifica conversa
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                await websocket.send_json({"error": "Conversa não encontrada"})
                await websocket.close()
                return
            
            logger.info(f"WebSocket Streaming conectado: user={user.id}")
            
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                auto_create = message_data.get("auto_create", True)
                
                if not user_message:
                    continue
                
                # Salva mensagem do usuário
                user_msg = Message(
                    conversation_id=conversation.id,
                    role="user",
                    content=user_message,
                    created_at=datetime.utcnow()
                )
                db.add(user_msg)
                await db.commit()
                
                # Recupera histórico
                chat_history = await get_chat_history(db, conversation.id)
                
                # Stream da resposta
                full_response = ""
                
                async for chunk in agent_orchestrator.process_message_streaming(
                    message=user_message,
                    user_id=user.id,
                    chat_history=chat_history,
                    thread_id=f"conv_{conversation.id}"
                ):
                    # Envia token individual
                    await websocket.send_json({
                        "type": "token",
                        "content": chunk.get("partial_response", ""),
                        "node": chunk.get("node")
                    })
                    
                    if chunk.get("partial_response"):
                        full_response += chunk.get("partial_response", "")
                
                # Salva resposta completa
                assistant_msg = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_response,
                    message_metadata={"streaming": True, "agent_version": "langgraph_v2"},
                    created_at=datetime.utcnow()
                )
                db.add(assistant_msg)
                await db.commit()
                
                # Sinaliza fim da resposta
                await websocket.send_json({
                    "type": "end",
                    "conversation_id": conversation.id
                })
                
    except WebSocketDisconnect:
        logger.info(f"Cliente desconectado do streaming")
    except Exception as e:
        logger.error(f"Erro no WebSocket streaming: {e}", exc_info=True)


# ============================================
# ENDPOINTS ADICIONAIS
# ============================================

@router.get("/actions/recent")
async def get_recent_actions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """Obtém ações recentes executadas pelos agentes para o usuário"""
    from sqlalchemy import and_, desc
    
    try:
        logger.info(f"GET /chat/actions/recent - user_id: {current_user.id}")
        
        # Buscar mensagens do assistente com ações
        stmt = select(Message).join(
            Conversation, Message.conversation_id == Conversation.id
        ).where(
            Conversation.user_id == current_user.id,
            Message.role == "assistant",
            Message.message_metadata.isnot(None)
        ).order_by(desc(Message.created_at)).limit(10)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        actions = []
        for msg in messages:
            if msg.message_metadata and msg.message_metadata.get("action"):
                actions.append({
                    "timestamp": msg.created_at.isoformat(),
                    "action": msg.message_metadata.get("action"),
                    "action_data": msg.message_metadata.get("action_data"),
                    "confidence": msg.message_metadata.get("confidence", 0.0),
                    "context": msg.content[:200] if msg.content else "",
                    "conversation_id": msg.conversation_id
                })
        
        return actions  # ← Retorna array direto
        
    except Exception as e:
        logger.error(f"Erro ao buscar ações: {e}", exc_info=True)
        return []
    

@router.post("/extract-profile")
async def extract_profile_from_message(
    message: str,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: ModernOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """
    Extrai métricas de perfil de uma mensagem sem salvar no histórico.
    Útil para processamento assíncrono de dados.
    """
    try:
        # Usa o profile agent diretamente
        result = await agent_orchestrator.profile_agent.process(
            message=message,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "success": True,
            "extracted_data": result.get("updated_fields", {}),
            "message": result.get("message", ""),
            "needs_more_info": result.get("needs_more_info", False),
            "missing_fields": result.get("missing_fields", [])
        }
        
    except Exception as e:
        logger.error(f"Erro ao extrair perfil: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/state")
async def get_conversation_state(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: ModernOrchestrator = Depends(get_orchestrator)
):
    """
    Recupera o estado interno da conversa no LangGraph.
    Útil para debug e retomada de conversas.
    """
    try:
        thread_id = f"conv_{conversation_id}"
        state = await agent_orchestrator.get_conversation_state(thread_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Estado da conversa não encontrado")
        
        return {
            "conversation_id": conversation_id,
            "thread_id": thread_id,
            "state": {
                "current_intent": state.get("current_intent"),
                "confidence": state.get("confidence"),
                "iteration": state.get("iteration"),
                "needs_more_info": state.get("needs_more_info"),
                "has_checkpoint": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar estado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}/state")
async def reset_conversation_state(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: ModernOrchestrator = Depends(get_orchestrator)
):
    """Reseta o estado interno da conversa no LangGraph"""
    try:
        thread_id = f"conv_{conversation_id}"
        success = await agent_orchestrator.reset_conversation(thread_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Falha ao resetar estado")
        
        return {
            "conversation_id": conversation_id,
            "reset": True,
            "message": "Estado da conversa resetado com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro ao resetar estado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HEALTH CHECK ESPECÍFICO DO CHAT
# ============================================

@router.get("/health")
async def chat_health(
    agent_orchestrator: ModernOrchestrator = Depends(get_orchestrator),
    rag: RAGService = Depends(get_rag_service)
):
    """Health check detalhado do sistema de chat"""
    
    return {
        "status": "healthy",
        "orchestrator": {
            "status": "ready",
            "type": "LangGraph",
            "version": "v2"
        },
        "rag_service": {
            "status": "ready",
            "initialized": rag_service_initialized
        },
        "features": {
            "streaming": True,
            "websocket": True,
            "structured_output": True,
            "checkpointing": True,
            "agents": ["profile", "workout", "diet", "chat"]
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    

# ============================================
# ENDPOINTS PARA HISTÓRICO DE CONVERSAS
# ============================================

@router.get("/conversations")
async def get_conversations_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """Lista todas as conversas do usuário"""
    from sqlalchemy import func, desc
    
    try:
        logger.info(f"GET /chat/conversations - user_id: {current_user.id}")
        
        # Buscar conversas - sem paginação
        stmt = select(Conversation).where(
            Conversation.user_id == current_user.id
        ).order_by(desc(Conversation.created_at))
        
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        conversations_data = []
        for conv in conversations:
            # Contar mensagens
            count_stmt = select(func.count()).select_from(Message).where(
                Message.conversation_id == conv.id
            )
            count_result = await db.execute(count_stmt)
            messages_count = count_result.scalar() or 0
            
            conversations_data.append({
                "id": conv.id,
                "title": conv.title or f"Conversa {conv.id}",
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "messages_count": messages_count
            })
        
        return conversations_data  # ← Retorna array direto
        
    except Exception as e:
        logger.error(f"Erro ao listar conversas: {e}", exc_info=True)
        return []


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages_list(
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """Lista mensagens de uma conversa específica"""
    from sqlalchemy import and_
    
    try:
        logger.info(f"GET /chat/conversations/{conversation_id}/messages - user_id: {current_user.id}")
        
        # Verificar se a conversa pertence ao usuário
        conv_stmt = select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conv_result = await db.execute(conv_stmt)
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            logger.warning(f"Conversa {conversation_id} não encontrada para user {current_user.id}")
            return {"messages": [], "total": 0}
        
        # Buscar mensagens
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "message_metadata": msg.message_metadata,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        return {
            "conversation_id": conversation_id,
            "conversation_title": conversation.title,
            "messages": messages_data,
            "total": len(messages_data)
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar mensagens: {e}", exc_info=True)
        return {"messages": [], "total": 0}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation_item(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """Exclui uma conversa"""
    from sqlalchemy import and_
    
    try:
        logger.info(f"DELETE /chat/conversations/{conversation_id} - user_id: {current_user.id}")
        
        stmt = select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {"message": "Conversa não encontrada"}
        
        await db.delete(conversation)
        await db.commit()
        
        return {"message": "Conversa excluída com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao excluir conversa: {e}", exc_info=True)
        return {"message": f"Erro: {str(e)}"}



'''
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import logging
from datetime import datetime

from app.services.rag_service import RAGService
from app.database import AsyncSessionLocal
from app.models import User, Conversation, Message
from app.utils.auth import get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.orchestrator import Orchestrator
from app.agents.workout_agent import WorkoutAgent
from app.agents.diet_agent import DietAgent
from app.agents.profile_agent import ProfileAgent


router = APIRouter()
logger = logging.getLogger(__name__)

# Instância global do RAG Service e Agent Orchestrator
rag_service = None
orchestrator = None
rag_service_initialized = False

async def get_rag_service():
    global rag_service, rag_service_initialized
    if rag_service is None:
        rag_service = RAGService()
        await rag_service.initialize()
        rag_service_initialized = True
        logger.info("RAG Service initialized successfully")
    elif not rag_service_initialized:
        await rag_service.initialize()
        rag_service_initialized = True
    return rag_service

async def get_orchestrator():
    """Get or create the agent orchestrator"""
    global orchestrator
    if orchestrator is None:
        # Get ChromaDB client from RAG service
        rag = await get_rag_service()
        
        # Import here to avoid circular imports
        from langchain_openai import ChatOpenAI
        from app.core.config import settings
        
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        
        orchestrator = Orchestrator(
            llm=llm,
            db_session_factory=AsyncSessionLocal,
            chroma_client=rag.chroma_client,
            rag_service=rag
        )
        logger.info("Orchestrator initialized successfully")
    return orchestrator

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    auto_create: bool = True  # Flag para permitir criação automática

class ChatResponse(BaseModel):
    answer: str
    conversation_id: int
    sources: Optional[list] = []
    action: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    rag: RAGService = Depends(get_rag_service),
    agent_orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Send a message to the AI assistant with agent-based processing"""
    try:
        async with AsyncSessionLocal() as db:
            # Cria ou recupera conversa
            if request.conversation_id:
                stmt = select(Conversation).where(
                    Conversation.id == request.conversation_id,
                    Conversation.user_id == current_user.id
                )
                result = await db.execute(stmt)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversa não encontrada")
            else:
                conversation = Conversation(
                    user_id=current_user.id,
                    title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
                    created_at=datetime.now()
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
            
            # Salva mensagem do usuário
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                created_at=datetime.now()
            )
            db.add(user_message)
            await db.commit()
            
            # Busca histórico recente (últimas 10 mensagens)
            stmt = select(Message).where(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at.desc()).limit(10)
            history_result = await db.execute(stmt)
            history_messages = history_result.scalars().all()
            
            chat_history = [
                {"role": msg.role, "content": msg.content} 
                for msg in reversed(history_messages)
            ]
            
            # Processa com o orquestrador de agentes
            if request.auto_create:
                # Usa os agentes para processamento inteligente
                agent_result = await agent_orchestrator.route(
                    message=request.message,
                    user_id=current_user.id,
                    chat_history=chat_history,
                    db=db
                )
                
                response_text = agent_result.get("message", agent_result.get("answer", ""))
                action = agent_result.get("action")
                action_data = agent_result.get("updated_fields") or agent_result.get("workout") or agent_result.get("meal")
                
                # Se o agente atualizou o perfil, busca dados atualizados
                if action == "profile_updated" and action_data:
                    # Atualiza o usuário na sessão
                    await db.refresh(current_user)
                    
                    # Adiciona contexto sobre a atualização
                    response_text += f"\n\n📊 **Dados atualizados:**\n" + \
                                     "\n".join([f"- {k}: {v}" for k, v in action_data.items()])
                
                # Se criou treino, adiciona info extra
                elif action == "workout_created" and action_data:
                    workout = action_data
                    response_text += f"\n\n💪 **Detalhes do treino:**\n"
                    response_text += f"- Nome: {workout.get('name')}\n"
                    response_text += f"- Duração estimada: {workout.get('estimated_duration_minutes', 45)} minutos\n"
                    response_text += f"- Dificuldade: {workout.get('difficulty', 'intermediário')}\n\n"
                    response_text += f"**Exercícios:**\n"
                    for ex in workout.get('exercises', []):
                        response_text += f"  • {ex.get('name')}: {ex.get('sets')} séries x {ex.get('reps')} reps\n"
                
                # Se criou refeição, adiciona info extra
                elif action == "meal_added" and action_data:
                    response_text += f"\n\n🍽️ **Refeição adicionada com sucesso!**"
                
                # Salva resposta do assistente com metadados da ação
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response_text,
                    meta_data={
                        "sources": agent_result.get("sources", []),
                        "action": action,
                        "action_data": action_data
                    },
                    created_at=datetime.now()
                )
                db.add(assistant_message)
                await db.commit()
                
                return ChatResponse(
                    answer=response_text,
                    sources=agent_result.get("sources", []),
                    conversation_id=conversation.id,
                    action=action,
                    action_data=action_data
                )
            
            else:
                # Fallback para RAG tradicional (sem agentes)
                response = await rag.generate_response(
                    user_id=current_user.id,
                    message=request.message,
                    conversation_history=chat_history,
                    use_cache=True
                )
                
                # Salva resposta do assistente
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response["answer"],
                    meta_data={"sources": response.get("sources", [])},
                    created_at=datetime.now()
                )
                db.add(assistant_message)
                await db.commit()
                
                return ChatResponse(
                    answer=response["answer"],
                    sources=response.get("sources", []),
                    conversation_id=conversation.id,
                    action="chat",
                    action_data=None
                )
            
    except Exception as e:
        logger.error(f"Erro no chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str
):
    """WebSocket for real-time chat with agent support"""
    await websocket.accept()
    
    try:
        # Valida usuário
        user = await get_current_user(token)
        rag = await get_rag_service()
        agent_orchestrator = await get_orchestrator()
        
        async with AsyncSessionLocal() as db:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                await websocket.send_json({"error": "Conversa não encontrada"})
                await websocket.close()
                return
            
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                user_message_text = message_data.get("message", "")
                auto_create = message_data.get("auto_create", True)
                
                # Salva mensagem do usuário
                user_message = Message(
                    conversation_id=conversation.id,
                    role="user",
                    content=user_message_text,
                    created_at=datetime.now()
                )
                db.add(user_message)
                await db.commit()
                
                # Busca histórico recente
                stmt = select(Message).where(
                    Message.conversation_id == conversation.id
                ).order_by(Message.created_at.desc()).limit(10)
                history_result = await db.execute(stmt)
                history_messages = history_result.scalars().all()
                
                chat_history = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in reversed(history_messages)
                ]
                
                # Processa com agente ou RAG normal
                if auto_create:
                    agent_result = await agent_orchestrator.route(
                        message=user_message_text,
                        user_id=user.id,
                        chat_history=chat_history,
                        db=db
                    )
                    
                    response_text = agent_result.get("message", agent_result.get("answer", ""))
                    action = agent_result.get("action")
                    action_data = agent_result.get("updated_fields") or agent_result.get("workout") or agent_result.get("meal")
                    
                    # Atualiza o usuário se necessário
                    if action == "profile_updated":
                        await db.refresh(user)
                else:
                    response = await rag.generate_response(
                        user_id=user.id,
                        message=user_message_text,
                        conversation_history=chat_history,
                        use_cache=True
                    )
                    response_text = response["answer"]
                    action = "chat"
                    action_data = None
                
                # Salva resposta do assistente
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response_text,
                    meta_data={
                        "action": action,
                        "action_data": action_data
                    },
                    created_at=datetime.now()
                )
                db.add(assistant_message)
                await db.commit()
                
                # Envia resposta via WebSocket
                await websocket.send_json({
                    "answer": response_text,
                    "action": action,
                    "action_data": action_data,
                    "sources": agent_result.get("sources", []) if auto_create else response.get("sources", [])
                })
                
    except WebSocketDisconnect:
        logger.info(f"Cliente desconectado da conversa {conversation_id}")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}", exc_info=True)
        await websocket.send_json({"error": str(e)})
        await websocket.close()

# Endpoint adicional para obter ações recentes do usuário
@router.get("/actions/recent")
async def get_recent_actions(
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """Get recent actions performed by agents for the user"""
    try:
        stmt = select(Message).where(
            Message.conversation_id == Conversation.id,
            Conversation.user_id == current_user.id,
            Message.role == "assistant",
            Message.metadata.isnot(None)
        ).order_by(Message.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        actions = []
        for msg in messages:
            if msg.metadata and msg.metadata.get("action"):
                actions.append({
                    "timestamp": msg.created_at.isoformat(),
                    "action": msg.metadata.get("action"),
                    "action_data": msg.metadata.get("action_data"),
                    "context": msg.content[:200]  # Preview da resposta
                })
        
        return {"actions": actions}
        
    except Exception as e:
        logger.error(f"Erro ao buscar ações: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para forçar atualização de perfil via chat
@router.post("/extract-profile")
async def extract_profile_from_message(
    message: str,
    current_user: User = Depends(get_current_user),
    agent_orchestrator: Orchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(AsyncSessionLocal)
):
    """Extract profile metrics from a message without saving to chat history"""
    try:
        result = await agent_orchestrator.profile_agent.process(
            message=message,
            user_id=current_user.id,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao extrair perfil: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    '''