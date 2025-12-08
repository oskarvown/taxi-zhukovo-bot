#!/bin/bash
# Простой скрипт обновления - можно запустить через Web SSH в Timeweb
# Скопируйте содержимое этого файла и вставьте в терминал на сервере

echo "🔄 Обновление бота такси Жуково..."

# Переход в директорию проекта
cd /opt/taxi-zhukovo || {
    echo "❌ Директория /opt/taxi-zhukovo не найдена!"
    exit 1
}

# Создание резервной копии БД
if [ -f "taxi_zhukovo.db" ]; then
    mkdir -p backups
    cp taxi_zhukovo.db "backups/taxi_zhukovo_$(date +%Y%m%d_%H%M%S).db"
    echo "✅ Резервная копия создана"
fi

# Остановка бота
echo "⏸ Остановка бота..."
systemctl stop taxi-bot 2>/dev/null || service taxi-bot stop 2>/dev/null || echo "⚠️ Бот не был запущен"

# Обновление из GitHub
echo "📥 Обновление кода из GitHub..."
git pull origin main

# Перезапуск бота
echo "▶️ Запуск бота..."
systemctl start taxi-bot 2>/dev/null || service taxi-bot start 2>/dev/null

# Проверка статуса
sleep 2
if systemctl is-active --quiet taxi-bot 2>/dev/null || service taxi-bot status >/dev/null 2>&1; then
    echo "✅ Бот успешно обновлен и запущен!"
    echo ""
    echo "Проверка статуса:"
    systemctl status taxi-bot --no-pager -l || service taxi-bot status
else
    echo "⚠️ Проверьте статус вручную:"
    echo "   systemctl status taxi-bot"
    echo "   или"
    echo "   service taxi-bot status"
fi

echo ""
echo "📋 Просмотр логов:"
echo "   journalctl -u taxi-bot -n 20 -f"
echo "   или"
echo "   tail -f /opt/taxi-zhukovo/logs/bot.log"










