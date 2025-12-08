#!/bin/bash
# Детальная проверка состояния бота на сервере

echo "🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА БОТА"
echo "=============================="
echo ""

# 1. Проверка статуса службы
echo "1️⃣ Статус службы systemd:"
echo "------------------------"
systemctl status taxi-bot --no-pager -l | head -30
echo ""

# 2. Проверка процесса
echo "2️⃣ Запущенные процессы Python:"
echo "-------------------------------"
ps aux | grep -E "python.*run.py|python.*bot" | grep -v grep
echo ""

# 3. Проверка файлов логов
echo "3️⃣ Проверка файлов логов:"
echo "------------------------"
if [ -f /opt/taxi-zhukovo/logs/bot.log ]; then
    echo "✅ bot.log существует"
    echo "   Размер: $(du -h /opt/taxi-zhukovo/logs/bot.log | cut -f1)"
    echo "   Последнее изменение: $(stat -c %y /opt/taxi-zhukovo/logs/bot.log)"
    echo ""
    echo "   Последние 50 строк bot.log:"
    echo "   ---------------------------"
    tail -50 /opt/taxi-zhukovo/logs/bot.log
else
    echo "❌ bot.log НЕ НАЙДЕН!"
    echo "   Проверьте права доступа к /opt/taxi-zhukovo/logs/"
fi
echo ""

if [ -f /opt/taxi-zhukovo/logs/bot_error.log ]; then
    echo "✅ bot_error.log существует"
    echo "   Размер: $(du -h /opt/taxi-zhukovo/logs/bot_error.log | cut -f1)"
    echo "   Последнее изменение: $(stat -c %y /opt/taxi-zhukovo/logs/bot_error.log)"
    if [ -s /opt/taxi-zhukovo/logs/bot_error.log ]; then
        echo ""
        echo "   Последние 50 строк bot_error.log:"
        echo "   ---------------------------------"
        tail -50 /opt/taxi-zhukovo/logs/bot_error.log
    else
        echo "   Файл пуст (нет ошибок)"
    fi
else
    echo "❌ bot_error.log НЕ НАЙДЕН!"
fi
echo ""

# 4. Проверка директории логов
echo "4️⃣ Проверка директории логов:"
echo "----------------------------"
ls -lah /opt/taxi-zhukovo/logs/ 2>/dev/null || echo "❌ Директория /opt/taxi-zhukovo/logs/ не существует!"
echo ""

# 5. Проверка прав доступа
echo "5️⃣ Проверка прав доступа:"
echo "------------------------"
if [ -d /opt/taxi-zhukovo/logs ]; then
    ls -ld /opt/taxi-zhukovo/logs
    echo ""
    echo "Права на файлы:"
    ls -l /opt/taxi-zhukovo/logs/*.log 2>/dev/null || echo "Нет файлов логов"
else
    echo "❌ Директория не существует, создаем..."
    mkdir -p /opt/taxi-zhukovo/logs
    chown taxi:taxi /opt/taxi-zhukovo/logs
    chmod 755 /opt/taxi-zhukovo/logs
    echo "✅ Директория создана"
fi
echo ""

# 6. Проверка .env файла
echo "6️⃣ Проверка конфигурации:"
echo "------------------------"
if [ -f /opt/taxi-zhukovo/.env ]; then
    echo "✅ .env существует"
    echo "   Проверка токена (первые 20 символов):"
    grep TELEGRAM_BOT_TOKEN /opt/taxi-zhukovo/.env | sed 's/\(.\{20\}\).*/\1.../'
    echo "   LOG_LEVEL:"
    grep LOG_LEVEL /opt/taxi-zhukovo/.env || echo "   LOG_LEVEL не установлен"
else
    echo "❌ .env НЕ НАЙДЕН!"
fi
echo ""

# 7. Попытка запуска вручную (тест)
echo "7️⃣ Тест запуска бота:"
echo "--------------------"
cd /opt/taxi-zhukovo
if [ -f venv/bin/python ]; then
    echo "✅ Виртуальное окружение найдено"
    echo "   Проверка импортов..."
    venv/bin/python -c "from bot.main import main; print('✅ Импорты успешны')" 2>&1 | head -20
else
    echo "❌ Виртуальное окружение не найдено!"
fi
echo ""

# 8. Проверка базы данных
echo "8️⃣ Проверка базы данных:"
echo "------------------------"
if [ -f /opt/taxi-zhukovo/taxi_zhukovo.db ]; then
    echo "✅ База данных существует"
    echo "   Размер: $(du -h /opt/taxi-zhukovo/taxi_zhukovo.db | cut -f1)"
    echo "   Последнее изменение: $(stat -c %y /opt/taxi-zhukovo/taxi_zhukovo.db)"
else
    echo "❌ База данных НЕ НАЙДЕНА!"
fi
echo ""

# 9. Проверка последних логов systemd с деталями
echo "9️⃣ Последние логи systemd (с деталями):"
echo "---------------------------------------"
journalctl -u taxi-bot -n 200 --no-pager | grep -v "systemd\[1\]" | tail -50
echo ""

echo "=============================="
echo "✅ Диагностика завершена"
echo ""
echo "💡 Если бот не работает, попробуйте:"
echo "   1. systemctl restart taxi-bot"
echo "   2. systemctl status taxi-bot"
echo "   3. journalctl -u taxi-bot -f (для просмотра в реальном времени)"







