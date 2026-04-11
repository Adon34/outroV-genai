# backend/app/agents/workout_agent.py
import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.agents.base_agent import BaseAgent
from app.agents.prompts import WORKOUT_AGENT_PROMPT
from app.agents.state import WorkoutRequest

logger = logging.getLogger(__name__)


class ModernWorkoutAgent(BaseAgent):
    """
    Agente especializado em criar planos de treino personalizados.
    
    Utiliza RAG service para buscar exercícios relevantes
    baseados no perfil e objetivos do usuário.
    """
    
    def __init__(self, llm: ChatOpenAI, db_session_factory, rag_service=None):
        super().__init__(llm, db_session_factory)
        self.rag_service = rag_service
    
    def get_prompt_template(self) -> ChatPromptTemplate:
        return WORKOUT_AGENT_PROMPT
    
    async def process(self, message: str, user_id: int, db=None) -> Dict[str, Any]:
        """Processa requisições de treino"""
        
        logger.info(f"WorkoutAgent processando mensagem para user {user_id}")
        
        try:
            # Busca conhecimento relevante via RAG
            knowledge_context = ""
            if self.rag_service:
                docs = await self.rag_service.get_relevant_knowledge(
                    query=message,
                    user_id=user_id,
                    k=4
                )
                if docs:
                    knowledge_context = "\n\n".join([
                        f"[{doc['metadata'].get('category', 'info')}]: {doc['content']}"
                        for doc in docs[:3]
                    ])
            
            # Recupera contexto do usuário
            user_context = await self._get_user_context(user_id, db)
            
            # Prepara e executa prompt
            prompt = self.get_prompt_template().format_messages(
                user_context=user_context or "Perfil não encontrado",
                knowledge_context=knowledge_context or "Nenhum conhecimento específico encontrado",
                chat_history="",
                input=message,
                messages=[]
            )
            
            # Gera resposta com streaming internamente
            response = await self._call_llm_with_retry(prompt)
            
            return self._format_response(
                message=response,
                metadata={
                    "knowledge_used": len(knowledge_context) > 0,
                    "sources": [doc.get("metadata", {}) for doc in docs[:2]] if docs else []
                }
            )
            
        except Exception as e:
            logger.error(f"Erro no WorkoutAgent: {e}", exc_info=True)
            return self._format_response(
                message="Desculpe, tive um problema ao gerar seu treino. Pode tentar novamente?",
                metadata={"error": str(e)}
            )
    
    async def _get_user_context(self, user_id: int, db) -> Optional[str]:
        """Recupera contexto do usuário via RAG service"""
        if self.rag_service:
            return await self.rag_service.get_user_context(user_id)
        return None