# Dockerfile для бота такси Жуково
FROM python:3.11-slim

# Метаданные
LABEL maintainer="Taxi Zhukovo"
LABEL description="Telegram bot for taxi service in Zhukovo"

# Рабочая директория
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Создание директорий для логов и данных
RUN mkdir -p /app/logs /app/data

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Точка входа
CMD ["python", "run.py"]

