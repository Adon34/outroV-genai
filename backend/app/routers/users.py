# backend/app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserUpdate, UserInDB
from app.utils.auth import get_current_user
from app.models.schemas import User

router = APIRouter()

@router.get("/me", response_model=UserInDB)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.put("/profile", response_model=UserInDB)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.get("/progress")
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user progress data"""
    # This would typically aggregate data from meals, workouts, and progress logs
    # For now, return basic user stats
    return {
        "weight": current_user.weight,
        "height": current_user.height,
        "bmi": current_user.bmi,
        "daily_calories": current_user.daily_calories,
        "goals": [goal.name for goal in current_user.goals]
    }