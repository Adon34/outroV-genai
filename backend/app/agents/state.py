# backend/app/agents/state.py
from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field
import operator

# ============================================
# ESTADOS PARA LANGGRAPH
# ============================================

class AgentState(TypedDict):
    """
    Estado principal do agente - usado pelo LangGraph
    O campo 'messages' é anotado com operator.add para acumular mensagens
    """
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: int
    current_intent: Optional[str]
    confidence: float
    extracted_entities: Dict[str, Any]
    user_context: Optional[str]
    relevant_docs: List[Dict]
    needs_more_info: bool
    iteration: int
    max_iterations: int
    final_response: Optional[str]
    error: Optional[str]
    start_time: Optional[datetime]


class IntentResult(BaseModel):
    """Resultado da classificação de intenção - Structured Output"""
    intent: Literal["PROFILE", "WORKOUT", "DIET", "CHAT"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confiança da classificação")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entidades extraídas")
    requires_clarification: bool = Field(default=False, description="Precisa de mais informações")
    clarification_question: Optional[str] = Field(default=None, description="Pergunta para clarificação")


class ProfileUpdate(BaseModel):
    """Dados para atualização de perfil"""
    field: str
    value: Any
    confidence: float
    requires_confirmation: bool = False


class WorkoutRequest(BaseModel):
    """Requisição de treino estruturada"""
    goal: Optional[str] = None
    difficulty: Literal["iniciante", "intermediario", "avancado"] = "intermediario"
    duration_minutes: int = 45
    equipment_available: List[str] = Field(default_factory=list)
    focus_areas: List[str] = Field(default_factory=list)
    injuries: List[str] = Field(default_factory=list)


class DietRequest(BaseModel):
    """Requisição de dieta estruturada"""
    goal: Optional[str] = None
    meal_type: Optional[Literal["cafe", "almoco", "jantar", "lanche"]] = None
    calories_target: Optional[int] = None
    restrictions: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)