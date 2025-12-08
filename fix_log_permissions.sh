#!/bin/bash
# Исправление прав доступа к файлам логов

echo "🔧 Исправление прав доступа к файлам логов"
echo "=========================================="

# Исправляем права на директорию логов
if [ -d /opt/taxi-zhukovo/logs ]; then
    chown -R taxi:taxi /opt/taxi-zhukovo/logs
    chmod 755 /opt/taxi-zhukovo/logs
    echo "✅ Права на директорию исправлены"
else
    mkdir -p /opt/taxi-zhukovo/logs
    chown -R taxi:taxi /opt/taxi-zhukovo/logs
    chmod 755 /opt/taxi-zhukovo/logs
    echo "✅ Директория создана с правильными правами"
fi

# Исправляем права на файлы логов
if [ -f /opt/taxi-zhukovo/logs/bot.log ]; then
    chown taxi:taxi /opt/taxi-zhukovo/logs/bot.log
    chmod 644 /opt/taxi-zhukovo/logs/bot.log
    echo "✅ Права на bot.log исправлены"
fi

if [ -f /opt/taxi-zhukovo/logs/bot_error.log ]; then
    chown taxi:taxi /opt/taxi-zhukovo/logs/bot_error.log
    chmod 644 /opt/taxi-zhukovo/logs/bot_error.log
    echo "✅ Права на bot_error.log исправлены"
fi

echo ""
echo "✅ Готово! Теперь бот сможет писать в логи"
echo ""
echo "💡 Перезапустите бота:"
echo "   systemctl restart taxi-bot"







