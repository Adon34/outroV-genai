# backend/app/models/schemas.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

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

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)  # user, assistant, system
    content = Column(Text)
    message_metadata = Column(JSON, default={})  # tokens, model, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

class Meal(Base):
    __tablename__ = "meals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(Text)
    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fats = Column(Float)
    meal_type = Column(String)  # breakfast, lunch, dinner, snack
    date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="meals")

class Workout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(Text)
    duration = Column(Integer)  # in minutes
    calories_burned = Column(Float)
    exercises = Column(JSON, default=[])  # list of exercises with sets/reps
    date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="workouts")

class ProgressLog(Base):
    __tablename__ = "progress_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    weight = Column(Float)
    body_fat = Column(Float, nullable=True)
    measurements = Column(JSON, default={})  # chest, waist, hips, etc.
    mood = Column(Integer)  # 1-10
    energy_level = Column(Integer)  # 1-10
    sleep_hours = Column(Float)
    notes = Column(Text)
    date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="progress_logs")

class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # weight_loss, muscle_gain, maintenance, etc.
    description = Column(Text)
    category = Column(String)  # fitness, nutrition, health
    
    # Relationships
    users = relationship("User", secondary=user_goals, back_populates="goals")