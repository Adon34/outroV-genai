# backend/app/routers/workouts.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models import Workout, User
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
    
    workout_date = workout.date if workout.date else datetime.now()
    
    # Converter exercises para dicionário
    exercises_dict = [ex.dict() for ex in workout.exercises] if workout.exercises else []
    
    db_workout = Workout(
        user_id=current_user.id,
        name=workout.name,
        description=workout.description,
        duration=workout.duration,
        calories_burned=workout.calories_burned,
        exercises=exercises_dict,
        date=workout_date,
        created_at=datetime.utcnow()
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
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    stmt = select(Workout).where(
        and_(
            Workout.user_id == current_user.id,
            Workout.date >= today_start,
            Workout.date <= today_end
        )
    ).order_by(Workout.date)
    
    result = await db.execute(stmt)
    workouts = result.scalars().all()
    return workouts

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
        start_date = datetime.combine(date_from, datetime.min.time())
        conditions.append(Workout.date >= start_date)
    if date_to:
        end_date = datetime.combine(date_to, datetime.max.time())
        conditions.append(Workout.date <= end_date)
    
    stmt = select(Workout).where(and_(*conditions)).offset(skip).limit(limit).order_by(Workout.date.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/weekly", response_model=List[WorkoutOut])
async def get_weekly_workouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get workouts from the last 7 days"""
    
    week_ago = datetime.now() - timedelta(days=7)
    
    stmt = select(Workout).where(
        and_(
            Workout.user_id == current_user.id,
            Workout.date >= week_ago
        )
    ).order_by(Workout.date.desc())
    
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
    
    update_data = workout_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "exercises" and value:
            # Converter exercises para dicionário
            value = [ex.dict() if hasattr(ex, 'dict') else ex for ex in value]
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

@router.get("/stats/daily", response_model=dict)
async def get_daily_stats(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily workout statistics"""
    
    if target_date:
        target = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        target = datetime.now()
    
    day_start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    stmt = select(Workout).where(
        and_(
            Workout.user_id == current_user.id,
            Workout.date >= day_start,
            Workout.date <= day_end
        )
    )
    result = await db.execute(stmt)
    workouts = result.scalars().all()
    
    stats = {
        "date": day_start.date().isoformat(),
        "total_workouts": len(workouts),
        "total_duration_minutes": sum(w.duration or 0 for w in workouts),
        "total_calories_burned": sum(w.calories_burned or 0 for w in workouts),
        "workouts": [
            {
                "id": w.id,
                "name": w.name,
                "duration": w.duration,
                "calories_burned": w.calories_burned
            } for w in workouts
        ]
    }
    
    return stats