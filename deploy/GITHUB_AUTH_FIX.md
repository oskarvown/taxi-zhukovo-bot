# 🔐 Решение проблемы аутентификации GitHub

## Проблема
GitHub больше не поддерживает парольную аутентификацию. Нужен **Personal Access Token** или **SSH ключи**.

---

## ✅ Решение 1: Personal Access Token (рекомендуется)

### Шаг 1: Создайте токен на GitHub

1. Зайдите на https://github.com
2. Нажмите на ваш аватар (правый верхний угол)
3. Выберите **Settings**
4. В левом меню выберите **Developer settings**
5. Выберите **Personal access tokens** → **Tokens (classic)**
6. Нажмите **Generate new token** → **Generate new token (classic)**
7. Заполните:
   - **Note**: `Taxi Bot Deploy`
   - **Expiration**: выберите срок (например, 90 days)
   - **Scopes**: отметьте `repo` (полный доступ к репозиториям)
8. Нажмите **Generate token**
9. **Скопируйте токен** (он показывается только один раз!)

### Шаг 2: Используйте токен вместо пароля

На сервере выполните:

```bash
cd /opt
git clone https://oskarvown:ВАШ_ТОКЕН@github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo
```

**Или:**
```bash
cd /opt
git clone https://github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo
# Когда попросит Username: введите oskarvown
# Когда попросит Password: вставьте ваш токен (НЕ пароль!)
```

---

## ✅ Решение 2: Сделать репозиторий публичным (временно)

Если репозиторий можно сделать публичным:

1. Зайдите на https://github.com/oskarvown/taxi-zhukovo-bot
2. Нажмите **Settings**
3. Прокрутите вниз до **Danger Zone**
4. Нажмите **Change visibility** → **Make public**
5. Теперь можно клонировать без аутентификации:

```bash
cd /opt
git clone https://github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo
```

**После деплоя можно вернуть приватность.**

---

## ✅ Решение 3: SSH ключи (для постоянного использования)

### На сервере:

```bash
# 1. Генерация SSH ключа
ssh-keygen -t ed25519 -C "deploy@taxi-bot"
# Нажмите Enter для всех запросов

# 2. Просмотр публичного ключа
cat ~/.ssh/id_ed25519.pub
```

### На GitHub:

1. Зайдите на https://github.com/oskarvown/taxi-zhukovo-bot
2. Нажмите **Settings** → **Deploy keys**
3. Нажмите **Add deploy key**
4. **Title**: `Timeweb Server`
5. **Key**: вставьте содержимое из `cat ~/.ssh/id_ed25519.pub`
6. Отметьте **Allow write access** (если нужно)
7. Нажмите **Add key**

### Клонирование через SSH:

```bash
cd /opt
git clone git@github.com:oskarvown/taxi-zhukovo-bot.git taxi-zhukovo
```

---

## 🚀 Быстрое решение (рекомендую)

**Самый быстрый способ - Personal Access Token:**

1. Создайте токен на GitHub (5 минут)
2. На сервере выполните:

```bash
cd /opt
git clone https://oskarvown:ВАШ_ТОКЕН@github.com/oskarvown/taxi-zhukovo-bot.git taxi-zhukovo
cd taxi-zhukovo
```

**Или сделайте репозиторий публичным временно** - это займет 30 секунд!

---

## 📝 После успешного клонирования

Продолжите деплой:

```bash
cd /opt/taxi-zhukovo

# Создание .env
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

# Деплой
chmod +x deploy/deploy.sh
./deploy/deploy.sh

# Запуск
systemctl start taxi-bot
systemctl enable taxi-bot
systemctl status taxi-bot
```

---

**Рекомендую использовать Personal Access Token - это самый простой и безопасный способ!**






