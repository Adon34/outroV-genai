# backend/app/agents/tools.py
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class UpdateProfileInput(BaseModel):
    """Schema para atualização de perfil"""
    user_id: int = Field(description="ID do usuário")
    field: str = Field(description="Campo a ser atualizado (peso, altura, idade, etc)")
    value: Any = Field(description="Novo valor")
    unit: Optional[str] = Field(default=None, description="Unidade de medida (kg, cm, anos)")


class CreateWorkoutInput(BaseModel):
    """Schema para criação de treino"""
    user_id: int = Field(description="ID do usuário")
    goal: str = Field(description="Objetivo do treino (perder peso, ganhar massa, etc)")
    duration_minutes: int = Field(default=45, description="Duração em minutos")
    equipment: List[str] = Field(default_factory=list, description="Equipamentos disponíveis")


class CreateDietInput(BaseModel):
    """Schema para criação de dieta"""
    user_id: int = Field(description="ID do usuário")
    goal: str = Field(description="Objetivo da dieta")
    meal_type: Optional[str] = Field(default=None, description="Tipo de refeição específica")
    calories_limit: Optional[int] = Field(default=None, description="Limite calórico")


# ============================================
# FERRAMENTAS (TOOLS)
# ============================================

@tool(args_schema=UpdateProfileInput)
async def update_user_profile_tool(
    user_id: int, 
    field: str, 
    value: Any, 
    unit: Optional[str] = None
) -> str:
    """
    Atualiza informações do perfil do usuário.
    Usar quando o usuário informar dados como peso, altura, idade, etc.
    """
    logger.info(f"Tool: Atualizando perfil do usuário {user_id}: {field}={value} {unit or ''}")
    
    # Aqui você implementaria a lógica de atualização no banco
    # Por enquanto, retorna confirmação
    return f"Perfil atualizado: {field} = {value} {unit or ''}".strip()


@tool(args_schema=CreateWorkoutInput)
async def create_workout_tool(
    user_id: int,
    goal: str,
    duration_minutes: int = 45,
    equipment: List[str] = None
) -> str:
    """
    Cria um plano de treino personalizado.
    Usar quando o usuário pedir sugestões de exercícios ou treinos.
    """
    logger.info(f"Tool: Criando treino para user {user_id}, objetivo: {goal}")
    
    equipment_str = f" com equipamentos: {', '.join(equipment)}" if equipment else ""
    
    # Retorna um placeholder - o agente principal vai processar
    return f"SOLICITACAO_TREINO|{user_id}|{goal}|{duration_minutes}|{equipment}"


@tool(args_schema=CreateDietInput)
async def create_diet_tool(
    user_id: int,
    goal: str,
    meal_type: Optional[str] = None,
    calories_limit: Optional[int] = None
) -> str:
    """
    Cria um plano alimentar ou sugere refeições.
    Usar quando o usuário pedir dieta, refeições, cardápio, etc.
    """
    logger.info(f"Tool: Criando dieta para user {user_id}, objetivo: {goal}")
    
    meal_info = f" para {meal_type}" if meal_type else ""
    calories_info = f" (limite: {calories_limit}kcal)" if calories_limit else ""
    
    return f"SOLICITACAO_DIETA|{user_id}|{goal}|{meal_type}|{calories_limit}"


@tool
async def get_user_stats_tool(user_id: int) -> str:
    """Recupera estatísticas e perfil do usuário"""
    logger.info(f"Tool: Buscando stats do usuário {user_id}")
    
    # Placeholder - implementar com DB real
    return f"STATS_USER_{user_id}|IMC: 22.5|Peso: 70kg|Altura: 175cm|Idade: 30"


@tool
async def search_knowledge_base_tool(query: str, category: Optional[str] = None) -> str:
    """Busca informações na base de conhecimento de nutrição e treinos"""
    logger.info(f"Tool: Buscando conhecimento: {query[:50]}...")
    
    # Placeholder - o RAG Service já faz isso
    return f"KNOWLEDGE_SEARCH|{query}"