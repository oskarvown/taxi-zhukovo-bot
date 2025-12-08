#!/bin/bash
# Скрипт для автоматического обновления на сервере
# Аудит и исправление логики очередей водителей

set -e  # Остановка при ошибке

echo "=========================================="
echo "Обновление: Аудит очередей водителей"
echo "=========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Переменные
PROJECT_DIR="/путь/к/проекту/TAXI_ЖУКОВО"  # ИЗМЕНИТЕ НА ВАШ ПУТЬ
BACKUP_DIR="backups"
DB_NAME="taxi_zhukovo.db"

# Проверка директории
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Ошибка: Директория $PROJECT_DIR не найдена!${NC}"
    echo "Измените переменную PROJECT_DIR в скрипте"
    exit 1
fi

cd "$PROJECT_DIR"

echo -e "${GREEN}✓ Директория проекта: $PROJECT_DIR${NC}"

# 1. Создание бэкапа БД
echo ""
echo "1. Создание резервной копии БД..."
mkdir -p "$BACKUP_DIR"
if [ -f "$DB_NAME" ]; then
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME%.db}_backup_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB_NAME" "$BACKUP_FILE"
    echo -e "${GREEN}✓ Бэкап создан: $BACKUP_FILE${NC}"
else
    echo -e "${YELLOW}⚠ База данных не найдена, пропускаем бэкап${NC}"
fi

# 2. Остановка бота
echo ""
echo "2. Остановка бота..."
if systemctl is-active --quiet taxi-bot 2>/dev/null; then
    sudo systemctl stop taxi-bot
    echo -e "${GREEN}✓ Бот остановлен (systemd)${NC}"
elif pgrep -f "python.*run.py\|python.*main.py" > /dev/null; then
    echo -e "${YELLOW}⚠ Бот запущен через другой метод. Остановите вручную!${NC}"
    echo "Найденные процессы:"
    ps aux | grep -E "python.*run.py|python.*main.py" | grep -v grep
    read -p "Остановить процессы? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "python.*run.py\|python.*main.py"
        sleep 2
        echo -e "${GREEN}✓ Процессы остановлены${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Бот не запущен${NC}"
fi

# 3. Обновление из GitHub
echo ""
echo "3. Обновление кода из GitHub..."
git fetch origin
CURRENT_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo -e "${YELLOW}⚠ Код уже обновлен${NC}"
else
    echo "Текущий коммит: ${CURRENT_COMMIT:0:7}"
    echo "Удаленный коммит: ${REMOTE_COMMIT:0:7}"
    git pull origin main
    echo -e "${GREEN}✓ Код обновлен${NC}"
fi

# 4. Проверка нового коммита
echo ""
echo "4. Проверка изменений..."
LATEST_COMMIT=$(git log -1 --oneline)
echo "Последний коммит: $LATEST_COMMIT"

if echo "$LATEST_COMMIT" | grep -q "Аудит и исправление логики очередей"; then
    echo -e "${GREEN}✓ Правильный коммит найден${NC}"
else
    echo -e "${YELLOW}⚠ Внимание: Коммит об аудите не найден!${NC}"
fi

# 5. Проверка новых файлов
echo ""
echo "5. Проверка новых файлов..."
if [ -f "check_dema_drivers.py" ]; then
    echo -e "${GREEN}✓ check_dema_drivers.py найден${NC}"
else
    echo -e "${RED}✗ check_dema_drivers.py не найден!${NC}"
fi

if [ -f "АУДИТ_ОЧЕРЕДЕЙ_ВОДИТЕЛЕЙ.md" ]; then
    echo -e "${GREEN}✓ АУДИТ_ОЧЕРЕДЕЙ_ВОДИТЕЛЕЙ.md найден${NC}"
else
    echo -e "${YELLOW}⚠ АУДИТ_ОЧЕРЕДЕЙ_ВОДИТЕЛЕЙ.md не найден${NC}"
fi

# 6. Обновление зависимостей (если нужно)
echo ""
echo "6. Проверка зависимостей..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Виртуальное окружение активировано${NC}"
    
    if [ -f "requirements.txt" ]; then
        read -p "Обновить зависимости из requirements.txt? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pip install -r requirements.txt --quiet
            echo -e "${GREEN}✓ Зависимости обновлены${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠ Виртуальное окружение не найдено${NC}"
fi

# 7. Запуск бота
echo ""
echo "7. Запуск бота..."
if systemctl list-unit-files | grep -q taxi-bot.service; then
    sudo systemctl start taxi-bot
    sleep 2
    if systemctl is-active --quiet taxi-bot; then
        echo -e "${GREEN}✓ Бот запущен через systemd${NC}"
        echo "Проверка статуса:"
        sudo systemctl status taxi-bot --no-pager -l | head -10
    else
        echo -e "${RED}✗ Ошибка запуска бота!${NC}"
        echo "Логи:"
        sudo journalctl -u taxi-bot -n 20 --no-pager
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Systemd service не найден. Запустите бота вручную!${NC}"
    echo "Команда: python run.py"
fi

# 8. Итог
echo ""
echo "=========================================="
echo -e "${GREEN}Обновление завершено!${NC}"
echo "=========================================="
echo ""
echo "Следующие шаги:"
echo "1. Проверьте логи: sudo journalctl -u taxi-bot -f"
echo "2. Проверьте новые команды:"
echo "   - /reset_drivers (от имени админа)"
echo "   - /check_dema (от имени админа)"
echo "3. Запустите проверку зоны DEMA: python check_dema_drivers.py"
echo ""
echo "Бэкап БД: $BACKUP_FILE"




