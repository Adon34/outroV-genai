from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db  # <-- Importe get_db
from app.models.schemas import User
from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from app.schemas.user import UserCreate, UserInDB, UserRegisterResponse

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: Optional[dict] = None

@router.post("/register", response_model=UserRegisterResponse)
async def register(
    user_data: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Create a new user account"""
    # Check if user exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name or "",
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return UserRegisterResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        full_name=db_user.full_name,
        is_active=db_user.is_active,
        created_at=db_user.created_at
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    stmt = select(User).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
        }
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str = None, current_user: User = Depends(get_current_user)):
    """Refresh JWT token"""
    # Se não houver refresh_token, apenas gere um novo token
    access_token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=timedelta(minutes=30)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }