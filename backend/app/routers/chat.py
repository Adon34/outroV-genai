# backend/app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional
from pydantic import BaseModel
import json
import logging

from app.services.rag_service import rag_service
from app.models.database import AsyncSessionLocal
from app.models.schemas import User, Conversation, Message
from app.utils.auth import get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    conversation_id: int

@router.post("/send")
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Envia mensagem e recebe resposta do chatbot"""
    try:
        async with AsyncSessionLocal() as db:
            # Cria ou recupera conversa
            if request.conversation_id:
                # Verifica se conversa pertence ao usuário
                stmt = select(Conversation).where(
                    Conversation.id == request.conversation_id,
                    Conversation.user_id == current_user.id
                )
                result = await db.execute(stmt)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversa não encontrada")
            else:
                # Cria nova conversa
                conversation = Conversation(
                    user_id=current_user.id,
                    title=request.message[:50] + "..."
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
            
            # Salva mensagem do usuário
            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.message
            )
            db.add(user_message)
            await db.commit()
            
            # Recupera histórico da conversa
            stmt = select(Message).where(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at)
            result = await db.execute(stmt)
            messages = result.scalars().all()
            
            # Prepara histórico para o RAG
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in messages[-10:]  # Últimas 10 mensagens
            ]
            
            # Obtém resposta do RAG
            response = await rag_service.get_response(
                user_id=current_user.id,
                message=request.message,
                conversation_history=history
            )
            
            # Salva resposta do assistente
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=response["answer"],
                metadata={"sources": response["sources"]}
            )
            db.add(assistant_message)
            await db.commit()
            
            return ChatResponse(
                answer=response["answer"],
                sources=response["sources"],
                conversation_id=conversation.id
            )
            
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar mensagem")

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str
):
    """WebSocket para chat em tempo real"""
    await websocket.accept()
    
    try:
        # Valida usuário
        user = await get_current_user(token)
        
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
            
            while True:
                # Recebe mensagem do cliente
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Salva mensagem do usuário
                user_message = Message(
                    conversation_id=conversation.id,
                    role="user",
                    content=message_data["message"]
                )
                db.add(user_message)
                await db.commit()
                
                # Obtém resposta
                response = await rag_service.get_response(
                    user_id=user.id,
                    message=message_data["message"]
                )
                
                # Salva resposta
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response["answer"],
                    metadata={"sources": response["sources"]}
                )
                db.add(assistant_message)
                await db.commit()
                
                # Envia resposta
                await websocket.send_json({
                    "answer": response["answer"],
                    "sources": response["sources"]
                })
                
    except WebSocketDisconnect:
        logger.info(f"Cliente desconectado da conversa {conversation_id}")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        await websocket.close()