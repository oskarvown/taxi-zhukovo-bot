"""
Простой скрипт для создания .env файла с правильными настройками
"""
import os

# Содержимое .env файла
env_content = """# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8447881195:AAFvBWR45SFXSy-lyeXfxnJWnVXrtAVVj1M
TELEGRAM_WEBHOOK_URL=

# Database Configuration
DATABASE_URL=sqlite:///./taxi_zhukovo.db

# Application Settings
DEBUG=False
LOG_LEVEL=INFO

# Admin Configuration - ВАШ ID УЖЕ ДОБАВЛЕН!
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

# Создаём файл .env
try:
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("=" * 70)
    print("✅ ФАЙЛ .ENV УСПЕШНО СОЗДАН!")
    print("=" * 70)
    print()
    print("✅ Ваш ID администратора: 6840100810 - УЖЕ ДОБАВЛЕН!")
    print("✅ Токен бота: настроен")
    print()
    print("🚀 ТЕПЕРЬ ЗАПУСТИТЕ БОТА:")
    print("   python run.py")
    print()
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Ошибка при создании .env: {e}")
    print()
    print("Попробуйте создать файл .env вручную с содержимым:")
    print(env_content)

