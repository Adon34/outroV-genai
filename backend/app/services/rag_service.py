# backend/app/services/rag_service.py
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import openai
import logging
import hashlib
from datetime import datetime, timedelta

from app.config import settings
from app.utils.cache import cache

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.chroma_host = settings.CHROMA_HOST
        self.chroma_port = settings.CHROMA_PORT
        self.collection_name = "diet_training_knowledge"
        self.user_context_collection = "user_contexts"
        
        # Initialize OpenAI
        openai.api_key = self.openai_api_key
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.HttpClient(
            host=self.chroma_host,
            port=self.chroma_port,
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=self.openai_api_key,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=settings.OPENAI_MODEL,
            temperature=0.7,
            max_tokens=500,
            openai_api_key=self.openai_api_key
        )
        
        # Text splitter for documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Prompt template for personalization
        self.prompt_template = PromptTemplate(
            input_variables=["context", "user_profile", "question", "chat_history"],
            template="""Você é um assistente especializado em nutrição e treinos físicos, focado em ajudar usuários a alcançar seus objetivos de saúde e fitness de forma personalizada e realista.

CONTEXTO DO CONHECIMENTO GERAL:
{context}

PERFIL DO USUÁRIO:
{user_profile}

HISTÓRICO DA CONVERSA:
{chat_history}

PERGUNTA DO USUÁRIO: {question}

INSTRUÇÕES:
1. Use o conhecimento geral e o perfil do usuário para dar respostas personalizadas
2. Considere as limitações, objetivos e preferências do usuário
3. Seja prático e dê exemplos concretos
4. Se não souber algo, admita e sugira consultar um profissional
5. Mantenha um tom motivador e encorajador
6. Sugestões devem ser realistas para a rotina do usuário

RESPOSTA PERSONALIZADA:"""
        )
        
    async def initialize(self):
        """Initialize the RAG system"""
        try:
            # Create or get collections
            await self._init_knowledge_base()
            await self._init_user_contexts()
            
            # Load base knowledge
            await self.load_base_knowledge()
            
            logger.info("RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing RAG Service: {e}")
            raise
    
    async def _init_knowledge_base(self):
        """Initialize knowledge base collection"""
        try:
            # Try to get existing collection
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
        except:
            # Create new collection
            self.vectorstore = Chroma.from_documents(
                documents=[],
                embedding=self.embeddings,
                client=self.chroma_client,
                collection_name=self.collection_name
            )
    
    async def _init_user_contexts(self):
        """Initialize user contexts collection"""
        try:
            self.user_context_store = Chroma(
                client=self.chroma_client,
                collection_name=self.user_context_collection,
                embedding_function=self.embeddings
            )
        except:
            self.user_context_store = Chroma.from_documents(
                documents=[],
                embedding=self.embeddings,
                client=self.chroma_client,
                collection_name=self.user_context_collection
            )
    
    async def load_base_knowledge(self):
        """Load base knowledge from JSON files"""
        knowledge_files = [
            "nutrition.json",
            "workouts.json",
            "health.json"
        ]
        
        base_path = os.path.join(os.path.dirname(__file__), "..", "rag", "knowledge_base")
        
        for filename in knowledge_files:
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    await self._process_knowledge_file(data)
    
    async def _process_knowledge_file(self, data: Dict):
        """Process a knowledge file and add to vector store"""
        for category, items in data.items():
            for item in items:
                content = item.get("content", "")
                metadata = {
                    "category": category,
                    "subcategory": item.get("subcategory", ""),
                    "source": item.get("source", "base_knowledge"),
                    "tags": json.dumps(item.get("tags", []))
                }
                
                # Split into chunks
                chunks = self.text_splitter.split_text(content)
                
                # Add each chunk
                texts = []
                metadatas = []
                for i, chunk in enumerate(chunks):
                    texts.append(chunk)
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk"] = i
                    metadatas.append(chunk_metadata)
                
                if texts:
                    await self.vectorstore.aadd_texts(texts, metadatas)
    
    async def add_user_context(self, user_id: int, user_data: Dict[str, Any]):
        """Add or update user context"""
        try:
            # Create context string
            context_str = self._format_user_context(user_data)

            # Create document
            doc_id = f"user_context_{user_id}"
            metadata = {
                "type": "user_context",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add to user context collection
            await self.user_context_store.aadd_texts(
                texts=[context_str],
                metadatas=[metadata],
                ids=[doc_id]
            )

            logger.info(f"Added user context for user {user_id}")

        except Exception as e:
            logger.error(f"Error adding user context: {e}")
            raise
        
# backend/app/services/rag_service.py (continuação)

    def _format_user_context(self, user_data: Dict[str, Any]) -> str:
        """Format user data into context string"""
        goals = user_data.get('goals', [])
        health_conditions = user_data.get('health_conditions', [])
        allergies = user_data.get('allergies', [])
        preferences = user_data.get('preferences', {})
        
        context = f"""
PERFIL DO USUÁRIO:
- ID: {user_data.get('id')}
- Idade: {user_data.get('age')} anos
- Peso: {user_data.get('weight')} kg
- Altura: {user_data.get('height')} cm
- Gênero: {user_data.get('gender')}
- IMC: {user_data.get('bmi')}
- Nível de atividade: {user_data.get('activity_level')}
- Tipo de dieta: {user_data.get('diet_type')}

OBJETIVOS:
{', '.join(goals) if goals else 'Manutenção da saúde'}

CONDIÇÕES DE SAÚDE:
{', '.join(health_conditions) if health_conditions else 'Nenhuma condição reportada'}

ALERGIAS/RESTRIÇÕES:
{', '.join(allergies) if allergies else 'Nenhuma alergia reportada'}

PREFERÊNCIAS:
- Alimentares: {', '.join(preferences.get('food_preferences', [])) if preferences.get('food_preferences') else 'Sem preferências específicas'}
- Treinos: {', '.join(preferences.get('workout_preferences', [])) if preferences.get('workout_preferences') else 'Sem preferências específicas'}
- Tempo disponível: {preferences.get('available_time', 'Não especificado')} minutos/dia

NECESSIDADES CALÓRICAS:
- Calorias diárias recomendadas: {user_data.get('daily_calories')} kcal
"""
        return context

    async def get_user_context(self, user_id: int) -> str:
        """Retrieve user context from vector store"""
        try:
            # Try cache first
            cache_key = f"user_context:{user_id}"
            cached = await cache.get(cache_key)
            if cached:
                return cached
            
            # Search in vector store
            results = self.user_context_store.similarity_search(
                query=f"user_id:{user_id}",
                k=1,
                filter={"user_id": user_id}
            )
            
            if results:
                context = results[0].page_content
                # Cache for 1 hour
                await cache.set(cache_key, context, expires=3600)
                return context
            
            return "Contexto do usuário não encontrado"
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return "Erro ao recuperar contexto"

    async def get_relevant_knowledge(self, query: str, user_id: Optional[int] = None, k: int = 5) -> List[Dict]:
        """Get relevant knowledge from vector store"""
        try:
            # Search filters
            filter_dict = {}
            if user_id:
                filter_dict = {"user_id": user_id}
            
            # Search for similar documents
            results = self.vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict
            )
            
            documents = []
            for doc, score in results:
                if score > 0.7:  # Relevance threshold
                    documents.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance": score
                    })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}")
            return []

    async def generate_response(
        self,
        user_id: int,
        message: str,
        conversation_history: List[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate personalized response"""
        try:
            # Check cache if enabled
            if use_cache:
                cache_key = f"response:{user_id}:{hashlib.md5(message.encode()).hexdigest()}"
                cached = await cache.get(cache_key)
                if cached:
                    return cached
            
            # Get user context
            user_context = await self.get_user_context(user_id)
            
            # Get relevant knowledge
            relevant_docs = await self.get_relevant_knowledge(message, user_id)
            knowledge_context = "\n\n".join([doc["content"] for doc in relevant_docs])
            
            # Format chat history
            history_text = ""
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    role = "Usuário" if msg["role"] == "user" else "Assistente"
                    history_text += f"{role}: {msg['content']}\n"
            
            # Create prompt
            prompt = self.prompt_template.format(
                context=knowledge_context,
                user_profile=user_context,
                question=message,
                chat_history=history_text
            )
            
            # Generate response
            response = await self.llm.apredict(prompt)
            
            # Prepare result
            result = {
                "answer": response,
                "sources": [
                    {
                        "category": doc["metadata"].get("category"),
                        "relevance": doc["relevance"]
                    }
                    for doc in relevant_docs
                ],
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache response (1 hour)
            if use_cache:
                await cache.set(cache_key, result, expires=3600)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": "Desculpe, tive um problema ao processar sua pergunta. Pode reformular?",
                "error": str(e),
                "user_id": user_id
            }

    async def add_feedback(self, user_id: int, message_id: str, feedback: str):
        """Add user feedback to improve responses"""
        try:
            feedback_doc = {
                "content": f"Feedback do usuário {user_id}: {feedback}",
                "metadata": {
                    "type": "feedback",
                    "user_id": user_id,
                    "message_id": message_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            await self.add_document(
                content=feedback_doc["content"],
                metadata=feedback_doc["metadata"]
            )
            
        except Exception as e:
            logger.error(f"Error adding feedback: {e}")

    async def close(self):
        """Close connections"""
        try:
            # Cleanup if needed
            pass
        except Exception as e:
            logger.error(f"Error closing RAG service: {e}")