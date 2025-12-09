#!/bin/bash
# Скрипт для тестирования всех компонентов

set -e

echo "🧪 Тестирование всех компонентов Telegram Farm..."
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция проверки
check_service() {
    local name=$1
    local command=$2
    
    echo -n "Проверка $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# 1. Проверка Docker контейнеров
echo "📦 Проверка Docker контейнеров:"
check_service "Postgres" "docker exec bip-postgres-1 pg_isready -U telegram_farm"
check_service "Redis" "docker exec bip- redis-1 redis-cli ping"
check_service "MinIO" "docker exec bip-minio-1 curl -f http://localhost:9000/minio/health/live"

# 2. Проверка Control API
echo ""
echo "🌐 Проверка Control API:"
check_service "Health endpoint" "curl -s http://localhost:8000/health | grep -q healthy"
check_service "Status endpoint" "curl -s http://localhost:8000/api/v1/status | grep -q running"
check_service "Root endpoint" "curl -s http://localhost:8000/ | grep -q message"

# 3. Проверка портов
echo ""
echo "🔌 Проверка портов:"
check_service "Port 8000 (API)" "nc -z localhost 8000 || timeout 1 bash -c '</dev/tcp/localhost/8000'"
check_service "Port 5432 (Postgres)" "nc -z localhost 5432 || timeout 1 bash -c '</dev/tcp/localhost/5432'"
check_service "Port 6379 (Redis)" "nc -z localhost 6379 || timeout 1 bash -c '</dev/tcp/localhost/6379'"
check_service "Port 9000 (MinIO)" "nc -z localhost 9000 || timeout 1 bash -c '</dev/tcp/localhost/9000'"

# 4. Проверка Docker образов
echo ""
echo "🐳 Проверка Docker образов:"
if docker images | grep -q "telegram-farm/android-worker"; then
    echo -e "Android Worker image ${GREEN}✓ OK${NC}"
else
    echo -e "Android Worker image ${RED}✗ NOT FOUND${NC}"
fi

if docker images | grep -q "bip-control-api"; then
    echo -e "Control API image ${GREEN}✓ OK${NC}"
else
    echo -e "Control API image ${RED}✗ NOT FOUND${NC}"
fi

# 5. Тест подключения к БД
echo ""
echo "💾 Тест подключения к базе данных:"
if docker exec bip-postgres-1 psql -U telegram_farm -d telegram_farm -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "Postgres connection ${GREEN}✓ OK${NC}"
else
    echo -e "Postgres connection ${RED}✗ FAILED${NC}"
fi

# 6. Тест Redis
echo ""
echo "📮 Тест Redis:"
if docker exec bip-redis-1 redis-cli set test_key "test_value" > /dev/null 2>&1 && \
   docker exec bip-redis-1 redis-cli get test_key | grep -q "test_value"; then
    echo -e "Redis read/write ${GREEN}✓ OK${NC}"
    docker exec bip-redis-1 redis-cli del test_key > /dev/null 2>&1
else
    echo -e "Redis read/write ${RED}✗ FAILED${NC}"
fi

# 7. Тест API endpoints
echo ""
echo "🔗 Тест API endpoints:"
API_BASE="http://localhost:8000"

echo -n "  GET /health: "
HEALTH=$(curl -s $API_BASE/health)
if echo $HEALTH | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} $HEALTH"
else
    echo -e "${RED}✗${NC} $HEALTH"
fi

echo -n "  GET /api/v1/status: "
STATUS=$(curl -s $API_BASE/api/v1/status)
if echo $STATUS | grep -q "running"; then
    echo -e "${GREEN}✓${NC} $STATUS"
else
    echo -e "${RED}✗${NC} $STATUS"
fi

echo ""
echo "✅ Тестирование завершено!"
echo ""
echo "Доступные сервисы:"
echo "  - Control API: http://localhost:8000"
echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "  - Postgres: localhost:5432"
echo "  - Redis: localhost:6379"









