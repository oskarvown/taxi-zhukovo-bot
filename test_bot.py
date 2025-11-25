"""
Тестовый запуск бота с проверкой всех компонентов
"""
import sys
from pathlib import Path

print("=" * 70)
print("🔍 ДИАГНОСТИКА И ЗАПУСК БОТА")
print("=" * 70)
print()

# Проверка Python версии
print(f"✓ Python версия: {sys.version}")
print()

# Проверка файла .env
env_file = Path('.env')
if env_file.exists():
    print("✓ Файл .env найден")
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'ADMIN_TELEGRAM_IDS=6840100810' in content:
            print("✓ Ваш ID администратора настроен правильно")
        else:
            print("⚠️  Ваш ID администратора НЕ найден в .env!")
        if 'TELEGRAM_BOT_TOKEN' in content and 'your_bot_token_here' not in content:
            print("✓ Токен бота настроен")
        else:
            print("⚠️  Токен бота не настроен!")
else:
    print("❌ Файл .env НЕ НАЙДЕН!")
    print("   Запустите: python create_env.py")
    sys.exit(1)

print()

# Проверка зависимостей
print("📦 Проверка зависимостей...")
try:
    import telegram
    print("✓ python-telegram-bot установлен")
except ImportError:
    print("❌ python-telegram-bot НЕ установлен!")
    print("   Запустите: pip install -r requirements.txt")
    sys.exit(1)

try:
    import sqlalchemy
    print("✓ sqlalchemy установлен")
except ImportError:
    print("❌ sqlalchemy НЕ установлен!")
    print("   Запустите: pip install -r requirements.txt")
    sys.exit(1)

try:
    from pydantic_settings import BaseSettings
    print("✓ pydantic-settings установлен")
except ImportError:
    print("❌ pydantic-settings НЕ установлен!")
    print("   Запустите: pip install -r requirements.txt")
    sys.exit(1)

print()

# Проверка конфигурации
print("⚙️  Проверка конфигурации...")
try:
    from bot.config import settings
    print(f"✓ Токен бота: {settings.telegram_bot_token[:10]}...")
    print(f"✓ Админы: {settings.admin_ids}")
    print(f"✓ База данных: {settings.database_url}")
except Exception as e:
    print(f"❌ Ошибка загрузки конфигурации: {e}")
    sys.exit(1)

print()

# Проверка базы данных
print("💾 Проверка базы данных...")
try:
    from database.db import engine, Base
    from bot.models import User, Driver, Order
    
    # Создаем таблицы если их нет
    Base.metadata.create_all(bind=engine)
    print("✓ База данных инициализирована")
except Exception as e:
    print(f"❌ Ошибка базы данных: {e}")
    sys.exit(1)

print()

# Проверка обработчиков
print("🔌 Проверка обработчиков...")
try:
    from bot.handlers import register_user_handlers, register_driver_handlers, register_admin_handlers
    print("✓ Обработчики пользователей загружены")
    print("✓ Обработчики водителей загружены")
    print("✓ Обработчики администраторов загружены")
except Exception as e:
    print(f"❌ Ошибка загрузки обработчиков: {e}")
    sys.exit(1)

print()

# Проверка клавиатур
print("⌨️  Проверка клавиатур...")
try:
    from bot.utils import Keyboards
    test_keyboard = Keyboards.main_menu()
    print(f"✓ Главное меню: {len(test_keyboard.keyboard)} рядов кнопок")
    for row in test_keyboard.keyboard:
        print(f"  - {', '.join([btn.text for btn in row])}")
except Exception as e:
    print(f"❌ Ошибка клавиатур: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("=" * 70)
print()
print("🚀 ЗАПУСКАЮ БОТА...")
print()
print("⚠️  ВАЖНО:")
print("   • НЕ ЗАКРЫВАЙТЕ это окно - бот работает здесь!")
print("   • Для остановки нажмите Ctrl+C")
print("   • Ваш ID админа: 6840100810")
print()
print("=" * 70)
print()

# Запуск бота
try:
    from bot.main import main
    main()
except KeyboardInterrupt:
    print()
    print("=" * 70)
    print("⚠️  БОТ ОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ")
    print("=" * 70)
except Exception as e:
    print()
    print("=" * 70)
    print(f"❌ ОШИБКА ПРИ ЗАПУСКЕ БОТА: {e}")
    print("=" * 70)
    import traceback
    traceback.print_exc()

