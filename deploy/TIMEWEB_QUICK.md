# ⚡ Быстрый деплой на Timeweb - Шпаргалка

## 🎯 Быстрая команда (копипаста)

```bash
# 1. Подключение к серверу
ssh root@ВАШ_IP

# 2. Установка пакетов
apt update && apt install -y python3 python3-venv python3-pip git nano

# 3. Клонирование проекта
cd /opt && git clone https://github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo

# 4. Создание .env
cd taxi-zhukovo
nano .env
# (вставьте содержимое из шага 5 ниже)

# 5. Деплой
chmod +x deploy/deploy.sh && ./deploy/deploy.sh

# 6. Запуск
systemctl start taxi-bot && systemctl enable taxi-bot

# 7. Проверка
systemctl status taxi-bot
journalctl -u taxi-bot -f
```

---

## 📝 Содержимое .env файла

Скопируйте и вставьте в `nano .env`:

```env
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
```

**Сохранение:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 🔄 Обновление бота

```bash
cd /opt/taxi-zhukovo
./deploy/update.sh main
```

---

## 📊 Полезные команды

```bash
# Статус
systemctl status taxi-bot

# Логи
journalctl -u taxi-bot -f

# Перезапуск
systemctl restart taxi-bot
```

---

**Полная инструкция:** [TIMEWEB_DEPLOY.md](./TIMEWEB_DEPLOY.md)






