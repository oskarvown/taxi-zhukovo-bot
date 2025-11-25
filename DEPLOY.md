# 🚀 Руководство по деплою и обновлению бота

Это руководство поможет вам разместить бота на сервере и настроить процесс обновлений.

## 📋 Содержание

1. [Варианты деплоя](#варианты-деплоя)
2. [Systemd (рекомендуется)](#вариант-1-systemd-рекомендуется)
3. [Docker](#вариант-2-docker)
4. [Обновление бота](#обновление-бота)
5. [Мониторинг и логи](#мониторинг-и-логи)
6. [Решение проблем](#решение-проблем)

---

## Варианты деплоя

### Вариант 1: Systemd (рекомендуется)

**Преимущества:**
- ✅ Простота настройки
- ✅ Автоматический перезапуск при сбоях
- ✅ Интеграция с системой логирования
- ✅ Минимальное потребление ресурсов

**Недостатки:**
- ⚠️ Требует Linux сервер
- ⚠️ Нужны права root/sudo

### Вариант 2: Docker

**Преимущества:**
- ✅ Изоляция окружения
- ✅ Легкое масштабирование
- ✅ Простое обновление
- ✅ Работает на любой ОС с Docker

**Недостатки:**
- ⚠️ Требует больше ресурсов
- ⚠️ Нужна установка Docker

---

## Вариант 1: Systemd (рекомендуется)

### Требования

- Linux сервер (Ubuntu/Debian/CentOS)
- Python 3.10+
- Права root или sudo

### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и необходимых пакетов
sudo apt install -y python3 python3-venv python3-pip git
```

### Шаг 2: Перенос файлов на сервер

**Вариант A: Через Git (рекомендуется)**

```bash
# На сервере
cd /opt
sudo git clone <ваш_repo_url> taxi-zhukovo
cd taxi-zhukovo
```

**Вариант B: Через SCP/SFTP**

```bash
# С локального компьютера
scp -r /Volumes/PortableSSD/TAXI_ЖУКОВО user@server:/opt/taxi-zhukovo
```

**Вариант C: Через архив**

```bash
# На локальном компьютере
tar -czf taxi-bot.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='*.db' .

# На сервере
scp taxi-bot.tar.gz user@server:/tmp/
ssh user@server
cd /opt
sudo tar -xzf /tmp/taxi-bot.tar.gz -C taxi-zhukovo
```

### Шаг 3: Первоначальный деплой

```bash
# Переход в директорию проекта
cd /opt/taxi-zhukovo

# Запуск скрипта деплоя
sudo chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

Скрипт автоматически:
- ✅ Создаст пользователя `taxi`
- ✅ Создаст виртуальное окружение
- ✅ Установит зависимости
- ✅ Настроит systemd service
- ✅ Настроит права доступа

### Шаг 4: Настройка .env файла

```bash
# Создание .env файла
sudo nano /opt/taxi-zhukovo/.env
```

Минимальные настройки:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_TELEGRAM_IDS=123456789
DATABASE_URL=sqlite:///./taxi_zhukovo.db
LOG_LEVEL=INFO
```

### Шаг 5: Запуск бота

```bash
# Запуск бота
sudo systemctl start taxi-bot

# Включение автозапуска при загрузке системы
sudo systemctl enable taxi-bot

# Проверка статуса
sudo systemctl status taxi-bot
```

### Управление ботом

```bash
# Запуск
sudo systemctl start taxi-bot

# Остановка
sudo systemctl stop taxi-bot

# Перезапуск
sudo systemctl restart taxi-bot

# Статус
sudo systemctl status taxi-bot

# Просмотр логов
sudo journalctl -u taxi-bot -f
```

---

## Вариант 2: Docker

### Требования

- Docker и Docker Compose установлены
- Минимум 512MB RAM

### Шаг 1: Установка Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt install -y docker-compose

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### Шаг 2: Подготовка файлов

```bash
# Копирование проекта на сервер
cd /opt
git clone <ваш_repo_url> taxi-zhukovo
cd taxi-zhukovo
```

### Шаг 3: Настройка .env

```bash
# Создание .env файла
cp .env.example .env
nano .env
```

### Шаг 4: Запуск через Docker Compose

```bash
cd deploy
docker-compose up -d
```

### Управление

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Логи
docker-compose logs -f

# Статус
docker-compose ps
```

---

## Обновление бота

### Systemd вариант

#### Способ 1: Автоматический скрипт (рекомендуется)

```bash
# На сервере
cd /opt/taxi-zhukovo
sudo chmod +x deploy/update.sh
sudo ./deploy/update.sh
```

Скрипт автоматически:
- ✅ Создаст резервную копию БД
- ✅ Остановит бота
- ✅ Обновит код (из git или архива)
- ✅ Обновит зависимости
- ✅ Запустит бота

#### Способ 2: Ручное обновление через Git

```bash
# Остановка бота
sudo systemctl stop taxi-bot

# Создание резервной копии БД
sudo cp /opt/taxi-zhukovo/taxi_zhukovo.db /opt/taxi-zhukovo/backups/taxi_zhukovo_$(date +%Y%m%d_%H%M%S).db

# Обновление кода
cd /opt/taxi-zhukovo
sudo -u taxi git pull origin main

# Обновление зависимостей
sudo -u taxi /opt/taxi-zhukovo/venv/bin/pip install -r requirements.txt

# Запуск бота
sudo systemctl start taxi-bot

# Проверка статуса
sudo systemctl status taxi-bot
```

#### Способ 3: Обновление через архив

```bash
# На локальном компьютере: создание архива обновления
tar -czf update_files.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='*.db' --exclude='.env' .

# Копирование на сервер
scp update_files.tar.gz user@server:/tmp/

# На сервере: обновление
sudo systemctl stop taxi-bot
sudo cp /opt/taxi-zhukovo/taxi_zhukovo.db /opt/taxi-zhukovo/backups/
sudo tar -xzf /tmp/update_files.tar.gz -C /opt/taxi-zhukovo --exclude='.env' --exclude='*.db'
sudo -u taxi /opt/taxi-zhukovo/venv/bin/pip install -r /opt/taxi-zhukovo/requirements.txt
sudo systemctl start taxi-bot
```

### Docker вариант

```bash
cd /opt/taxi-zhukovo/deploy
sudo chmod +x update-docker.sh
sudo ./update-docker.sh
```

Или вручную:

```bash
# Остановка
docker-compose down

# Обновление кода (если через git)
cd /opt/taxi-zhukovo
git pull origin main

# Пересборка образа
cd deploy
docker-compose build --no-cache

# Запуск
docker-compose up -d
```

---

## Мониторинг и логи

### Systemd

```bash
# Просмотр логов в реальном времени
sudo journalctl -u taxi-bot -f

# Последние 100 строк логов
sudo journalctl -u taxi-bot -n 100

# Логи за сегодня
sudo journalctl -u taxi-bot --since today

# Логи с ошибками
sudo journalctl -u taxi-bot -p err

# Логи в файл проекта
tail -f /opt/taxi-zhukovo/logs/bot.log
```

### Docker

```bash
# Все логи
docker-compose logs

# Логи в реальном времени
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100

# Логи конкретного сервиса
docker-compose logs taxi-bot
```

---

## Решение проблем

### Бот не запускается

1. **Проверьте логи:**
   ```bash
   sudo journalctl -u taxi-bot -n 50
   ```

2. **Проверьте .env файл:**
   ```bash
   sudo cat /opt/taxi-zhukovo/.env
   ```

3. **Проверьте токен бота:**
   - Убедитесь, что токен правильный
   - Проверьте, что бот не запущен на другом сервере

4. **Проверьте права доступа:**
   ```bash
   sudo chown -R taxi:taxi /opt/taxi-zhukovo
   ```

### Бот падает с ошибкой Conflict

Это означает, что бот уже запущен в другом месте. Решение:

1. Найдите все запущенные процессы:
   ```bash
   ps aux | grep run.py
   ```

2. Остановите все процессы:
   ```bash
   sudo pkill -f run.py
   ```

3. Подождите 1-2 минуты и перезапустите:
   ```bash
   sudo systemctl restart taxi-bot
   ```

### База данных заблокирована

```bash
# Остановка бота
sudo systemctl stop taxi-bot

# Проверка блокировок
sudo lsof /opt/taxi-zhukovo/taxi_zhukovo.db

# Если нужно, принудительное завершение процессов
sudo pkill -f run.py

# Восстановление из резервной копии (если нужно)
sudo cp /opt/taxi-zhukovo/backups/taxi_zhukovo_YYYYMMDD_HHMMSS.db /opt/taxi-zhukovo/taxi_zhukovo.db
```

### Проблемы с зависимостями

```bash
# Пересоздание виртуального окружения
sudo systemctl stop taxi-bot
cd /opt/taxi-zhukovo
sudo rm -rf venv
sudo -u taxi python3 -m venv venv
sudo -u taxi venv/bin/pip install --upgrade pip
sudo -u taxi venv/bin/pip install -r requirements.txt
sudo systemctl start taxi-bot
```

### Проверка здоровья бота

Создайте простой скрипт мониторинга:

```bash
#!/bin/bash
# /opt/taxi-zhukovo/deploy/health-check.sh

if ! systemctl is-active --quiet taxi-bot; then
    echo "Бот не запущен! Перезапуск..."
    systemctl restart taxi-bot
    # Можно добавить отправку уведомления администратору
fi
```

Добавьте в crontab для проверки каждые 5 минут:

```bash
sudo crontab -e
# Добавьте строку:
*/5 * * * * /opt/taxi-zhukovo/deploy/health-check.sh
```

---

## Рекомендации по безопасности

1. **Огненная стена:**
   ```bash
   sudo ufw allow 22/tcp  # SSH
   sudo ufw enable
   ```

2. **Регулярные резервные копии:**
   ```bash
   # Добавьте в crontab для ежедневных бэкапов
   0 2 * * * cp /opt/taxi-zhukovo/taxi_zhukovo.db /opt/taxi-zhukovo/backups/taxi_zhukovo_$(date +\%Y\%m\%d).db
   ```

3. **Обновление системы:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Мониторинг дискового пространства:**
   ```bash
   df -h
   ```

---

## Быстрая справка команд

### Systemd

| Действие | Команда |
|----------|---------|
| Запуск | `sudo systemctl start taxi-bot` |
| Остановка | `sudo systemctl stop taxi-bot` |
| Перезапуск | `sudo systemctl restart taxi-bot` |
| Статус | `sudo systemctl status taxi-bot` |
| Логи | `sudo journalctl -u taxi-bot -f` |
| Автозапуск | `sudo systemctl enable taxi-bot` |

### Docker

| Действие | Команда |
|----------|---------|
| Запуск | `docker-compose up -d` |
| Остановка | `docker-compose down` |
| Перезапуск | `docker-compose restart` |
| Логи | `docker-compose logs -f` |
| Статус | `docker-compose ps` |

---

## Поддержка

При возникновении проблем:
1. Проверьте логи
2. Убедитесь, что все зависимости установлены
3. Проверьте права доступа к файлам
4. Убедитесь, что .env файл настроен правильно

---

**Удачного деплоя! 🚀**

