# app/models.py - Adicione estas classes no final do arquivo

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.sql import func 
from app.database import Base

# ... (seus modelos existentes: User, Conversation, Message, etc.)
Base = declarative_base()

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
    age = Column(Integer)
    weight = Column(Float)
    height = Column(Float)
    gender = Column(String)
    body_fat = Column(Float, nullable=True)  # Adicionar se não existir
    activity_level = Column(String)
    fitness_goals = Column(JSON)
    health_conditions = Column(JSON)
    allergies = Column(JSON)
    preferences = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relacionamentos
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", secondary=user_goals, back_populates="users")
    
class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # weight_loss, muscle_gain, maintenance, etc.
    description = Column(Text)
    category = Column(String)  # fitness, nutrition, health
    
    # Relationships
    users = relationship("User", secondary=user_goals, back_populates="goals")
    
    
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    # CORREÇÃO: Renomear 'metadata' para 'meta_data' (evita conflito com SQLAlchemy)
    message_metadata = Column(JSON, nullable=True)  # Antigo 'metadata'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")


class Exercise(Base):
    """Modelo para exercícios"""
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    muscle_group = Column(String)  # peito, costas, perna, etc.
    equipment = Column(String)  # halter, máquina, peso corporal
    difficulty = Column(String)  # iniciante, intermediário, avançado
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    # workouts = relationship("Workout", back_populates="exercise")
    # workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")

class Workout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, nullable=True)  # em minutos
    calories_burned = Column(Float, nullable=True)
    exercises = Column(JSON, default=list)
    date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="workouts")

'''
class WorkoutExercise(Base):
    """Modelo para relação entre treino e exercício (com séries, reps)"""
    __tablename__ = "workout_exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    sets = Column(Integer, nullable=False)
    reps = Column(String, nullable=False)  # Pode ser "12", "10-12", "até a falha"
    weight = Column(Float, nullable=True)  # Carga usada (kg)
    rest_seconds = Column(Integer, default=60)
    order = Column(Integer, default=0)  # Ordem dos exercícios no treino
    notes = Column(Text)
    
    # Relacionamentos
    workout = relationship("Workout", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="workouts")
'''

class Meal(Base):
    __tablename__ = "meals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # ← nome correto: description
    meal_type = Column(String(50), nullable=True)
    calories = Column(Float, nullable=True)  # ← Float, não Integer
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fats = Column(Float, nullable=True)
    date = Column(DateTime, nullable=True)  # ← coluna date existe
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="meals")


class ProgressLog(Base):
    __tablename__ = "progress_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    weight = Column(Float, nullable=True)
    body_fat = Column(Float, nullable=True)
    muscle_mass = Column(Float, nullable=True)
    measurements = Column(JSON, default=dict)  # chest, waist, hips, etc.
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="progress_logs")
    