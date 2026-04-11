# backend/app/agents/__init__.py
from app.agents.orchestrator import ModernOrchestrator
from app.agents.profile_agent import ModernProfileAgent
from app.agents.workout_agent import ModernWorkoutAgent
from app.agents.diet_agent import ModernDietAgent
from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState, IntentResult
from app.agents.tools import (
    update_user_profile_tool,
    create_workout_tool,
    create_diet_tool
)

__all__ = [
    "ModernOrchestrator",
    "ModernProfileAgent", 
    "ModernWorkoutAgent",
    "ModernDietAgent",
    "BaseAgent",
    "AgentState",
    "IntentResult",
    "update_user_profile_tool",
    "create_workout_tool",
    "create_diet_tool",
    "WorkoutAgent",
    "DietAgent"

]   