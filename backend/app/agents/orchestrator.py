# backend/app/agents/orchestrator.py
from enum import Enum
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint import MemorySaver
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from app.config import settings
from app.agents.state import AgentState, IntentResult
from app.agents.prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    FALLBACK_PROMPT
)
from app.agents.tools import (
    update_user_profile_tool,
    create_workout_tool,
    create_diet_tool,
    get_user_stats_tool
)

logger = logging.getLogger(__name__)


class AgentType(Enum):
    PROFILE = "profile"
    WORKOUT = "workout"
    DIET = "diet"
    CHAT = "chat"


class ModernOrchestrator:
    """
    Orquestrador moderno usando LangGraph para gestão de estado e fluxo.
    
    Características:
    - Graph-based execution com LangGraph
    - Structured output para classificação de intenção
    - Suporte a streaming e human-in-the-loop
    - Checkpointing para retomada de conversas
    """
    
    def __init__(self, llm: ChatOpenAI, db_session_factory, rag_service=None):
        self.llm = llm
        self.db_session_factory = db_session_factory
        self.rag_service = rag_service
        
        # Inicializa agents (serão criados sob demanda para evitar circular imports)
        self._profile_agent = None
        self._workout_agent = None
        self._diet_agent = None
        
        # Classificador de intenção com structured output
        self.intent_classifier = self.llm.with_structured_output(IntentResult)
        
        # MemorySaver para checkpointing (permite pausar/retomar conversas)
        self.checkpointer = MemorySaver()
        
        # Constrói o grafo de execução
        self.graph = self._build_graph()
        
        logger.info("ModernOrchestrator inicializado com LangGraph")
    
    @property
    def profile_agent(self):
        """Lazy loading do ProfileAgent para evitar circular imports"""
        if self._profile_agent is None:
            from app.agents.profile_agent import ModernProfileAgent
            self._profile_agent = ModernProfileAgent(self.llm, self.db_session_factory)
        return self._profile_agent
    
    @property
    def workout_agent(self):
        """Lazy loading do WorkoutAgent"""
        if self._workout_agent is None:
            from app.agents.workout_agent import ModernWorkoutAgent
            self._workout_agent = ModernWorkoutAgent(
                self.llm, 
                self.db_session_factory,
                self.rag_service
            )
        return self._workout_agent
    
    @property
    def diet_agent(self):
        """Lazy loading do DietAgent"""
        if self._diet_agent is None:
            from app.agents.diet_agent import ModernDietAgent
            self._diet_agent = ModernDietAgent(
                self.llm,
                self.db_session_factory,
                self.rag_service
            )
        return self._diet_agent
    
    def _build_graph(self) -> StateGraph:
        """
        Constrói o grafo de execução do agente.
        
        Fluxo:
        1. classify_intent -> decide rota
        2. Roteia para agente específico (profile/workout/diet/chat)
        3. Cada agente processa e retorna resposta
        4. Se precisar de mais info, loop; senão, finaliza
        """
        
        # Cria o grafo com o estado tipado
        workflow = StateGraph(AgentState)
        
        # Adiciona nós
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("profile_handler", self._profile_handler_node)
        workflow.add_node("workout_handler", self._workout_handler_node)
        workflow.add_node("diet_handler", self._diet_handler_node)
        workflow.add_node("chat_handler", self._chat_handler_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define o ponto de entrada
        workflow.set_entry_point("classify_intent")
        
        # Adiciona arestas condicionais baseadas na intenção
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "profile": "profile_handler",
                "workout": "workout_handler",
                "diet": "diet_handler",
                "chat": "chat_handler",
                "error": "error_handler"
            }
        )
        
        # Após cada handler, decide se continua ou finaliza
        workflow.add_conditional_edges(
            "profile_handler",
            self._should_continue,
            {
                "continue": "classify_intent",  # Loop para mais informações
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "workout_handler",
            self._should_continue,
            {
                "continue": "classify_intent",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "diet_handler",
            self._should_continue,
            {
                "continue": "classify_intent",
                "end": END
            }
        )
        
        workflow.add_edge("chat_handler", END)
        workflow.add_edge("error_handler", END)
        
        # Compila o grafo com checkpointing
        return workflow.compile(checkpointer=self.checkpointer)
    
    # ============================================
    # NÓS DO GRAFO
    # ============================================
    
    async def _classify_intent_node(self, state: AgentState) -> dict:
        """
        Classifica a intenção do usuário usando Structured Output.
        Este nó é o "cérebro" do orquestrador.
        """
        logger.info(f"Classificando intenção para user {state['user_id']}")
        
        # Pega a última mensagem do usuário
        last_message = state["messages"][-1] if state["messages"] else None
        if not last_message or not isinstance(last_message, HumanMessage):
            return {"current_intent": "CHAT", "confidence": 0.5}
        
        try:
            # Classificação com structured output
            result: IntentResult = await self.intent_classifier.ainvoke(
                INTENT_CLASSIFICATION_PROMPT.format(message=last_message.content)
            )
            
            logger.info(f"Intenção classificada: {result.intent} (confidence: {result.confidence})")
            
            return {
                "current_intent": result.intent,
                "confidence": result.confidence,
                "extracted_entities": result.entities,
                "needs_more_info": result.requires_clarification
            }
            
        except Exception as e:
            logger.error(f"Erro na classificação de intenção: {e}")
            return {
                "current_intent": "CHAT",
                "confidence": 0.3,
                "error": str(e)
            }
    
    async def _profile_handler_node(self, state: AgentState) -> dict:
        """Processa requisições relacionadas a perfil do usuário"""
        logger.info(f"Profile handler processando user {state['user_id']}")
        
        try:
            # Usa o ProfileAgent refatorado
            response = await self.profile_agent.process(
                message=state["messages"][-1].content,
                user_id=state["user_id"],
                db=None  # Será obtido via session factory
            )
            
            # Adiciona resposta ao estado
            new_messages = [AIMessage(content=response.get("message", ""))]
            
            return {
                "messages": new_messages,
                "final_response": response.get("message"),
                "iteration": state.get("iteration", 0) + 1
            }
            
        except Exception as e:
            logger.error(f"Erro no profile handler: {e}")
            return {
                "messages": [AIMessage(content="Desculpe, tive um problema ao processar seu perfil.")],
                "error": str(e)
            }
    
    async def _workout_handler_node(self, state: AgentState) -> dict:
        """Processa requisições de treino"""
        logger.info(f"Workout handler processando user {state['user_id']}")
        
        try:
            response = await self.workout_agent.process(
                message=state["messages"][-1].content,
                user_id=state["user_id"],
                db=None
            )
            
            return {
                "messages": [AIMessage(content=response.get("message", ""))],
                "final_response": response.get("message"),
                "iteration": state.get("iteration", 0) + 1
            }
            
        except Exception as e:
            logger.error(f"Erro no workout handler: {e}")
            return {
                "messages": [AIMessage(content="Desculpe, tive um problema ao gerar seu treino.")],
                "error": str(e)
            }
    
    async def _diet_handler_node(self, state: AgentState) -> dict:
        """Processa requisições de dieta"""
        logger.info(f"Diet handler processando user {state['user_id']}")
        
        try:
            response = await self.diet_agent.process(
                message=state["messages"][-1].content,
                user_id=state["user_id"],
                db=None
            )
            
            return {
                "messages": [AIMessage(content=response.get("message", ""))],
                "final_response": response.get("message"),
                "iteration": state.get("iteration", 0) + 1
            }
            
        except Exception as e:
            logger.error(f"Erro no diet handler: {e}")
            return {
                "messages": [AIMessage(content="Desculpe, tive um problema ao preparar sua dieta.")],
                "error": str(e)
            }
    
    async def _chat_handler_node(self, state: AgentState) -> dict:
        """Processa conversa geral usando RAG service"""
        logger.info(f"Chat handler processando user {state['user_id']}")
        
        if not self.rag_service:
            fallback_response = "Olá! Posso ajudar com treinos, dieta ou atualizar seu perfil. O que você precisa?"
            return {
                "messages": [AIMessage(content=fallback_response)],
                "final_response": fallback_response
            }
        
        try:
            # Usa o RAG Service refatorado
            response = await self.rag_service.generate_response(
                user_id=state["user_id"],
                message=state["messages"][-1].content,
                conversation_history=[
                    {"role": "user" if isinstance(m, HumanMessage) else "assistant", 
                     "content": m.content}
                    for m in state["messages"][-5:]  # Últimas 5 mensagens
                ]
            )
            
            return {
                "messages": [AIMessage(content=response.get("answer", ""))],
                "final_response": response.get("answer"),
                "relevant_docs": response.get("sources", [])
            }
            
        except Exception as e:
            logger.error(f"Erro no chat handler: {e}")
            return {
                "messages": [AIMessage(content="Desculpe, não entendi. Pode reformular sua pergunta?")],
                "error": str(e)
            }
    
    async def _error_handler_node(self, state: AgentState) -> dict:
        """Trata erros e fallbacks"""
        logger.error(f"Error handler ativado: {state.get('error', 'Erro desconhecido')}")
        
        fallback_message = "Desculpe, tive um problema. Pode repetir sua pergunta?"
        
        return {
            "messages": [AIMessage(content=fallback_message)],
            "final_response": fallback_message,
            "error": None  # Limpa o erro após tratamento
        }
    
    # ============================================
    # FUNÇÕES DE ROTEAMENTO
    # ============================================
    
    def _route_by_intent(self, state: AgentState) -> str:
        """Decide para qual nó ir baseado na intenção classificada"""
        intent = state.get("current_intent", "CHAT")
        confidence = state.get("confidence", 0.5)
        
        # Se confiança muito baixa, vai para chat handler (fallback)
        if confidence < 0.4:
            logger.warning(f"Baixa confiança ({confidence}), usando fallback")
            return "chat"
        
        # Mapeia intenção para nome do handler
        intent_map = {
            "PROFILE": "profile",
            "WORKOUT": "workout",
            "DIET": "diet",
            "CHAT": "chat"
        }
        
        return intent_map.get(intent, "chat")
    
    def _should_continue(self, state: AgentState) -> str:
        """
        Decide se o agente precisa de mais iterações.
        Usado para coletar informações adicionais do usuário.
        """
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)
        needs_more_info = state.get("needs_more_info", False)
        
        if needs_more_info and iteration < max_iterations:
            logger.info(f"Continuação necessária (iteração {iteration + 1}/{max_iterations})")
            return "continue"
        
        return "end"
    
    # ============================================
    # MÉTODOS PÚBLICOS
    # ============================================
    
    async def process_message(
        self,
        message: str,
        user_id: int,
        chat_history: List[Dict] = None,
        db = None,
        thread_id: str = None
    ) -> Dict[str, Any]:
        """
        Processa uma mensagem e retorna resposta.
        
        Args:
            message: Mensagem do usuário
            user_id: ID do usuário
            chat_history: Histórico da conversa (opcional)
            db: Sessão do banco (opcional)
            thread_id: ID da thread para checkpointing (opcional)
        """
        
        # Constrói o estado inicial
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "current_intent": None,
            "confidence": 0.0,
            "extracted_entities": {},
            "user_context": None,
            "relevant_docs": [],
            "needs_more_info": False,
            "iteration": 0,
            "max_iterations": 3,
            "final_response": None,
            "error": None,
            "start_time": datetime.utcnow()
        }
        
        # Configura checkpoint (permite retomar conversas)
        config = {"configurable": {"thread_id": thread_id or f"user_{user_id}"}}
        
        try:
            # Executa o grafo
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            return {
                "action": final_state.get("current_intent", "CHAT").lower(),
                "message": final_state.get("final_response", ""),
                "sources": final_state.get("relevant_docs", []),
                "confidence": final_state.get("confidence", 0.0),
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Erro na execução do grafo: {e}", exc_info=True)
            return {
                "action": "error",
                "message": "Desculpe, ocorreu um erro inesperado. Por favor, tente novamente.",
                "error": str(e),
                "user_id": user_id
            }
    
    async def process_message_streaming(
        self,
        message: str,
        user_id: int,
        chat_history: List[Dict] = None,
        thread_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Processa mensagem com streaming para experiência em tempo real.
        
        Yields eventos parciais da execução do grafo.
        """
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "current_intent": None,
            "confidence": 0.0,
            "extracted_entities": {},
            "user_context": None,
            "relevant_docs": [],
            "needs_more_info": False,
            "iteration": 0,
            "max_iterations": 3,
            "final_response": None,
            "error": None,
            "start_time": datetime.utcnow()
        }
        
        config = {"configurable": {"thread_id": thread_id or f"user_{user_id}"}}
        
        try:
            # Stream dos eventos do grafo
            async for event in self.graph.astream(initial_state, config=config):
                # Cada evento contém mudanças no estado
                for node_name, node_state in event.items():
                    yield {
                        "type": "node_complete",
                        "node": node_name,
                        "partial_response": node_state.get("messages", [None])[-1].content if node_state.get("messages") else None,
                        "intent": node_state.get("current_intent")
                    }
                    
        except Exception as e:
            logger.error(f"Erro no streaming: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def get_conversation_state(self, thread_id: str) -> Optional[AgentState]:
        """Recupera o estado de uma conversa anterior (checkpoint)"""
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            state = await self.graph.aget_state(config)
            return state.values if state else None
        except Exception as e:
            logger.error(f"Erro ao recuperar estado: {e}")
            return None
    
    async def reset_conversation(self, thread_id: str) -> bool:
        """Reseta uma conversa (limpa checkpoint)"""
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            await self.graph.aclear(config)
            logger.info(f"Conversa resetada: {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao resetar conversa: {e}")
            return False