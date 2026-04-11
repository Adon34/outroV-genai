# backend/app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.schemas.user import UserUpdate, UserInDB
from app.utils.auth import get_current_user
from app.models import User

router = APIRouter()

@router.get("/me", response_model=UserInDB)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "age": current_user.age,
        "weight": current_user.weight,
        "height": current_user.height,
        "gender": current_user.gender,
        "activity_level": current_user.activity_level,
        "is_active": current_user.is_active,
        "is_verified": getattr(current_user, 'is_verified', True),  # Valor padrão
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.put("/profile", response_model=UserInDB)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    for field, value in user_update.dict(exclude_unset=True).items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Profile updated successfully"}

@router.get("/progress")
async def get_user_progress(
    current_user: User = Depends(get_current_user)
):
    """Get user progress data"""
    try:
        # Retorna dados básicos do usuário
        return {
            "weight": current_user.weight,
            "goal_weight": None,  # Pode adicionar depois se tiver campo
            "weight_change": 0,
            "bmi": calculate_bmi(current_user.weight, current_user.height),
            "body_fat": None,
            "daily_calories": current_user.daily_calories,
            "muscle_mass": None,
            "goals": [goal.name for goal in current_user.goals]
        }
    except Exception as e:
        # Em caso de erro, retorna dados mínimos
        return {
            "weight": None,
            "goal_weight": None, 
            "weight_change": None,
            "bmi": None,
            "body_fat": None,
            "daily_calories": None,
            "muscle_mass": None,
            "goals": []
        }
        
def calculate_bmi(weight: Optional[float], height: Optional[float]) -> Optional[float]:
    """Calculate BMI"""
    if weight and height and height > 0:
        height_m = height / 100
        return round(weight / (height_m * height_m), 1)
    return None
    