# backend/app/schemas/workout.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Exercise(BaseModel):
    name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight: Optional[float] = None
    duration: Optional[int] = None  # in seconds
    notes: Optional[str] = None

class WorkoutBase(BaseModel):
    name: str
    description: Optional[str] = None  # ← existe na tabela
    duration: Optional[int] = None  # ← em minutos, existe na tabela
    calories_burned: Optional[float] = None  # ← existe na tabela
    exercises: Optional[List[Exercise]] = []
    date: Optional[datetime] = None

class WorkoutCreate(WorkoutBase):
    pass

class WorkoutUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    calories_burned: Optional[float] = None
    exercises: Optional[List[Exercise]] = None
    date: Optional[datetime] = None

class WorkoutOut(WorkoutBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True