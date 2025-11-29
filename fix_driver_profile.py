#!/usr/bin/env python3
"""
Скрипт для исправления профиля водителя
Использование: python fix_driver_profile.py <telegram_id>
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from database.db import SessionLocal
from bot.models.driver import Driver
from bot.models.user import User, UserRole

def fix_driver_profile(telegram_id: int):
    """Исправляет профиль водителя"""
    db = SessionLocal()
    
    try:
        # Находим пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            return False
        
        print(f"✓ Пользователь найден: {user.full_name} (ID: {user.id})")
        print(f"  Текущая роль: {user.role}")
        
        # Проверяем профиль водителя
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        
        if not driver:
            print(f"\n❌ Профиль водителя не найден для пользователя {user.full_name}")
            print("   Нужно создать профиль водителя или использовать add_driver.py")
            return False
        
        print(f"✓ Профиль водителя найден:")
        print(f"  Автомобиль: {driver.car_model} ({driver.car_number})")
        print(f"  Верифицирован: {driver.is_verified}")
        
        # Исправляем проблемы
        fixed = False
        
        # 1. Проверяем роль
        if user.role != UserRole.DRIVER:
            print(f"\n🔧 Исправление: меняем роль с {user.role} на DRIVER")
            user.role = UserRole.DRIVER
            fixed = True
        
        # 2. Проверяем верификацию
        if not driver.is_verified:
            print(f"\n🔧 Исправление: верифицируем водителя")
            driver.is_verified = True
            fixed = True
        
        if fixed:
            db.commit()
            print(f"\n✅ Профиль водителя исправлен!")
            print(f"   Пользователь: {user.full_name}")
            print(f"   Роль: {user.role}")
            print(f"   Верифицирован: {driver.is_verified}")
            return True
        else:
            print(f"\n✅ Профиль водителя в порядке!")
            print(f"   Роль: {user.role}")
            print(f"   Верифицирован: {driver.is_verified}")
            print(f"\n   Если водитель всё равно не видит меню, проверьте:")
            print(f"   1. Что бот запущен на сервере")
            print(f"   2. Что водитель отправил /start в боте")
            print(f"   3. Логи бота: journalctl -u taxi-bot -f")
            return True
            
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python fix_driver_profile.py <telegram_id>")
        print("\nПример:")
        print("  python fix_driver_profile.py 7003530057")
        sys.exit(1)
    
    try:
        telegram_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Ошибка: {sys.argv[1]} не является числом")
        sys.exit(1)
    
    print(f"🔍 Проверка профиля водителя для Telegram ID: {telegram_id}\n")
    success = fix_driver_profile(telegram_id)
    
    if success:
        print("\n💡 Следующие шаги:")
        print("   1. Перезапустите бота на сервере: systemctl restart taxi-bot")
        print("   2. Попросите водителя отправить /start в боте")
        print("   3. Проверьте логи, если проблема сохраняется")
    else:
        sys.exit(1)




