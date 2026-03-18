#!/bin/bash

# Script para validar configuração das variáveis de ambiente
# Execute: ./scripts/validate-env.sh

echo "🔍 Validando configuração das variáveis de ambiente..."
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para verificar variável
check_var() {
    local var_name=$1
    local var_value=$2
    local required=${3:-false}

    if [ -z "$var_value" ]; then
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ $var_name: NÃO CONFIGURADO (obrigatório)${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠️  $var_name: NÃO CONFIGURADO (opcional)${NC}"
            return 0
        fi
    else
        if [ "$required" = "true" ]; then
            echo -e "${GREEN}✅ $var_name: CONFIGURADO${NC}"
        else
            echo -e "${GREEN}✅ $var_name: CONFIGURADO${NC}"
        fi
        return 0
    fi
}

# Carregar variáveis do .env
if [ -f ".env" ]; then
    echo "📄 Carregando arquivo .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${RED}❌ Arquivo .env não encontrado!${NC}"
    exit 1
fi

echo ""
echo "🔐 Verificando variáveis obrigatórias:"
echo "-------------------------------------"

# Verificações obrigatórias
errors=0
check_var "OPENAI_API_KEY" "$OPENAI_API_KEY" true || ((errors++))
check_var "JWT_SECRET" "$JWT_SECRET" true || ((errors++))
check_var "DB_PASSWORD" "$DB_PASSWORD" true || ((errors++))
check_var "REDIS_PASSWORD" "$REDIS_PASSWORD" true || ((errors++))

echo ""
echo "🔧 Verificando variáveis opcionais:"
echo "-----------------------------------"

# Verificações opcionais
check_var "NUTRITIONIX_APP_ID" "$NUTRITIONIX_APP_ID" false
check_var "NUTRITIONIX_API_KEY" "$NUTRITIONIX_API_KEY" false
check_var "EXERCISE_API_KEY" "$EXERCISE_API_KEY" false

echo ""
echo "🧪 Testando conectividade:"
echo "-------------------------"

# Testar OpenAI API (se chave estiver configurada)
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "Testando OpenAI API..."
    python3 -c "
import openai
import asyncio
import sys

async def test_openai():
    try:
        client = openai.AsyncOpenAI(api_key='$OPENAI_API_KEY')
        models = await client.models.list()
        print('✅ OpenAI API: Conexão bem-sucedida')
        print(f'   Modelos disponíveis: {len(models.data)}')
        return True
    except Exception as e:
        print(f'❌ OpenAI API: Erro - {str(e)}')
        return False

result = asyncio.run(test_openai())
sys.exit(0 if result else 1)
" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ OpenAI API: OK${NC}"
    else
        echo -e "${RED}❌ OpenAI API: FALHA${NC}"
        ((errors++))
    fi
fi

echo ""
echo "📊 Resumo:"
echo "----------"

if [ $errors -eq 0 ]; then
    echo -e "${GREEN}🎉 Todas as configurações obrigatórias estão OK!${NC}"
    echo ""
    echo "🚀 Você pode iniciar a aplicação com:"
    echo "   docker compose up -d --build"
else
    echo -e "${RED}❌ $errors problema(s) encontrado(s). Corrija antes de continuar.${NC}"
    echo ""
    echo "🔧 Para corrigir:"
    echo "   1. Edite o arquivo .env: nano .env"
    echo "   2. Configure as variáveis marcadas em vermelho"
    echo "   3. Execute novamente: ./scripts/validate-env.sh"
fi

echo ""
echo "💡 Dicas:"
echo "   - JWT_SECRET deve ter pelo menos 32 caracteres"
echo "   - Use senhas fortes para DB_PASSWORD e REDIS_PASSWORD"
echo "   - OPENAI_API_KEY deve começar com 'sk-'"