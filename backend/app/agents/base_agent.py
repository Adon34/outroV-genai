# backend/app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Classe base para todos os agents especializados.
    
    Implementa funcionalidades comuns:
    - Cache de contexto
    - Tratamento de erros
    - Logging estruturado
    """
    
    def __init__(self, llm: ChatOpenAI, db_session_factory):
        self.llm = llm
        self.db_session_factory = db_session_factory
        self._cache = {}
        
    @abstractmethod
    def get_prompt_template(self) -> ChatPromptTemplate:
        """Retorna o prompt template específico do agente"""
        pass
    
    @abstractmethod
    async def process(self, message: str, user_id: int, db=None) -> Dict[str, Any]:
        """Processa a mensagem e retorna resposta"""
        pass
    
    async def _get_user_context(self, user_id: int, db) -> Optional[str]:
        """Recupera contexto do usuário (pode ser sobrescrito)"""
        # Implementação padrão - será integrada com RAG Service
        return None
    
    async def _call_llm_with_retry(self, prompt: str, max_retries: int = 2) -> str:
        """Chama o LLM com retry automático"""
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke(prompt)
                return response.content
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                if attempt == max_retries - 1:
                    raise
        return "Desculpe, não consegui processar sua solicitação."
    
    def _format_response(self, message: str, metadata: Dict = None) -> Dict[str, Any]:
        """Formata a resposta padronizada"""
        return {
            "message": message,
            "metadata": metadata or {},
            "agent": self.__class__.__name__
        }