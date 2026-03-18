# backend/app/routers/workouts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date

from app.database import get_db
from app.models.schemas import Workout, User
from app.schemas.workout import WorkoutCreate, WorkoutOut, WorkoutUpdate
from app.utils.auth import get_current_user
from sqlalchemy import select, and_, func

router = APIRouter()

@router.post("/", response_model=WorkoutOut)
async def create_workout(
    workout: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workout"""
    db_workout = Workout(
        user_id=current_user.id,
        **workout.dict()
    )
    db.add(db_workout)
    await db.commit()
    await db.refresh(db_workout)
    return db_workout

@router.get("/today", response_model=List[WorkoutOut])
async def get_today_workouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get today's workouts"""
    today = date.today()
    stmt = select(Workout).where(
        and_(
            Workout.user_id == current_user.id,
            func.date(Workout.date) == today
        )
    ).order_by(Workout.created_at)

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/", response_model=List[WorkoutOut])
async def get_workouts(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workouts with optional filters"""
    conditions = [Workout.user_id == current_user.id]

    if date_from:
        conditions.append(Workout.date >= date_from)
    if date_to:
        conditions.append(Workout.date <= date_to)

    stmt = select(Workout).where(and_(*conditions)).offset(skip).limit(limit).order_by(Workout.date.desc())

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{workout_id}", response_model=WorkoutOut)
async def get_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific workout"""
    stmt = select(Workout).where(
        and_(
            Workout.id == workout_id,
            Workout.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    workout = result.scalar_one_or_none()

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return workout

@router.put("/{workout_id}", response_model=WorkoutOut)
async def update_workout(
    workout_id: int,
    workout_update: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a workout"""
    stmt = select(Workout).where(
        and_(
            Workout.id == workout_id,
            Workout.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_workout = result.scalar_one_or_none()

    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    for field, value in workout_update.dict(exclude_unset=True).items():
        setattr(db_workout, field, value)

    await db.commit()
    await db.refresh(db_workout)
    return db_workout

@router.delete("/{workout_id}")
async def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a workout"""
    stmt = select(Workout).where(
        and_(
            Workout.id == workout_id,
            Workout.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_workout = result.scalar_one_or_none()

    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    await db.delete(db_workout)
    await db.commit()
    return {"message": "Workout deleted successfully"}