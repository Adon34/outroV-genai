# backend/app/routers/meals.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models import Meal, User
from app.schemas.meal import MealCreate, MealOut, MealUpdate
from app.utils.auth import get_current_user
from sqlalchemy import select, and_, func, cast, Date

router = APIRouter()

@router.post("/", response_model=MealOut)
async def create_meal(
    meal: MealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new meal"""
    
    # Usar a data fornecida ou a data atual
    meal_date = meal.date if meal.date else datetime.now()
    
    db_meal = Meal(
        user_id=current_user.id,
        name=meal.name,
        description=meal.description,
        meal_type=meal.meal_type,
        calories=meal.calories,
        protein=meal.protein,
        carbs=meal.carbs,
        fats=meal.fats,
        date=meal_date,
        created_at=datetime.utcnow()
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
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    stmt = select(Meal).where(
        and_(
            Meal.user_id == current_user.id,
            Meal.date >= today_start,
            Meal.date <= today_end
        )
    ).order_by(Meal.date)
    
    result = await db.execute(stmt)
    meals = result.scalars().all()
    return meals

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
        start_date = datetime.combine(date_from, datetime.min.time())
        conditions.append(Meal.date >= start_date)
    if date_to:
        end_date = datetime.combine(date_to, datetime.max.time())
        conditions.append(Meal.date <= end_date)
    if meal_type:
        conditions.append(Meal.meal_type == meal_type)
    
    stmt = select(Meal).where(and_(*conditions)).offset(skip).limit(limit).order_by(Meal.date.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/weekly", response_model=List[MealOut])
async def get_weekly_meals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get meals from the last 7 days"""
    week_ago = datetime.now() - timedelta(days=7)
    
    stmt = select(Meal).where(
        and_(
            Meal.user_id == current_user.id,
            Meal.date >= week_ago
        )
    ).order_by(Meal.date.desc())
    
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
    
    # Atualizar apenas os campos fornecidos
    update_data = meal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
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

@router.get("/stats/daily", response_model=dict)
async def get_daily_stats(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily nutrition statistics"""
    
    if target_date:
        target = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        target = datetime.now()
    
    day_start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    stmt = select(Meal).where(
        and_(
            Meal.user_id == current_user.id,
            Meal.date >= day_start,
            Meal.date <= day_end
        )
    )
    result = await db.execute(stmt)
    meals = result.scalars().all()
    
    stats = {
        "date": day_start.date().isoformat(),
        "total_calories": sum(m.calories or 0 for m in meals),
        "total_protein": sum(m.protein or 0 for m in meals),
        "total_carbs": sum(m.carbs or 0 for m in meals),
        "total_fats": sum(m.fats or 0 for m in meals),
        "meals_count": len(meals),
        "meals_by_type": {}
    }
    
    # Agrupar por tipo de refeição
    for meal in meals:
        meal_type = meal.meal_type or "other"
        if meal_type not in stats["meals_by_type"]:
            stats["meals_by_type"][meal_type] = {
                "count": 0,
                "total_calories": 0,
                "meals": []
            }
        stats["meals_by_type"][meal_type]["count"] += 1
        stats["meals_by_type"][meal_type]["total_calories"] += meal.calories or 0
        stats["meals_by_type"][meal_type]["meals"].append({
            "id": meal.id,
            "name": meal.name,
            "calories": meal.calories
        })
    
    return stats