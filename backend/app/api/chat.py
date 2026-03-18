# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json
import logging

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationOut, MessageOut
from app.services.rag_service import rag_service
from app.services.chat_service import ChatService
from app.utils.auth import get_current_user, get_current_user_ws
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response"""
    chat_service = ChatService(db)
    
    # Get or create conversation
    conversation = await chat_service.get_or_create_conversation(
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        title=request.message[:50]
    )
    
    # Save user message
    await chat_service.save_message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )
    
    # Get conversation history
    history = await chat_service.get_conversation_history(conversation.id)
    
    # Get AI response
    response = await rag_service.get_response(
        user_id=current_user.id,
        message=request.message,
        conversation_history=history
    )
    
    # Save AI response
    await chat_service.save_message(
        conversation_id=conversation.id,
        role="assistant",
        content=response["answer"],
        metadata={"sources": response["sources"]}
    )
    
    return ChatResponse(
        answer=response["answer"],
        sources=response["sources"],
        conversation_id=conversation.id
    )

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str
):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    try:
        # Authenticate user
        user = await get_current_user_ws(token)
        if not user:
            await websocket.send_json({"error": "Authentication failed"})
            await websocket.close(code=1008)
            return
        
        # Get database session
        async for db in get_db():
            chat_service = ChatService(db)
            
            # Verify conversation belongs to user
            conversation = await chat_service.get_conversation(conversation_id)
            if not conversation or conversation.user_id != user.id:
                await websocket.send_json({"error": "Conversation not found"})
                await websocket.close(code=1008)
                return
            
            # Send welcome message
            await websocket.send_json({
                "type": "connected",
                "message": "Connected to chat server"
            })
            
            # Main loop
            while True:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Save user message
                await chat_service.save_message(
                    conversation_id=conversation.id,
                    role="user",
                    content=message_data["message"]
                )
                
                # Send typing indicator
                await websocket.send_json({"type": "typing", "status": True})
                
                # Get history
                history = await chat_service.get_conversation_history(conversation.id)
                
                # Get AI response
                response = await rag_service.get_response(
                    user_id=user.id,
                    message=message_data["message"],
                    conversation_history=history
                )
                
                # Save AI response
                await chat_service.save_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response["answer"],
                    metadata={"sources": response["sources"]}
                )
                
                # Send response
                await websocket.send_json({
                    "type": "message",
                    "content": response["answer"],
                    "sources": response["sources"]
                })
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from conversation {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)

@router.get("/conversations", response_model=List[ConversationOut])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """Get user's conversations"""
    chat_service = ChatService(db)
    return await chat_service.get_user_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific conversation"""
    chat_service = ChatService(db)
    conversation = await chat_service.get_conversation(conversation_id)
    
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation"""
    chat_service = ChatService(db)
    
    conversation = await chat_service.get_conversation(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await chat_service.delete_conversation(conversation_id)
    return {"message": "Conversation deleted successfully"}