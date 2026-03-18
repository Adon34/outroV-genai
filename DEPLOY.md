# 🚀 Guia de Deploy - Diet & Training Chatbot na EC2

Este guia fornece instruções completas para fazer deploy da aplicação Diet & Training Chatbot em uma instância EC2 da AWS.

## 📋 Pré-requisitos da EC2

### Especificações Mínimas Recomendadas
- **Instância**: t3.medium ou superior (2 vCPU, 4GB RAM)
- **Armazenamento**: 20GB SSD
- **SO**: Ubuntu 22.04 LTS ou Amazon Linux 2
- **Security Group**:
  - SSH (porta 22)
  - HTTP (porta 80)
  - HTTPS (porta 443)
  - Aplicação (porta 8001 - backend, opcional)

### Pacotes Necessários
```bash
sudo apt update
sudo apt install -y docker.io docker-compose git curl wget
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu  # ou seu usuário
```

## 🛠️ Deploy Automático

### 1. Clone e Configure
```bash
# Clone o repositório
git clone https://github.com/Adon34/outroV-genai.git
cd outroV-genai

# Configure as variáveis de ambiente
cp .env.example .env
nano .env  # Configure as chaves necessárias
```

### 2. Configure o Ambiente (.env)
```env
# OpenAI API Key (OBRIGATÓRIO)
OPENAI_API_KEY=sk-your-openai-api-key-here

# JWT Secret (mude para produção)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# Database
DB_USER=postgres
DB_PASSWORD=your-secure-db-password-here
DB_NAME=diet_chatbot
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-redis-password-here

# ChromaDB
CHROMA_HOST=chroma-db
CHROMA_PORT=8000

# Ambiente
ENVIRONMENT=production
DEBUG=false

# CORS (configure para seu domínio)
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
```

### 3. Deploy com Docker Compose
```bash
# Construa e inicie todos os serviços
docker compose up -d --build

# Verifique se todos os serviços estão rodando
docker compose ps

# Verifique logs
docker compose logs -f
```

### 4. Inicialize o Banco de Dados
```bash
# Execute as migrações
docker compose exec backend alembic upgrade head

# Opcional: Popule com dados de exemplo
docker compose exec backend python scripts/seed-data.py
```

### 5. Configure Nginx (Opcional - para produção)
```bash
# Instale Nginx
sudo apt install -y nginx

# Configure o site
sudo nano /etc/nginx/sites-available/diet-chatbot
```

Conteúdo do arquivo `/etc/nginx/sites-available/diet-chatbot`:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Frontend React
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks
    location /health {
        proxy_pass http://localhost:8001/health;
        access_log off;
    }

    # Prometheus metrics (se necessário)
    location /metrics {
        proxy_pass http://localhost:8001/metrics;
        allow 127.0.0.1;
        deny all;
    }
}
```

```bash
# Ative o site
sudo ln -s /etc/nginx/sites-available/diet-chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔍 Verificação do Deploy

### 1. Verifique a Saúde dos Serviços
```bash
# Status dos containers
docker compose ps

# Logs dos serviços
docker compose logs backend
docker compose logs frontend

# Teste da API
curl http://localhost:8001/health
curl http://localhost:8001/docs
```

### 2. Acesse a Aplicação
- **Frontend**: `http://your-ec2-public-ip`
- **API Docs**: `http://your-ec2-public-ip/api/docs`
- **Health Check**: `http://your-ec2-public-ip/health`

### 3. Monitore os Serviços
```bash
# Prometheus: http://your-ec2-public-ip:9090
# Grafana: http://your-ec2-public-ip:3001 (admin/admin)

# Verifique métricas de saúde
curl http://localhost:8001/health | jq
```

## 🔧 Comandos Úteis para Manutenção

### Atualizar a Aplicação
```bash
# Pare os serviços
docker compose down

# Puxe as últimas mudanças
git pull origin main

# Reinicie tudo
docker compose up -d --build

# Execute migrações se houver
docker compose exec backend alembic upgrade head
```

### Backup do Banco de Dados
```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U postgres diet_chatbot > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup Redis (se necessário)
docker compose exec redis redis-cli --rdb backup.rdb
```

### Logs e Troubleshooting
```bash
# Logs de todos os serviços
docker compose logs -f

# Logs específicos
docker compose logs -f backend
docker compose logs -f postgres

# Verificar uso de recursos
docker stats

# Entrar no container para debug
docker compose exec backend bash
```

## 🚨 Monitoramento e Alertas

### Health Checks
- **Aplicação**: `GET /health` - Status completo de todos os componentes
- **Liveness**: `GET /health/live` - Verifica se app está rodando
- **Readiness**: `GET /health/ready` - Verifica se app está pronto para tráfego

### Métricas Prometheus
- **Endpoint**: `GET /metrics`
- **Dashboards**: Grafana disponível em `:3001`
- **Alertas**: Configurados para notificações automáticas

### Logs Importantes
```bash
# Logs de erro da aplicação
docker compose logs backend | grep ERROR

# Logs de acesso Nginx
sudo tail -f /var/log/nginx/access.log

# System logs
sudo journalctl -u docker -f
```

## 🔒 Segurança em Produção

### 1. Configure SSL/TLS
```bash
# Instale Certbot para Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 2. Configure Firewall
```bash
# UFW básico
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

### 3. Segurança do Docker
```bash
# Execute containers como usuário não-root
# Configure secrets para senhas
# Use redes Docker isoladas
# Monitore vulnerabilidades: docker scan
```

### 4. Backup Automático
```bash
# Configure cron job para backup diário
echo "0 2 * * * cd /home/ubuntu/outroV-genai && ./scripts/backup.sh" | crontab -
```

## 📊 Escalabilidade

### Horizontal Scaling
- Use ALB (Application Load Balancer) para múltiplas EC2
- Configure Redis Cluster para cache distribuído
- Use RDS PostgreSQL para banco gerenciado

### Vertical Scaling
- Monitore uso de CPU/Memória
- Ajuste instance type conforme necessário
- Configure auto-scaling groups

## 🆘 Troubleshooting Comum

### Aplicação não inicia
```bash
# Verifique variáveis de ambiente
docker compose config

# Verifique logs detalhados
docker compose logs --tail=100 backend
```

### Erro de conectividade com banco
```bash
# Teste conexão PostgreSQL
docker compose exec postgres psql -U postgres -d diet_chatbot -c "SELECT 1;"

# Verifique se serviço está saudável
docker compose ps
```

### Frontend não carrega
```bash
# Verifique build do frontend
docker compose logs frontend

# Teste acesso direto
curl http://localhost:3000
```

### Problemas de memória
```bash
# Monitore uso de recursos
docker stats

# Ajuste limites no docker-compose.yml
# Considere aumentar instance type
```

---

## 📞 Suporte

Para problemas específicos:
1. Verifique os logs: `docker compose logs`
2. Teste health checks: `curl http://localhost:8001/health`
3. Consulte documentação: [README.md](READE.md)
4. Abra issue no GitHub se necessário

**Deploy realizado com sucesso!** 🎉