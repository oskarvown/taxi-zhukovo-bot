#!/bin/bash
# Скрипт обновления бота на сервере
# Использование: ./update.sh [branch_name]
# По умолчанию обновляется из текущей директории или из git

set -e  # Остановка при ошибке

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="/opt/taxi-zhukovo"
SERVICE_NAME="taxi-bot"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}🔄 Начало обновления бота...${NC}"

# Проверка, что скрипт запущен от root или с sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Ошибка: Скрипт должен быть запущен с правами root или через sudo${NC}"
    exit 1
fi

# Проверка существования директории проекта
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Ошибка: Директория проекта $PROJECT_DIR не найдена${NC}"
    echo "Сначала выполните первоначальный деплой: ./deploy.sh"
    exit 1
fi

echo -e "${YELLOW}📋 Шаг 1: Создание резервной копии...${NC}"

# Создание резервной копии базы данных
if [ -f "$PROJECT_DIR/taxi_zhukovo.db" ]; then
    mkdir -p "$BACKUP_DIR"
    cp "$PROJECT_DIR/taxi_zhukovo.db" "$BACKUP_DIR/taxi_zhukovo_${TIMESTAMP}.db"
    echo -e "${GREEN}✅ Резервная копия БД создана: taxi_zhukovo_${TIMESTAMP}.db${NC}"
fi

# Создание резервной копии .env
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/.env_${TIMESTAMP}"
    echo -e "${GREEN}✅ Резервная копия .env создана${NC}"
fi

echo -e "${YELLOW}📋 Шаг 2: Остановка бота...${NC}"

systemctl stop "$SERVICE_NAME" || {
    echo -e "${YELLOW}⚠️  Бот не был запущен или уже остановлен${NC}"
}

# Ждем полной остановки
sleep 3

echo -e "${GREEN}✅ Бот остановлен${NC}"

echo -e "${YELLOW}📋 Шаг 3: Обновление кода...${NC}"

cd "$PROJECT_DIR"

# Если это git репозиторий
if [ -d ".git" ]; then
    BRANCH=${1:-main}
    echo "Обновление из git (ветка: $BRANCH)..."
    
    # Сохранение текущих изменений (если есть)
    git stash || true
    
    # Обновление из удаленного репозитория
    git fetch origin
    
    # Переключение на нужную ветку
    git checkout "$BRANCH" || git checkout -b "$BRANCH" origin/"$BRANCH"
    
    # Обновление кода
    git pull origin "$BRANCH"
    
    echo -e "${GREEN}✅ Код обновлен из git (ветка: $BRANCH)${NC}"
    
    # Показ последних коммитов
    echo -e "${BLUE}Последние изменения:${NC}"
    git log --oneline -5
else
    # Если обновление из локальной директории
    if [ -f "../update_files.tar.gz" ]; then
        echo "Распаковка обновления из архива..."
        tar -xzf ../update_files.tar.gz -C "$PROJECT_DIR" --exclude='.env' --exclude='*.db' --exclude='venv' --exclude='logs'
        echo -e "${GREEN}✅ Код обновлен из архива${NC}"
    else
        echo -e "${YELLOW}⚠️  Git репозиторий не найден и архив обновления отсутствует${NC}"
        echo "Скопируйте новые файлы вручную в $PROJECT_DIR"
    fi
fi

echo -e "${YELLOW}📋 Шаг 4: Обновление зависимостей...${NC}"

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Зависимости обновлены${NC}"

echo -e "${YELLOW}📋 Шаг 5: Очистка кэша...${NC}"

# Удаление __pycache__
find "$PROJECT_DIR" -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

echo -e "${GREEN}✅ Кэш очищен${NC}"

echo -e "${YELLOW}📋 Шаг 6: Проверка .env файла...${NC}"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}⚠️  ВНИМАНИЕ: Файл .env не найден!${NC}"
    echo "Восстановите его из резервной копии или создайте заново"
else
    echo -e "${GREEN}✅ Файл .env на месте${NC}"
fi

echo -e "${YELLOW}📋 Шаг 7: Запуск бота...${NC}"

systemctl start "$SERVICE_NAME"
sleep 2

# Проверка статуса
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ Бот успешно запущен${NC}"
else
    echo -e "${RED}❌ Ошибка при запуске бота${NC}"
    echo "Проверьте логи: sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Обновление завершено успешно!${NC}"
echo ""
echo "Проверьте статус: sudo systemctl status $SERVICE_NAME"
echo "Просмотрите логи: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Резервные копии сохранены в: $BACKUP_DIR"

