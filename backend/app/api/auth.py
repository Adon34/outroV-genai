# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Any

from app.database import get_db
from app.schemas.user import UserCreate, Token, UserInDB
from app.services.user_service import UserService
from app.utils.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new user"""
    user_service = UserService(db)
    
    # Check if user exists
    existing_user = await user_service.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_username = await user_service.get_by_username(user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = await user_service.create(user_data)
    
    # Add to RAG context
    from app.services.rag_service import rag_service
    await rag_service.add_user_context(user.id, user.to_dict())
    
    return user

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Login and get access token"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    return {
        "access_token": create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        ),
        "refresh_token": create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        ),
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get new access token using refresh token"""
    from app.utils.auth import verify_refresh_token
    
    user_id = await verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return {
        "access_token": create_access_token(
            data={"sub": str(user_id)},
            expires_delta=access_token_expires
        ),
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserInDB)
async def get_current_user_info(
    current_user = Depends(get_current_user)
) -> Any:
    """Get current user information"""
    return current_user

@router.post("/logout")
async def logout(
    current_user = Depends(get_current_user)
) -> Any:
    """Logout user (invalidate token)"""
    # In a real app, you might want to blacklist the token
    return {"message": "Successfully logged out"}