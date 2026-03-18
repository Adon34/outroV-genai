# backend/app/routers/meals.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date

from app.database import get_db
from app.models.schemas import Meal, User
from app.schemas.meal import MealCreate, MealOut, MealUpdate
from app.utils.auth import get_current_user
from sqlalchemy import select, and_, func

router = APIRouter()

@router.post("/", response_model=MealOut)
async def create_meal(
    meal: MealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new meal"""
    db_meal = Meal(
        user_id=current_user.id,
        **meal.dict()
    )
    db.add(db_meal)
    await db.commit()
    await db.refresh(db_meal)
    return db_meal

@router.get("/today", response_model=List[MealOut])
async def get_today_meals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get today's meals"""
    today = date.today()
    stmt = select(Meal).where(
        and_(
            Meal.user_id == current_user.id,
            func.date(Meal.date) == today
        )
    ).order_by(Meal.created_at)

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/", response_model=List[MealOut])
async def get_meals(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    meal_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get meals with optional filters"""
    conditions = [Meal.user_id == current_user.id]

    if date_from:
        conditions.append(Meal.date >= date_from)
    if date_to:
        conditions.append(Meal.date <= date_to)
    if meal_type:
        conditions.append(Meal.meal_type == meal_type)

    stmt = select(Meal).where(and_(*conditions)).offset(skip).limit(limit).order_by(Meal.date.desc())

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{meal_id}", response_model=MealOut)
async def get_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific meal"""
    stmt = select(Meal).where(
        and_(
            Meal.id == meal_id,
            Meal.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    meal = result.scalar_one_or_none()

    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    return meal

@router.put("/{meal_id}", response_model=MealOut)
async def update_meal(
    meal_id: int,
    meal_update: MealUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a meal"""
    stmt = select(Meal).where(
        and_(
            Meal.id == meal_id,
            Meal.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_meal = result.scalar_one_or_none()

    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    for field, value in meal_update.dict(exclude_unset=True).items():
        setattr(db_meal, field, value)

    await db.commit()
    await db.refresh(db_meal)
    return db_meal

@router.delete("/{meal_id}")
async def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a meal"""
    stmt = select(Meal).where(
        and_(
            Meal.id == meal_id,
            Meal.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    db_meal = result.scalar_one_or_none()

    if not db_meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    await db.delete(db_meal)
    await db.commit()
    return {"message": "Meal deleted successfully"}