# 🔧 Исправление проблемы с деплоем

## Проблема
Скрипт пытался скопировать файлы в ту же директорию, что вызывало ошибку.

## ✅ Решение

Скрипт исправлен! Теперь он правильно определяет, находится ли проект уже в нужной директории.

### На сервере выполните:

```bash
# 1. Обновите код из GitHub
cd /opt/taxi-zhukovo
git pull origin main

# 2. Запустите деплой снова
./deploy/deploy.sh
```

**Или выполните всё вручную:**

```bash
cd /opt/taxi-zhukovo

# Создание .env (если еще не создан)
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

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Настройка прав
chown -R taxi:taxi /opt/taxi-zhukovo
chmod +x /opt/taxi-zhukovo/run.py

# Установка systemd service
cp deploy/taxi-bot.service /etc/systemd/system/taxi-bot.service
systemctl daemon-reload

# Запуск бота
systemctl start taxi-bot
systemctl enable taxi-bot
systemctl status taxi-bot
```

---

## 🚀 Быстрый вариант (после обновления скрипта)

```bash
cd /opt/taxi-zhukovo
git pull origin main
./deploy/deploy.sh
systemctl start taxi-bot
systemctl enable taxi-bot
```

---

**Скрипт теперь работает правильно!**














