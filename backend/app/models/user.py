# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import json

# Tabela de associação para metas de usuário
user_goals = Table(
    'user_goals',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('goal_id', Integer, ForeignKey('goals.id'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    
    # Dados físicos
    age = Column(Integer)
    weight = Column(Float)
    height = Column(Float)
    gender = Column(String)
    body_fat = Column(Float, nullable=True)
    
    # Preferências e estilo de vida
    activity_level = Column(String)  # sedentary, light, moderate, active, very_active
    diet_type = Column(String)  # standard, vegetarian, vegan, keto, paleo, mediterranean
    health_conditions = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    
    # Preferências detalhadas
    preferences = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", secondary=user_goals, back_populates="users")
    
    @property
    def bmi(self):
        """Calculate BMI"""
        if self.weight and self.height:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 1)
        return None
    
    @property
    def daily_calories(self):
        """Calculate daily calorie needs using Harris-Benedict equation"""
        if not all([self.weight, self.height, self.age, self.gender]):
            return None
        
        # BMR calculation
        if self.gender.lower() == 'male':
            bmr = 88.362 + (13.397 * self.weight) + (4.799 * self.height) - (5.677 * self.age)
        else:
            bmr = 447.593 + (9.247 * self.weight) + (3.098 * self.height) - (4.330 * self.age)
        
        # Activity multiplier
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        tdee = bmr * activity_multipliers.get(self.activity_level, 1.2)
        
        # Adjust based on goals
        goals = [goal.name for goal in self.goals]
        if 'weight_loss' in goals:
            return round(tdee - 500)
        elif 'muscle_gain' in goals:
            return round(tdee + 300)
        else:
            return round(tdee)
    
    def to_dict(self):
        """Convert to dictionary (safe version without sensitive data)"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'age': self.age,
            'weight': self.weight,
            'height': self.height,
            'gender': self.gender,
            'body_fat': self.body_fat,
            'activity_level': self.activity_level,
            'diet_type': self.diet_type,
            'health_conditions': self.health_conditions,
            'allergies': self.allergies,
            'preferences': self.preferences,
            'bmi': self.bmi,
            'daily_calories': self.daily_calories,
            'goals': [goal.name for goal in self.goals],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # weight_loss, muscle_gain, maintenance, etc.
    description = Column(Text)
    category = Column(String)  # fitness, nutrition, health
    
    # Relationships
    users = relationship("User", secondary=user_goals, back_populates="goals")