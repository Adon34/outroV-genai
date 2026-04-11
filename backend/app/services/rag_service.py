# backend/app/services/rag_service.py
import os
import json
import hashlib
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from app.config import settings
from app.utils.cache import cache

logger = logging.getLogger(__name__)


class RAGResponse(BaseModel):
    """Resposta estruturada do RAG"""
    answer: str = Field(description="Resposta personalizada para o usuário")
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    requires_professional: bool = Field(default=False)


class UserContext(BaseModel):
    """Estrutura tipada do contexto do usuário"""
    user_id: int
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    gender: Optional[str] = None
    bmi: Optional[float] = None
    activity_level: Optional[str] = None
    diet_type: Optional[str] = None
    goals: List[str] = Field(default_factory=list)
    health_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    daily_calories: Optional[int] = None


class RAGService:
    """
    Serviço RAG usando API direta do ChromaDB (sem LangChain wrapper problemático)
    """
    
    def __init__(self):
        """Inicializa o RAG Service"""
        
        self.openai_api_key = settings.OPENAI_API_KEY
        self.chroma_host = settings.CHROMA_HOST
        self.chroma_port = settings.CHROMA_PORT
        self.collection_name = "diet_training_knowledge"
        self.user_context_collection = "user_contexts"
        
        # ========================================
        # 1. INICIALIZAÇÃO DO CHROMADB
        # ========================================
        self.chroma_client = None
        self._init_chromadb()
        
        # ========================================
        # 2. MODELOS LLM E EMBEDDINGS
        # ========================================
        
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            max_tokens=500,
            timeout=30,
            max_retries=2,
            streaming=True,
            openai_api_key=self.openai_api_key
        )
        
        # Embeddings para ChromaDB (API direta)
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name=settings.OPENAI_EMBEDDING_MODEL
        )
        
        # LangChain embeddings para outros usos
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=self.openai_api_key,
            chunk_size=100,
            max_retries=3
        )
        
        # ========================================
        # 3. TEXT SPLITTER
        # ========================================
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            add_start_index=True
        )
        
        # ========================================
        # 4. COLLECTIONS (API direta)
        # ========================================
        self.knowledge_collection = None
        self.context_collection = None
        
        logger.info("RAG Service inicializado")
    
    def _init_chromadb(self):
        """Inicializa conexão com ChromaDB"""
        try:
            self.chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            self.chroma_client.heartbeat()
            logger.info(f"Conectado ao ChromaDB em {self.chroma_host}:{self.chroma_port}")
        except Exception as e:
            logger.warning(f"Falha ao conectar ao ChromaDB remoto: {e}. Usando persistência local.")
            self.chroma_client = chromadb.PersistentClient(
                path="./chroma_db",
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
    
    async def initialize(self):
        """Inicializa o sistema RAG"""
        try:
            # Obtém ou cria coleções usando API direta
            self.knowledge_collection = await self._get_or_create_collection(
                self.collection_name,
                "Base de conhecimento de nutrição e treinos"
            )
            
            self.context_collection = await self._get_or_create_collection(
                self.user_context_collection,
                "Contextos personalizados dos usuários"
            )
            
            # Carrega conhecimento base se a coleção estiver vazia
            if self.knowledge_collection.count() == 0:
                await self.load_base_knowledge()
            else:
                logger.info(f"Coleção já possui {self.knowledge_collection.count()} documentos")
            
            logger.info("RAG Service inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na inicialização: {e}", exc_info=True)
            raise
    
    async def _get_or_create_collection(self, name: str, description: str):
        """Obtém ou cria uma coleção de forma segura"""
        try:
            # Tenta obter coleção existente
            collection = self.chroma_client.get_collection(name)
            logger.info(f"Coleção '{name}' obtida com sucesso")
            return collection
        except Exception as e:
            # Coleção não existe, cria nova
            logger.info(f"Criando coleção '{name}': {description}")
            collection = self.chroma_client.create_collection(
                name=name,
                metadata={"description": description, "hnsw:space": "cosine"}
            )
            return collection
    
    async def load_base_knowledge(self):
        """Carrega arquivos JSON de conhecimento base"""
        base_path = Path(__file__).parent.parent / "rag" / "knowledge_base"
        
        if not base_path.exists():
            logger.warning(f"Diretório de conhecimento não encontrado: {base_path}")
            return
        
        knowledge_files = ["nutrition.json", "workouts.json", "health.json"]
        all_chunks = []
        
        for filename in knowledge_files:
            filepath = base_path / filename
            if not filepath.exists():
                logger.warning(f"Arquivo não encontrado: {filepath}")
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    chunks = self._process_knowledge_file(data, filename)
                    all_chunks.extend(chunks)
                    logger.info(f"Processado {filename}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Erro ao processar {filename}: {e}")
        
        if all_chunks:
            await self._add_chunks_batch(all_chunks)
            logger.info(f"Total de {len(all_chunks)} chunks adicionados")
    
    def _process_knowledge_file(self, data: Dict, source_file: str) -> List[Dict]:
        """Processa arquivo de conhecimento e retorna lista de chunks"""
        chunks = []
        
        for category, items in data.items():
            if not isinstance(items, list):
                continue
                
            for item in items:
                content = item.get("content", "")
                if not content:
                    continue
                
                metadata = {
                    "category": category,
                    "subcategory": item.get("subcategory", ""),
                    "source": source_file,
                    "tags": json.dumps(item.get("tags", [])),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Divide em chunks
                text_chunks = self.text_splitter.split_text(content)
                
                for i, chunk in enumerate(text_chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["total_chunks"] = len(text_chunks)
                    
                    chunks.append({
                        "text": chunk,
                        "metadata": chunk_metadata
                    })
        
        return chunks
    
    async def _add_chunks_batch(self, chunks: List[Dict], batch_size: int = 500):
        """Adiciona chunks em batch usando API direta do ChromaDB"""
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            texts = [chunk["text"] for chunk in batch]
            metadatas = [chunk["metadata"] for chunk in batch]
            
            # Gera IDs únicos
            ids = []
            for text in texts:
                hash_id = hashlib.md5(text.encode()).hexdigest()[:16]
                ids.append(f"doc_{i}_{hash_id}")
            
            # Adiciona usando API síncrona em thread pool
            await asyncio.to_thread(
                self.knowledge_collection.add,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.debug(f"Batch {i//batch_size + 1} adicionado: {len(batch)} chunks")
    
    # ============================================
    # MÉTODOS DE CONTEXTO DO USUÁRIO
    # ============================================
    
    async def add_user_context(self, user_id: int, user_data: Dict[str, Any]):
        """Adiciona ou atualiza o contexto do usuário"""
        try:
            validated_context = UserContext(**user_data)
            context_str = self._format_user_context(validated_context)
            
            doc_id = f"user_context_{user_id}"
            metadata = {
                "type": "user_context",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Remove documento antigo
            try:
                existing = self.context_collection.get(where={"user_id": user_id})
                if existing['ids']:
                    await asyncio.to_thread(self.context_collection.delete, ids=existing['ids'])
            except Exception as e:
                logger.warning(f"Erro ao remover contexto antigo: {e}")
            
            # Adiciona novo contexto
            await asyncio.to_thread(
                self.context_collection.add,
                documents=[context_str],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            await cache.delete(f"user_context:{user_id}")
            logger.info(f"Contexto atualizado para usuário {user_id}")
            
            return validated_context
            
        except Exception as e:
            logger.error(f"Erro ao adicionar contexto: {e}")
            raise
    
    def _format_user_context(self, context: UserContext) -> str:
        """Formata o contexto como string"""
        lines = [
            f"PERFIL DO USUÁRIO (ID: {context.user_id})",
            "-" * 50,
            f"Idade: {context.age or 'Não informado'} anos",
            f"Peso: {context.weight or 'Não informado'} kg",
            f"Altura: {context.height or 'Não informado'} cm",
            f"Gênero: {context.gender or 'Não informado'}",
            f"IMC: {context.bmi or 'Não calculado'}",
            f"Nível de atividade: {context.activity_level or 'Não informado'}",
            "",
            f"OBJETIVOS: {', '.join(context.goals) if context.goals else 'Manutenção da saúde'}",
            "",
            f"CONDIÇÕES DE SAÚDE: {', '.join(context.health_conditions) if context.health_conditions else 'Nenhuma'}",
            "",
            f"ALERGIAS: {', '.join(context.allergies) if context.allergies else 'Nenhuma'}",
        ]
        return "\n".join(lines)
    
    async def get_user_context(self, user_id: int) -> str:
        """Recupera o contexto do usuário"""
        cache_key = f"user_context:{user_id}"
        
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        try:
            results = await asyncio.to_thread(
                self.context_collection.get,
                where={"user_id": user_id},
                limit=1
            )
            
            if results and results['documents']:
                context = results['documents'][0]
                await cache.set(cache_key, context, expires=3600)
                return context
                
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {e}")
        
        return "Perfil do usuário não encontrado."
    
    # ============================================
    # MÉTODO DE BUSCA
    # ============================================
    
    async def get_relevant_knowledge(
        self, 
        query: str, 
        user_id: Optional[int] = None, 
        k: int = 5
    ) -> List[Dict]:
        """Busca conhecimento relevante usando API direta do ChromaDB"""
        if not self.knowledge_collection:
            return []
        
        try:
            # Query com embedding
            results = await asyncio.to_thread(
                self.knowledge_collection.query,
                query_texts=[query],
                n_results=k
            )
            
            documents = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    # Converte distância para similaridade (quanto menor a distância, maior a similaridade)
                    similarity = 1.0 - distance
                    
                    if similarity > 0.7:
                        documents.append({
                            "content": doc,
                            "metadata": metadata,
                            "relevance": similarity
                        })
            
            return documents
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
    
    # ============================================
    # GERAÇÃO DE RESPOSTA
    # ============================================
    
    async def generate_response(
        self,
        user_id: int,
        message: str,
        conversation_history: List[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Gera resposta personalizada"""
        try:
            if use_cache:
                cache_key = f"response:{user_id}:{hashlib.md5(message.encode()).hexdigest()}"
                cached = await cache.get(cache_key)
                if cached:
                    return cached
            
            user_context = await self.get_user_context(user_id)
            relevant_docs = await self.get_relevant_knowledge(message, user_id)
            
            knowledge_context = "\n\n".join([doc["content"] for doc in relevant_docs[:3]])
            
            # Formata histórico
            chat_history = ""
            if conversation_history:
                for msg in conversation_history[-5:]:
                    role = "Usuário" if msg.get("role") == "user" else "Assistente"
                    chat_history += f"{role}: {msg.get('content', '')}\n"
            
            prompt = f"""Você é um assistente especialista em nutrição e treinos.

CONTEXTO DE CONHECIMENTO:
{knowledge_context if knowledge_context else 'Nenhum contexto específico.'}

PERFIL DO USUÁRIO:
{user_context}

HISTÓRICO:
{chat_history if chat_history else 'Início da conversa'}

PERGUNTA: {message}

Responda de forma personalizada, prática e motivadora. Use o contexto e o perfil para dar recomendações específicas.
Se não souber algo, admita e sugira consultar um profissional. Mantenha tom encorajador."""
            
            response = await self.llm.ainvoke(prompt)
            
            result = {
                "answer": response.content,
                "sources": [{"category": doc["metadata"].get("category"), "relevance": doc["relevance"]} 
                           for doc in relevant_docs[:3]],
                "confidence": 0.8,
                "requires_professional": False,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if use_cache:
                await cache.set(cache_key, result, expires=3600)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}", exc_info=True)
            return {
                "answer": "Desculpe, tive um problema. Pode reformular?",
                "error": str(e),
                "user_id": user_id
            }
    
    async def generate_response_streaming(
        self,
        user_id: int,
        message: str,
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """Gera resposta com streaming"""
        try:
            user_context = await self.get_user_context(user_id)
            relevant_docs = await self.get_relevant_knowledge(message, user_id)
            knowledge_context = "\n\n".join([doc["content"] for doc in relevant_docs[:3]])
            
            prompt = f"""Você é um assistente de nutrição e treinos.

CONTEXTO: {knowledge_context}
PERFIL: {user_context}
PERGUNTA: {message}

Resposta personalizada:"""
            
            async for chunk in self.llm.astream(prompt):
                yield chunk.content
                
        except Exception as e:
            logger.error(f"Erro no streaming: {e}")
            yield "Desculpe, ocorreu um erro."
    
    async def close(self):
        """Fecha conexões"""
        logger.info("Fechando RAG Service")
        

'''
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
# from langchain.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings 
from langchain.vectorstores import Chroma
# from langchain_chroma import Chroma
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
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
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
            # Primeiro, tenta obter a coleção existente
            collection = self.chroma_client.get_collection(self.collection_name)
            # Se existir, cria o LangChain wrapper
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
        except:
            # Se não existir, cria a coleção primeiro
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            # Depois cria o LangChain wrapper
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
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
        collection = self.chroma_client.get_collection(self.collection_name)
        
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
                
                # Add each chunk diretamente
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk"] = i
                    
                    # Gerar ID único
                    doc_id = f"{category}_{item.get('subcategory', '')}_{i}_{hashlib.md5(chunk.encode()).hexdigest()[:8]}"
                    
                    # Adicionar diretamente ao Chroma
                    collection.add(
                        documents=[chunk],
                        metadatas=[chunk_metadata],
                        ids=[doc_id]
                    )
    
    """     
    async def _process_knowledge_file(self, data: Dict):
        "Process a knowledge file and add to vector store"
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
                    await self.vectorstore.aadd_texts(texts, metadatas) """
    
    
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
            
            """             
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
            """

                     # Usar cliente diretamente
            collection = self.chroma_client.get_collection(self.user_context_collection)
            
            # Buscar por metadados
            results = collection.get(
                where={"user_id": user_id},
                limit=1
            )
            
            if results and results['documents']:
                context = results['documents'][0]
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
            
            
'''