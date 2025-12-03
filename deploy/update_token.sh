#!/bin/bash
# ===========================================
# СКРИПТ ОБНОВЛЕНИЯ ТОКЕНА TELEGRAM БОТА
# ===========================================

set -e

PROJECT_DIR="/opt/taxi-zhukovo"
ENV_FILE="$PROJECT_DIR/.env"
NEW_TOKEN="8460587651:AAGKey9Z54B2fcgyKTs06Lm5PFveNBVwdpI"

echo "========================================"
echo "🔄 ОБНОВЛЕНИЕ ТОКЕНА TELEGRAM БОТА"
echo "========================================"

# Проверяем, что мы на сервере
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Директория $PROJECT_DIR не найдена"
    echo "   Этот скрипт должен выполняться на сервере!"
    exit 1
fi

cd "$PROJECT_DIR"

# Проверяем существование .env
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Файл .env не найден в $PROJECT_DIR"
    exit 1
fi

# Показываем старый токен (первые 10 символов)
OLD_TOKEN=$(grep "TELEGRAM_BOT_TOKEN" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
echo "📌 Старый токен: ${OLD_TOKEN:0:15}..."
echo "📌 Новый токен:  ${NEW_TOKEN:0:15}..."

# Создаём бэкап
cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Бэкап создан"

# Заменяем токен
sed -i "s|TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$NEW_TOKEN|" "$ENV_FILE"
echo "✅ Токен обновлён в .env"

# Проверяем замену
CURRENT_TOKEN=$(grep "TELEGRAM_BOT_TOKEN" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ "$CURRENT_TOKEN" == "$NEW_TOKEN" ]; then
    echo "✅ Токен успешно заменён!"
else
    echo "❌ Ошибка: токен не заменился корректно"
    exit 1
fi

# Обновляем код из GitHub
echo ""
echo "📥 Обновление кода из GitHub..."
git pull origin main

# Перезапускаем бота
echo ""
echo "🔄 Перезапуск бота..."
sudo systemctl restart taxi-bot
sleep 3

# Проверяем статус
echo ""
echo "📊 Статус бота:"
sudo systemctl status taxi-bot --no-pager | head -20

# Проверяем логи на ошибки
echo ""
echo "📋 Последние записи логов:"
if [ -f "$PROJECT_DIR/logs/bot.log" ]; then
    tail -20 "$PROJECT_DIR/logs/bot.log"
else
    sudo journalctl -u taxi-bot -n 20 --no-pager
fi

echo ""
echo "========================================"
echo "✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo "========================================"
echo ""
echo "Проверьте работу бота в Telegram:"
echo "Отправьте /start новому боту"

