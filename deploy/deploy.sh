#!/bin/bash
# Скрипт первоначального деплоя бота на сервер
# Использование: ./deploy.sh

set -e  # Остановка при ошибке

echo "🚀 Начало деплоя бота такси Жуково..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка, что скрипт запущен от root или с sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Ошибка: Скрипт должен быть запущен с правами root или через sudo${NC}"
    exit 1
fi

# Путь к директории проекта
PROJECT_DIR="/opt/taxi-zhukovo"
SERVICE_USER="taxi"

echo -e "${YELLOW}📋 Шаг 1: Создание пользователя и директорий...${NC}"

# Создание пользователя (если не существует)
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$PROJECT_DIR" "$SERVICE_USER"
    echo -e "${GREEN}✅ Пользователь $SERVICE_USER создан${NC}"
else
    echo -e "${YELLOW}⚠️  Пользователь $SERVICE_USER уже существует${NC}"
fi

# Создание директорий
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/backups"

echo -e "${GREEN}✅ Директории созданы${NC}"

echo -e "${YELLOW}📋 Шаг 2: Клонирование/копирование проекта...${NC}"

# Проверка наличия Git репозитория
if [ -d ".git" ]; then
    echo "Обнаружен Git репозиторий, копирование с сохранением .git..."
    cp -r . "$PROJECT_DIR/" || {
        echo -e "${RED}❌ Ошибка при копировании файлов${NC}"
        exit 1
    }
    # Убедимся, что .git скопирован
    if [ -d "$PROJECT_DIR/.git" ]; then
        echo -e "${GREEN}✅ Git репозиторий скопирован${NC}"
    fi
elif [ -f "run.py" ]; then
    echo "Копирование файлов из текущей директории..."
    cp -r . "$PROJECT_DIR/" || {
        echo -e "${RED}❌ Ошибка при копировании файлов${NC}"
        exit 1
    }
else
    echo -e "${YELLOW}⚠️  Файлы не найдены в текущей директории${NC}"
    echo "Варианты:"
    echo "  1. Если проект в Git - склонируйте его на сервере:"
    echo "     git clone <repository_url> $PROJECT_DIR"
    echo "  2. Или скопируйте файлы вручную в $PROJECT_DIR"
    echo ""
    echo -e "${RED}❌ Прервано: файлы проекта не найдены${NC}"
    echo "Убедитесь, что вы находитесь в корне проекта или склонируйте репозиторий."
    exit 1
fi

# Удаление ненужных файлов (кроме .git для обновлений)
rm -rf "$PROJECT_DIR"/__pycache__ "$PROJECT_DIR"/**/__pycache__ 2>/dev/null || true
# НЕ удаляем .git - он нужен для обновлений!

echo -e "${GREEN}✅ Файлы скопированы${NC}"

echo -e "${YELLOW}📋 Шаг 3: Создание виртуального окружения...${NC}"

# Установка Python и venv (если не установлены)
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не установлен. Установите его: apt-get install python3 python3-venv${NC}"
    exit 1
fi

# Создание venv
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}✅ Виртуальное окружение создано${NC}"

echo -e "${YELLOW}📋 Шаг 4: Установка зависимостей...${NC}"

pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Зависимости установлены${NC}"

echo -e "${YELLOW}📋 Шаг 5: Настройка прав доступа...${NC}"

chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
chmod +x "$PROJECT_DIR/run.py"

echo -e "${GREEN}✅ Права доступа настроены${NC}"

echo -e "${YELLOW}📋 Шаг 6: Настройка systemd service...${NC}"

# Копирование service файла
if [ -f "deploy/taxi-bot.service" ]; then
    cp deploy/taxi-bot.service /etc/systemd/system/taxi-bot.service
    systemctl daemon-reload
    echo -e "${GREEN}✅ Systemd service установлен${NC}"
else
    echo -e "${YELLOW}⚠️  Файл deploy/taxi-bot.service не найден${NC}"
    echo "Создайте service файл вручную"
fi

echo -e "${YELLOW}📋 Шаг 7: Проверка .env файла...${NC}"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo "Создайте файл .env в $PROJECT_DIR с необходимыми переменными:"
    echo "  TELEGRAM_BOT_TOKEN=your_token"
    echo "  ADMIN_TELEGRAM_IDS=your_id"
    echo "  DATABASE_URL=sqlite:///./taxi_zhukovo.db"
    echo ""
    echo "После создания .env файла запустите:"
    echo "  sudo systemctl start taxi-bot"
    echo "  sudo systemctl enable taxi-bot"
else
    echo -e "${GREEN}✅ Файл .env найден${NC}"
fi

echo ""
echo -e "${GREEN}✅ Деплой завершен!${NC}"
echo ""
echo "Следующие шаги:"
echo "1. Убедитесь, что файл .env настроен правильно"
echo "2. Запустите бота: sudo systemctl start taxi-bot"
echo "3. Включите автозапуск: sudo systemctl enable taxi-bot"
echo "4. Проверьте статус: sudo systemctl status taxi-bot"
echo "5. Просмотрите логи: sudo journalctl -u taxi-bot -f"

