#!/usr/bin/env python3
"""
Скрипт для проверки профиля водителя
Использование: python check_driver.py <telegram_id>
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from database.db import SessionLocal
from bot.models.driver import Driver
from bot.models.user import User, UserRole

def check_driver_profile(telegram_id: int):
    """Проверяет профиль водителя"""
    db = SessionLocal()
    
    try:
        # Находим пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            return False
        
        print(f"👤 Пользователь:")
        print(f"   ID: {user.id}")
        print(f"   Имя: {user.full_name}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Роль: {user.role}")
        print(f"   Активен: {user.is_active}")
        
        # Проверяем профиль водителя
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        
        if not driver:
            print(f"\n❌ Профиль водителя не найден!")
            print(f"   Пользователь существует, но нет записи в таблице drivers")
            print(f"   Решение: используйте add_driver.py для создания профиля")
            return False
        
        print(f"\n🚗 Профиль водителя:")
        print(f"   ID: {driver.id}")
        print(f"   Автомобиль: {driver.car_model}")
        print(f"   Номер: {driver.car_number}")
        print(f"   Цвет: {driver.car_color or 'не указан'}")
        print(f"   Водительское удостоверение: {driver.license_number}")
        print(f"   Верифицирован: {driver.is_verified}")
        print(f"   Статус: {driver.status}")
        print(f"   Рейтинг: {driver.rating_avg:.1f} ({driver.rating_count} оценок)")
        print(f"   Поездок: {driver.completed_trips_count}")
        
        # Проверяем проблемы
        issues = []
        
        if user.role != UserRole.DRIVER:
            issues.append(f"⚠️  Роль пользователя: {user.role} (должно быть DRIVER)")
        
        if not driver.is_verified:
            issues.append("⚠️  Водитель не верифицирован")
        
        if user.id != driver.user_id:
            issues.append(f"⚠️  Несоответствие user_id: user.id={user.id}, driver.user_id={driver.user_id}")
        
        if issues:
            print(f"\n🔍 Обнаружены проблемы:")
            for issue in issues:
                print(f"   {issue}")
            print(f"\n💡 Решение: запустите fix_driver_profile.py для исправления")
        else:
            print(f"\n✅ Все проверки пройдены!")
            print(f"   Профиль водителя настроен правильно")
        
        return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python check_driver.py <telegram_id>")
        print("\nПример:")
        print("  python check_driver.py 7003530057")
        sys.exit(1)
    
    try:
        telegram_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Ошибка: {sys.argv[1]} не является числом")
        sys.exit(1)
    
    print(f"🔍 Проверка профиля водителя для Telegram ID: {telegram_id}\n")
    check_driver_profile(telegram_id)




