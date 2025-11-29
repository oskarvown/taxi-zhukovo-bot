#!/bin/bash
# Автоматический деплой на Timeweb сервер
# IP: 195.133.73.49

SERVER_IP="195.133.73.49"
SERVER_USER="root"
SERVER_PASS="u1,mSm4G3gGEXH"

echo "🚀 Автоматический деплой бота на Timeweb"
echo "IP: $SERVER_IP"
echo ""

# Установка sshpass если нужно
if ! command -v sshpass &> /dev/null; then
    echo "⚠️  sshpass не установлен. Установите его:"
    echo "   Mac: brew install hudochenkov/sshpass/sshpass"
    echo "   Linux: sudo apt install sshpass"
    echo ""
    echo "Или выполните команды вручную через Web SSH в панели Timeweb"
    exit 1
fi

echo "📦 Шаг 1: Установка пакетов..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
apt update && apt install -y python3 python3-venv python3-pip git nano
ENDSSH

echo "✅ Пакеты установлены"
echo ""

echo "📦 Шаг 2: Клонирование проекта..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd /opt
if [ -d "taxi-zhukovo" ]; then
    echo "Директория уже существует, обновляю..."
    cd taxi-zhukovo
    git pull origin main
else
    git clone https://github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo
    cd taxi-zhukovo
fi
ENDSSH

echo "✅ Проект склонирован"
echo ""

echo "📝 Шаг 3: Создание .env файла..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd /opt/taxi-zhukovo
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=8447881195:AAFvBWR45SFXSy-lyeXfxnJWnVXrtAVVj1M
TELEGRAM_WEBHOOK_URL=
DATABASE_URL=sqlite:///./taxi_zhukovo.db
DEBUG=False
LOG_LEVEL=INFO
ADMIN_TELEGRAM_IDS=6840100810
BASE_PRICE=100.0
PRICE_PER_KM=25.0
MIN_PRICE=150.0
SERVICE_AREA_LAT=55.5833
SERVICE_AREA_LON=36.7500
SERVICE_RADIUS_KM=50.0
EOF
ENDSSH

echo "✅ .env файл создан"
echo ""

echo "🚀 Шаг 4: Запуск деплоя..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd /opt/taxi-zhukovo
chmod +x deploy/deploy.sh
./deploy/deploy.sh
ENDSSH

echo "✅ Деплой завершен"
echo ""

echo "▶️  Шаг 5: Запуск бота..."
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
systemctl start taxi-bot
systemctl enable taxi-bot
systemctl status taxi-bot
ENDSSH

echo ""
echo "✅ Готово! Бот должен быть запущен."
echo ""
echo "Проверьте логи:"
echo "ssh root@195.133.73.49 'journalctl -u taxi-bot -f'"






