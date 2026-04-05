# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=13, le=120)
    weight: Optional[float] = Field(None, gt=0, le=300)
    height: Optional[float] = Field(None, gt=0, le=250)
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    diet_type: Optional[str] = None
    health_conditions: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    preferences: Optional[Dict[str, Any]] = {}
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match("^[a-zA-Z0-9_]+$", v):
            raise ValueError('Username must be alphanumeric with underscores only')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v and v not in ['male', 'female', 'other']:
            raise ValueError('Gender must be male, female, or other')
        return v
    
    @validator('activity_level')
    def validate_activity_level(cls, v):
        valid_levels = ['sedentary', 'light', 'moderate', 'active', 'very_active']
        if v and v not in valid_levels:
            raise ValueError(f'Activity level must be one of: {valid_levels}')
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class UserRegisterResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=13, le=120)
    weight: Optional[float] = Field(None, gt=0, le=300)
    height: Optional[float] = Field(None, gt=0, le=250)
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    diet_type: Optional[str] = None
    health_conditions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    bmi: Optional[float] = None
    daily_calories: Optional[int] = None
    goals: List[str] = []
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None