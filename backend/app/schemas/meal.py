# backend/app/schemas/meal.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MealBase(BaseModel):
    name: str
    description: Optional[str] = None
    calories: float
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    meal_type: str  # breakfast, lunch, dinner, snack
    date: Optional[datetime] = None

class MealCreate(MealBase):
    pass

class MealUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    meal_type: Optional[str] = None
    date: Optional[datetime] = None

class MealOut(MealBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True