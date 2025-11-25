"""
Скрипт для добавления администратора в файл .env
Запуск: python add_admin.py
"""
import os
from pathlib import Path

def main():
    print("=" * 70)
    print("🔧 НАСТРОЙКА АДМИНИСТРАТОРА ДЛЯ БОТА «ТАКСИ ЖУКОВО+»")
    print("=" * 70)
    print()
    
    # ID администратора
    ADMIN_ID = "6840100810"
    
    # Путь к .env файлу
    env_file = Path('.env')
    
    # Проверяем, существует ли .env
    if not env_file.exists():
        print("⚠️  Файл .env не найден. Создаю новый файл...")
        
        # Содержимое .env с админом
        env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8447881195:AAFvBWR45SFXSy-lyeXfxnJWnVXrtAVVj1M
TELEGRAM_WEBHOOK_URL=

# Database Configuration
DATABASE_URL=sqlite:///./taxi_zhukovo.db

# Application Settings
DEBUG=False
LOG_LEVEL=INFO

# Admin Configuration (comma-separated Telegram IDs)
ADMIN_TELEGRAM_IDS={ADMIN_ID}

# Pricing Configuration
BASE_PRICE=100.0
PRICE_PER_KM=25.0
MIN_PRICE=150.0

# Service Area Configuration (Жуково coordinates)
SERVICE_AREA_LAT=55.5833
SERVICE_AREA_LON=36.7500
SERVICE_RADIUS_KM=50.0
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ Файл .env создан успешно!")
        print(f"✅ Администратор с ID {ADMIN_ID} добавлен!")
    else:
        print("✅ Файл .env уже существует")
        
        # Читаем текущий .env
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, есть ли уже ADMIN_TELEGRAM_IDS
        if 'ADMIN_TELEGRAM_IDS=' in content:
            lines = content.split('\n')
            updated = False
            
            for i, line in enumerate(lines):
                if line.startswith('ADMIN_TELEGRAM_IDS='):
                    current_value = line.split('=', 1)[1].strip()
                    
                    if not current_value or current_value == '':
                        # Добавляем первого админа
                        lines[i] = f'ADMIN_TELEGRAM_IDS={ADMIN_ID}'
                        print(f"✅ ID {ADMIN_ID} добавлен как администратор")
                        updated = True
                    elif ADMIN_ID in current_value.split(','):
                        print(f"ℹ️  ID {ADMIN_ID} уже в списке администраторов")
                        updated = False
                    else:
                        # Добавляем к существующим
                        lines[i] = f'ADMIN_TELEGRAM_IDS={current_value},{ADMIN_ID}'
                        print(f"✅ ID {ADMIN_ID} добавлен к существующим админам")
                        updated = True
                    break
            
            if updated:
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                print("✅ Файл .env обновлён")
        else:
            # Добавляем строку с админом
            content += f'\n\n# Admin Configuration\nADMIN_TELEGRAM_IDS={ADMIN_ID}\n'
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ ID {ADMIN_ID} добавлен в файл .env")
    
    print()
    print("=" * 70)
    print("🎉 НАСТРОЙКА ЗАВЕРШЕНА!")
    print("=" * 70)
    print()
    print("📋 ЧТО ДАЛЬШЕ:")
    print()
    print("   1. Запустите бота:")
    print("      python run.py")
    print()
    print("   2. Откройте бота в Telegram и отправьте:")
    print("      /start")
    print("      /admin_stats")
    print()
    print("   3. Если увидите статистику — вы администратор! ✅")
    print()
    print("📖 Полная документация:")
    print("   - ФУНКЦИОНАЛЬНОСТЬ_РОЛЕЙ.md — обзор всех функций")
    print("   - НАСТРОЙКА_АДМИНА.md — инструкция по настройке")
    print()
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nПопробуйте создать файл .env вручную:")
        print("1. Создайте файл .env в корне проекта")
        print("2. Скопируйте содержимое из .env.example")
        print("3. Замените ADMIN_TELEGRAM_IDS= на ADMIN_TELEGRAM_IDS=6840100810")

