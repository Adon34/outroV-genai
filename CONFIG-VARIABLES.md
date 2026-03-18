# 🔧 Guia Completo de Configuração das Variáveis de Ambiente

## 📋 Visão Geral

Este arquivo explica como configurar todas as variáveis de ambiente necessárias para o projeto Diet & Training Chatbot funcionar corretamente.

## 🚨 VARIÁVEIS OBRIGATÓRIAS

### 1. OPENAI_API_KEY
**Como obter:**
1. Acesse: https://platform.openai.com/api-keys
2. Faça login na sua conta OpenAI
3. Clique em "Create new secret key"
4. Copie a chave gerada (formato: `sk-...`)
5. **IMPORTANTE**: Nunca compartilhe esta chave!

**Exemplo:**
```env
OPENAI_API_KEY=sk-proj-1234567890abcdef...
```

**Custos aproximados:**
- GPT-4: ~$0.03 por 1K tokens
- Embeddings: ~$0.0001 por 1K tokens
- Configure limites de uso no painel da OpenAI

---

### 2. JWT_SECRET
**O que é:** Chave secreta para gerar tokens JWT de autenticação

**Como gerar:**
```bash
# Opção 1: Usar openssl (recomendado)
openssl rand -hex 32

# Opção 2: Usar Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Exemplo:**
```env
JWT_SECRET=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z
```

**Requisitos:** Mínimo 32 caracteres, use caracteres aleatórios

---

### 3. DB_PASSWORD
**O que é:** Senha do banco de dados PostgreSQL

**Recomendações:**
- Mínimo 12 caracteres
- Misture letras maiúsculas/minúsculas, números e símbolos
- Não use senhas comuns

**Exemplo:**
```env
DB_PASSWORD=MinhaSenh@S3gur@2024!
```

---

### 4. REDIS_PASSWORD
**O que é:** Senha do cache Redis

**Recomendações:**
- Mesmo padrão da senha do banco
- Deve ser diferente da DB_PASSWORD

**Exemplo:**
```env
REDIS_PASSWORD=R3d1sC@ch3P@ssw0rd
```

---

## 🔧 VARIÁVEIS OPCIONAIS

### APIs Externas (Nutritionix & Exercise)

#### Nutritionix API
**Como obter:**
1. Acesse: https://developer.nutritionix.com/
2. Crie uma conta gratuita
3. Vá para "My Apps" > "Create New App"
4. Copie App ID e API Key

```env
NUTRITIONIX_APP_ID=12345678
NUTRITIONIX_API_KEY=abcd1234efgh5678
```

#### Exercise API
**Como obter:**
1. Acesse: https://api-ninjas.com/api/exercises
2. Inscreva-se para API gratuita
3. Copie sua API Key

```env
EXERCISE_API_KEY=abcd1234efgh5678ijkl9012
```

---

## ⚙️ VARIÁVEIS DE CONFIGURAÇÃO

### Ambiente
```env
ENVIRONMENT=development  # ou production
DEBUG=true              # false em produção
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

### JWT Config
```env
ACCESS_TOKEN_EXPIRE_MINUTES=30    # 30 minutos
REFRESH_TOKEN_EXPIRE_DAYS=7       # 7 dias
```

### Modelos OpenAI
```env
OPENAI_MODEL=gpt-4                    # gpt-4, gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### CORS (Importante para produção)
```env
CORS_ORIGINS=["http://localhost:3000", "https://seudominio.com"]
```

---

## 🧪 Como Testar a Configuração

### 1. Script de Validação Automática
```bash
# Execute o script de validação
./scripts/validate-env.sh
```

### 2. Teste Manual da OpenAI API
```bash
# Ative o ambiente virtual
source venv/bin/activate

# Teste a API
python3 -c "
import openai
import asyncio

async def test():
    client = openai.AsyncOpenAI()
    models = await client.models.list()
    print(f'✅ Sucesso! {len(models.data)} modelos disponíveis')

asyncio.run(test())
"
```

### 3. Teste do Backend
```bash
# Inicie o backend
docker compose up backend -d

# Teste health check
curl http://localhost:8001/health

# Deve retornar status 'healthy'
```

---

## 🔒 Segurança em Produção

### 1. Nunca commite o .env
```bash
# Adicione ao .gitignore
echo ".env" >> .gitignore
```

### 2. Use variáveis de ambiente do sistema
```bash
# Em produção, use variáveis do Docker/Sistema
export OPENAI_API_KEY="sk-..."
export JWT_SECRET="$(openssl rand -hex 32)"
```

### 3. Rotate chaves regularmente
- **OpenAI API Key**: Pelo menos a cada 6 meses
- **JWT Secret**: A cada deploy ou incidente de segurança
- **Database/Redis passwords**: Quando necessário

---

## 🚨 Troubleshooting

### "OpenAI API key not found"
```bash
# Verifique se a variável está definida
echo $OPENAI_API_KEY

# Ou no .env
grep OPENAI_API_KEY .env
```

### "Invalid JWT secret"
```bash
# JWT secret deve ter pelo menos 32 caracteres
echo -n "$JWT_SECRET" | wc -c  # Deve ser >= 32
```

### "Database connection failed"
```bash
# Verifique credenciais
docker compose exec postgres psql -U postgres -d diet_chatbot -c "SELECT 1;"

# Ou teste manualmente
psql "postgresql://postgres:$DB_PASSWORD@localhost:5432/diet_chatbot" -c "SELECT 1;"
```

### "Redis connection failed"
```bash
# Teste conexão
docker compose exec redis redis-cli -a "$REDIS_PASSWORD" ping
```

---

## 📝 Exemplo de .env Completo

```env
# Database
DB_USER=postgres
DB_PASSWORD=MinhaSenh@S3gur@2024!
DB_NAME=diet_chatbot
DB_HOST=postgres
DB_PORT=5432
DATABASE_URL=postgresql://postgres:MinhaSenh@S3gur@2024!@postgres:5432/diet_chatbot

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=R3d1sC@ch3P@ssw0rd
REDIS_URL=redis://:R3d1sC@ch3P@ssw0rd@redis:6379

# ChromaDB
CHROMA_HOST=chroma-db
CHROMA_PORT=8000
CHROMA_URL=http://chroma-db:8000

# JWT
JWT_SECRET=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI
OPENAI_API_KEY=sk-proj-1234567890abcdef...
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# APIs Opcionais
NUTRITIONIX_APP_ID=12345678
NUTRITIONIX_API_KEY=abcd1234efgh5678
EXERCISE_API_KEY=abcd1234efgh5678ijkl9012

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
```

---

## 🎯 Próximos Passos

1. **Configure o .env** com suas chaves reais
2. **Execute a validação**: `./scripts/validate-env.sh`
3. **Teste a aplicação**: `docker compose up -d`
4. **Verifique logs**: `docker compose logs -f backend`
5. **Acesse a aplicação**: http://localhost

**Lembre-se**: Mantenha suas chaves seguras e nunca as commite no GitHub! 🔐