# 🤖 Diet & Training Chatbot - Assistente IA para Saúde e Fitness

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)](https://reactjs.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)

> Assistente pessoal inteligente para dieta e treinos personalizados usando RAG (Retrieval-Augmented Generation) e monitoramento avançado.

## ✨ Funcionalidades

### 🤖 IA Avançada
- **Chatbot inteligente** com GPT-4 para conversas naturais
- **Sistema RAG** para respostas contextuais baseadas em conhecimento nutricional
- **Recomendações personalizadas** de dieta e exercícios
- **Acompanhamento de progresso** com métricas detalhadas

### 📊 Monitoramento em Tempo Real
- **Matriz de Saúde** completa por componente
- **Métricas Prometheus** para observabilidade
- **Dashboard Grafana** com visualizações avançadas
- **Health checks** automatizados e alertas inteligentes

### 🏗️ Infraestrutura Robusta
- **Microserviços** com Docker e Kubernetes-ready
- **Banco PostgreSQL** para dados relacionais
- **Redis** para cache de alta performance
- **ChromaDB** para embeddings vetoriais
- **Nginx** como proxy reverso

## 🚀 Início Rápido

### Pré-requisitos
- 🐳 **Docker** 24.0+
- 🐳 **Docker Compose** 2.20+
- 🔑 **Chave OpenAI API** (veja [como obter](#-configuração-da-openai-api))

### 1. Clone e Configure
```bash
# Clone o repositório
git clone https://github.com/Adon34/outroV-genai.git
cd outroV-genai

# Configure variáveis de ambiente
cp .env.example .env
nano .env  # Configure suas chaves
```

### 2. Valide a Configuração
```bash
# Execute validação automática
./scripts/validate-env.sh
```

### 3. Inicie a Aplicação
```bash
# Build e start de todos os serviços
docker compose up -d --build

# Verifique se está tudo rodando
docker compose ps
```

### 4. Acesse a Aplicação
- 🌐 **Frontend**: http://localhost
- 📚 **API Docs**: http://localhost:8001/docs
- 📊 **Monitoramento**: http://localhost:9090 (Prometheus)
- 📈 **Dashboards**: http://localhost:3001 (Grafana: admin/admin)

## 🔧 Configuração Detalhada

### 🔑 Configuração da OpenAI API

1. Acesse [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Crie uma nova chave secreta
3. Configure no `.env`:
```env
OPENAI_API_KEY=sk-proj-sua-chave-aqui
```

### 📋 Todas as Variáveis de Ambiente

Para configuração completa, consulte:
- 📖 **[CONFIG-VARIABLES.md](CONFIG-VARIABLES.md)** - Guia detalhado de todas as variáveis
- 🧪 **Script de validação**: `./scripts/validate-env.sh`

**Variáveis obrigatórias:**
- `OPENAI_API_KEY` - Chave da API OpenAI
- `JWT_SECRET` - Chave secreta para tokens JWT
- `DB_PASSWORD` - Senha do PostgreSQL
- `REDIS_PASSWORD` - Senha do Redis

## 🏥 Matriz de Saúde por Componente

O sistema inclui uma **matriz de saúde abrangente** que monitora todos os componentes em tempo real:

### 📈 Endpoints de Saúde
- `GET /health` - Status completo de todos os componentes
- `GET /health/live` - Probe de liveness (simples)
- `GET /health/ready` - Probe de readiness (com dependências)
- `GET /health/{component}` - Status individual
- `GET /metrics` - Métricas Prometheus

### 🔍 Componentes Monitorados
| Componente | Métricas | Status |
|------------|----------|--------|
| **PostgreSQL** | Conexões ativas, pool utilization | ✅ |
| **Redis** | Memória, conexões, uptime | ✅ |
| **ChromaDB** | Coleções, latência | ✅ |
| **RAG Service** | Inicialização, performance | ✅ |
| **OpenAI API** | Rate limits, disponibilidade | ✅ |

### 📊 Dashboard de Monitoramento

Acesse a aba **"Saúde Sistema"** no dashboard do usuário para visualizar:
- Status em tempo real de todos os componentes
- Métricas de performance e latência
- Histórico de disponibilidade
- Alertas e notificações

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Monitoring    │
│   React App     │    │  Prometheus     │
│   (Port 3000)   │    │  + Grafana      │
└─────────┬───────┘    │  (Ports 9090,   │
          │            │      3001)     │
          ▼            └─────────────────┘
┌─────────────────┐
│   Nginx Proxy   │  ◄── Load Balancer
│   (Port 80)     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│   Backend API   │────│   Databases     │
│   FastAPI       │    │                 │
│   (Port 8001)   │    │ • PostgreSQL    │
│                 │    │   (Port 5432)   │
│ • Auth Service  │    │ • Redis Cache   │
│ • Chat Service  │    │   (Port 6379)   │
│ • Health Matrix │    │ • ChromaDB      │
│ • RAG Engine    │    │   (Port 8000)   │
└─────────────────┘    └─────────────────┘
```

## 📁 Estrutura do Projeto

```
outroV-genai/
├── backend/                 # 🏭 API FastAPI
│   ├── app/
│   │   ├── health/         # 🏥 Módulo de saúde
│   │   ├── routers/        # 🔌 Endpoints da API
│   │   ├── models/         # 🗄️ Modelos SQLAlchemy
│   │   ├── schemas/        # 📋 Schemas Pydantic
│   │   ├── services/       # ⚙️ Lógica de negócio
│   │   └── rag/           # 🧠 Sistema RAG
│   ├── requirements.txt    # 📦 Dependências Python
│   └── Dockerfile         # 🐳 Container backend
├── frontend/              # ⚛️ Aplicação React
│   ├── src/
│   │   ├── components/    # 🧩 Componentes React
│   │   └── services/      # 🔗 Serviços API
│   ├── package.json       # 📦 Dependências Node
│   └── Dockerfile         # 🐳 Container frontend
├── monitoring/           # 📊 Stack de monitoramento
│   ├── prometheus/       # 📈 Métricas
│   └── grafana/          # 📊 Dashboards
├── scripts/              # 🛠️ Scripts utilitários
│   ├── validate-env.sh   # ✅ Validação de config
│   ├── backup.sh         # 💾 Backup
│   └── init-db.sh        # 🗄️ Inicialização DB
├── docker-compose.yml    # 🐳 Orquestração
├── DEPLOY.md            # 🚀 Guia de deploy EC2
├── CONFIG-VARIABLES.md  # 🔧 Guia de configuração
└── README.md           # 📖 Este arquivo
```

## 🔌 API Endpoints

### Autenticação
- `POST /auth/register` - Registrar novo usuário
- `POST /auth/login` - Login do usuário
- `POST /auth/refresh` - Renovar token JWT

### Chat & IA
- `POST /chat/send` - Enviar mensagem para o chatbot
- `GET /chat/history` - Histórico de conversas

### Nutrição
- `GET /meals/today` - Refeições do dia
- `POST /meals` - Adicionar refeição
- `GET /meals/{id}` - Detalhes da refeição

### Treinos
- `GET /workouts/today` - Treinos do dia
- `POST /workouts` - Adicionar treino
- `GET /workouts/{id}` - Detalhes do treino

### Usuário
- `GET /users/profile` - Perfil do usuário
- `PUT /users/profile` - Atualizar perfil
- `GET /users/progress` - Progresso e métricas

### Sistema
- `GET /health` - Matriz de saúde completa
- `GET /health/live` - Health check simples
- `GET /health/ready` - Readiness check
- `GET /metrics` - Métricas Prometheus

## 🧪 Desenvolvimento

### Ambiente Local
```bash
# Backend
cd backend
source ../venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend (terminal separado)
cd frontend
npm install
npm start
```

### Comandos Úteis
```bash
# Logs em tempo real
docker compose logs -f

# Parar serviços
docker compose down

# Limpar tudo (volumes incluídos)
docker compose down -v

# Executar testes
docker compose exec backend python -m pytest

# Backup do banco
docker compose exec postgres pg_dump -U postgres diet_chatbot > backup.sql

# Verificar saúde
curl http://localhost:8001/health | jq
```

## 🚀 Deploy em Produção

### AWS EC2
Para deploy completo na EC2, siga o guia:
- 📖 **[DEPLOY.md](DEPLOY.md)** - Guia passo-a-passo para EC2

### Configuração Básica
```bash
# Em produção, configure:
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=["https://yourdomain.com"]
```

## 🔒 Segurança

- ✅ **JWT Authentication** com refresh tokens
- ✅ **CORS** configurado para domínios específicos
- ✅ **Password Hashing** com bcrypt
- ✅ **Rate Limiting** implementado
- ✅ **Environment Secrets** (nunca commite `.env`)
- ✅ **Health Checks** para auto-healing
- ✅ **SSL/TLS** pronto para configuração

## 📊 Monitoramento & Observabilidade

### Métricas Coletadas
- **Performance**: Latência, throughput, error rates
- **Sistema**: CPU, memória, disco, rede
- **Aplicação**: Requests, responses, cache hits
- **Negócio**: Usuários ativos, conversas, progresso

### Dashboards Disponíveis
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Health Matrix**: Interface web integrada

### Alertas Configurados
- Componentes não saudáveis
- Alta utilização de recursos
- Falhas de conectividade
- Rate limits da OpenAI

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Padrões de Código
- **Backend**: Black, isort, flake8
- **Frontend**: ESLint, Prettier
- **Commits**: Conventional commits
- **Testes**: pytest para Python, Jest para React

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

- 📧 **Issues**: [GitHub Issues](https://github.com/Adon34/outroV-genai/issues)
- 📖 **Documentação**: [Wiki](https://github.com/Adon34/outroV-genai/wiki)
- 🐛 **Bugs**: Abra uma issue com logs e passos para reproduzir

## 🙏 Agradecimentos

- **OpenAI** pela API GPT-4
- **FastAPI** pela framework incrível
- **React** pelo ecossistema robusto
- **Comunidade Open Source** por todas as ferramentas

---

**⭐ Star este repositório se o projeto foi útil para você!**

**🚀 Pronto para revolucionar a experiência de saúde e fitness com IA!**

**⭐ Star este repositório se o projeto foi útil para você!**

**🚀 Pronto para revolucionar a experiência de saúde e fitness com IA!**

O projeto inclui monitoramento completo com:
- **Prometheus**: Coleta métricas dos serviços
- **Grafana**: Dashboards visuais
- **Alertas**: Notificações automáticas
- **Health checks**: Verificação de saúde dos serviços

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 🆘 Suporte

Para suporte, abra uma issue no GitHub ou entre em contato com a equipe de desenvolvimento.