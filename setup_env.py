"""Скрипт для создания файла .env"""
import os

env_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8447881195:AAFvBWR45SFXSy-lyeXfxnJWnVXrtAVVj1M
TELEGRAM_WEBHOOK_URL=

# Database Configuration
DATABASE_URL=sqlite:///./taxi_zhukovo.db

# Application Settings
DEBUG=False
LOG_LEVEL=INFO

# Admin Configuration (comma-separated Telegram IDs)
ADMIN_TELEGRAM_IDS=6840100810

# Pricing Configuration
BASE_PRICE=100.0
PRICE_PER_KM=25.0
MIN_PRICE=150.0

# Service Area Configuration (Жуково coordinates)
SERVICE_AREA_LAT=55.5833
SERVICE_AREA_LON=36.7500
SERVICE_RADIUS_KM=50.0
"""

# Создаем файл .env в текущей директории
env_path = os.path.join(os.path.dirname(__file__), '.env')
with open(env_path, 'w', encoding='utf-8') as f:
    f.write(env_content)

print(f"✅ Файл .env успешно создан: {env_path}")
print("\nТеперь можно запустить бота командой:")
print("python run.py")

