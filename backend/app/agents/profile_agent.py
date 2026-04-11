# backend/app/agents/profile_agent.py
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.prompts import PROFILE_AGENT_PROMPT
from app.agents.state import ProfileUpdate

logger = logging.getLogger(__name__)


class ProfileUpdateResult(BaseModel):
    """Resposta estruturada para atualização de perfil"""
    success: bool
    updated_fields: Dict[str, Any] = Field(default_factory=dict)
    message: str
    needs_more_info: bool = False
    missing_fields: list = Field(default_factory=list)


class ModernProfileAgent(BaseAgent):
    """
    Agente especializado em gerenciar perfil do usuário.
    
    Funcionalidades:
    - Atualização de dados (peso, altura, idade, etc)
    - Cálculo de IMC
    - Identificação de informações faltantes
    """
    
    def __init__(self, llm: ChatOpenAI, db_session_factory):
        super().__init__(llm, db_session_factory)
        
        # Structured output para respostas garantidas
        self.structured_llm = self.llm.with_structured_output(ProfileUpdateResult)
        
    def get_prompt_template(self) -> ChatPromptTemplate:
        return PROFILE_AGENT_PROMPT
    
    async def process(self, message: str, user_id: int, db=None) -> Dict[str, Any]:
        """Processa mensagens relacionadas ao perfil"""
        
        logger.info(f"ProfileAgent processando mensagem para user {user_id}")
        
        try:
            # Recupera contexto atual do usuário
            user_context = await self._get_user_context_from_db(user_id, db)
            
            # Prepara o prompt
            prompt = self.get_prompt_template().format_messages(
                user_context=user_context or "Perfil não encontrado",
                chat_history="",  # Poderia vir do histórico
                input=message,
                messages=[]
            )
            
            # Invoca o LLM com structured output
            result: ProfileUpdateResult = await self.structured_llm.ainvoke(prompt)
            
            # Se atualizou campos, persiste no banco
            if result.success and result.updated_fields:
                await self._persist_profile_update(user_id, result.updated_fields, db)
            
            # Se precisa de mais informações, prepara pergunta
            if result.needs_more_info and result.missing_fields:
                follow_up = self._generate_follow_up_question(result.missing_fields)
                return self._format_response(
                    message=follow_up,
                    metadata={"needs_more_info": True, "missing_fields": result.missing_fields}
                )
            
            return self._format_response(
                message=result.message,
                metadata={"updated_fields": result.updated_fields, "success": result.success}
            )
            
        except Exception as e:
            logger.error(f"Erro no ProfileAgent: {e}", exc_info=True)
            return self._format_response(
                message="Desculpe, tive um problema ao processar seu perfil. Pode tentar novamente?",
                metadata={"error": str(e)}
            )
    
    async def _get_user_context_from_db(self, user_id: int, db) -> Optional[str]:
        """Recupera contexto do banco de dados"""
        # Implementar com sua lógica de DB
        # Placeholder
        return None
    
    async def _persist_profile_update(self, user_id: int, updates: Dict, db):
        """Persiste atualizações no banco"""
        logger.info(f"Persistindo atualizações para user {user_id}: {updates}")
        # Implementar com sua lógica de DB
    
    def _generate_follow_up_question(self, missing_fields: list) -> str:
        """Gera pergunta educada para informações faltantes"""
        if not missing_fields:
            return "Tudo certo com seu perfil!"
        
        field_names = {
            "weight": "peso",
            "height": "altura",
            "age": "idade",
            "gender": "gênero",
            "activity_level": "nível de atividade física"
        }
        
        missing_names = [field_names.get(f, f) for f in missing_fields]
        
        if len(missing_names) == 1:
            return f"Para personalizar melhor, poderia me informar seu {missing_names[0]}?"
        else:
            return f"Para um acompanhamento mais preciso, poderia me informar: {', '.join(missing_names)}?"