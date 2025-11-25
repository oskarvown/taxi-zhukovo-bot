#!/bin/bash
# Скрипт обновления бота в Docker
# Использование: ./update-docker.sh

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 Обновление бота в Docker...${NC}"

# Проверка наличия docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose не установлен${NC}"
    exit 1
fi

# Переход в директорию с docker-compose.yml
cd "$(dirname "$0")"

echo -e "${YELLOW}📋 Шаг 1: Создание резервной копии...${NC}"

# Создание резервной копии данных
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -d "../data" ]; then
    mkdir -p "../backups"
    tar -czf "../backups/data_${TIMESTAMP}.tar.gz" -C .. data/
    echo -e "${GREEN}✅ Резервная копия данных создана${NC}"
fi

echo -e "${YELLOW}📋 Шаг 2: Остановка контейнера...${NC}"
docker-compose down

echo -e "${YELLOW}📋 Шаг 3: Обновление образа...${NC}"
docker-compose build --no-cache

echo -e "${YELLOW}📋 Шаг 4: Запуск обновленного контейнера...${NC}"
docker-compose up -d

echo -e "${YELLOW}📋 Шаг 5: Проверка статуса...${NC}"
sleep 3

if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Бот успешно запущен${NC}"
else
    echo -e "${RED}❌ Ошибка при запуске${NC}"
    echo "Проверьте логи: docker-compose logs"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Обновление завершено!${NC}"
echo ""
echo "Проверьте статус: docker-compose ps"
echo "Просмотрите логи: docker-compose logs -f"

