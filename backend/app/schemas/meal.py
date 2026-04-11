# backend/app/schemas/meal.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MealBase(BaseModel):
    name: str
    description: Optional[str] = None
    calories: Optional[float] = None  # ← tornar opcional
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    meal_type: Optional[str] = None  # ← tornar opcional (breakfast, lunch, dinner, snack)
    date: Optional[datetime] = None

class MealCreate(MealBase):
    pass

class MealResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    meal_type: Optional[str]
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fats: Optional[float]
    date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

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