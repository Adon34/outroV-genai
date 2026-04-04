# Estágio 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar arquivos de dependências
COPY package*.json ./

# Instalar dependências (inclui devDependencies como react-scripts)
# Usa --legacy-peer-deps para resolver conflitos
RUN npm install --legacy-peer-deps --no-audit --no-fund

# Instalar explicitamente o módulo problemático (ajv)
RUN npm install ajv@8.12.0 --save-dev

# Copiar o código fonte
COPY . .

# Construir a aplicação
RUN npm run build

# Verificar se o build gerou a pasta (debug)
RUN if [ ! -d /app/build ] || [ -z "$(ls -A /app/build)" ]; then echo "Build failed - no output" && exit 1; fi

# Estágio 2: Servir arquivos estáticos
FROM node:18-alpine

WORKDIR /app

# Instalar curl (para healthcheck) e serve
RUN apk add --no-cache curl && npm install -g serve

# Copiar os arquivos buildados do estágio anterior
COPY --from=builder /app/build ./build

# Verificar se a cópia funcionou
RUN if [ ! -d ./build ] || [ -z "$(ls -A ./build)" ]; then echo "No build files copied" && exit 1; fi

# Expor porta
EXPOSE 3000

# Healthcheck (aguarda 10 segundos antes de começar)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:3000 || exit 1

# Servir a aplicação
CMD ["serve", "-s", "build", "-l", "3000"]