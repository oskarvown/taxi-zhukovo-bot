#!/bin/bash
# Скрипт для быстрого деплоя на Timeweb
# IP: 195.133.73.49

echo "🚀 Деплой бота такси Жуково на Timeweb"
echo "IP сервера: 195.133.73.49"
echo ""
echo "Выполните эти команды на сервере:"
echo ""
echo "1. Подключение:"
echo "   ssh root@195.133.73.49"
echo ""
echo "2. После подключения выполните:"
echo ""
echo "   # Установка пакетов"
echo "   apt update && apt install -y python3 python3-venv python3-pip git nano"
echo ""
echo "   # Клонирование проекта"
echo "   cd /opt && git clone https://github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo"
echo ""
echo "   # Создание .env файла"
echo "   cd taxi-zhukovo"
echo "   nano .env"
echo ""
echo "   # (Вставьте содержимое .env из файла ниже)"
echo ""
echo "   # Деплой"
echo "   chmod +x deploy/deploy.sh && ./deploy/deploy.sh"
echo ""
echo "   # Запуск"
echo "   systemctl start taxi-bot && systemctl enable taxi-bot"
echo ""
echo "   # Проверка"
echo "   systemctl status taxi-bot"
echo ""














