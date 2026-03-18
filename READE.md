# Diet & Training Chatbot

Assistente pessoal com IA para dieta e treinos personalizados usando RAG (Retrieval-Augmented Generation).

## 🚀 Tecnologias

- **Backend**: FastAPI, PostgreSQL, Redis, ChromaDB
- **Frontend**: React 18, Axios, WebSocket
- **IA**: OpenAI GPT-4, RAG (Retrieval-Augmented Generation)
- **Infra**: Docker, Nginx, Prometheus, Grafana

## 📋 Pré-requisitos

- Docker 24.0+
- Docker Compose 2.20+
- Git
- 8GB RAM mínimo
- 20GB espaço em disco
- Chave da API OpenAI

## 🛠️ Instalação e Configuração

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/diet-chatbot.git
cd diet-chatbot
```

### 2. Configure as variáveis de ambiente
```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure:
```env
# OpenAI API Key (obrigatório)
OPENAI_API_KEY=sk-your-openai-api-key-here

# JWT Secret (mude para produção)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# Opcional: senhas customizadas
DB_PASSWORD=your-secure-db-password
REDIS_PASSWORD=your-secure-redis-password
```

### 3. Inicie os serviços
```bash
# Desenvolvimento
npm run docker:up

# Com monitoramento
npm run monitor
```

### 4. Inicialize o banco de dados
```bash
npm run db:migrate
npm run db:seed
```

## 🚀 Uso

### API Endpoints

- **POST** `/auth/register` - Registrar usuário
- **POST** `/auth/token` - Login
- **POST** `/chat/send` - Enviar mensagem para o chatbot
- **GET** `/meals/today` - Refeições do dia
- **GET** `/workouts/today` - Treinos do dia
- **GET** `/users/progress` - Progresso do usuário

### Interface Web

Acesse `http://localhost` para usar a interface web.

### Monitoramento

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3001` (admin/admin)

## 🧪 Testes

```bash
# Testes de API
npm run test:api

# Desenvolvimento com hot reload
npm run docker:build && npm run docker:up
```

## 📁 Estrutura do Projeto

```
.
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── routers/        # Endpoints da API
│   │   ├── models/         # Modelos SQLAlchemy
│   │   ├── schemas/        # Schemas Pydantic
│   │   ├── services/       # Lógica de negócio
│   │   └── rag/           # Sistema RAG
├── frontend/               # App React
├── monitoring/            # Prometheus & Grafana
├── nginx/                 # Configuração do proxy reverso
├── postgres/              # Scripts de inicialização do banco
├── scripts/               # Scripts utilitários
└── docker-compose.yml     # Orquestração dos serviços
```

## 🔧 Desenvolvimento

### Backend
```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Comandos Úteis
```bash
# Logs dos serviços
npm run docker:logs

# Parar todos os serviços
npm run docker:down

# Limpar volumes (cuidado!)
npm run docker:clean

# Backup
npm run backup
```

## 🔒 Segurança

- JWT tokens para autenticação
- CORS configurado para domínios específicos
- Senhas hasheadas com bcrypt
- Rate limiting implementado
- Secrets gerenciados via variáveis de ambiente

## 📊 Monitoramento

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