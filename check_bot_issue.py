#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для диагностики проблемы с проверкой на бота
Проверяет состояние пользователей и водителей в базе данных
"""

from database.db import SessionLocal
from bot.models import User, Driver, UserRole

def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ С ПРОВЕРКОЙ НА БОТА")
        print("=" * 70)
        print()
        
        # Проверка всех пользователей
        all_users = db.query(User).all()
        print(f"📊 Всего пользователей в базе: {len(all_users)}")
        print()
        
        # Пользователи без телефона
        users_without_phone = db.query(User).filter(User.phone_number == None).all()
        print(f"⚠️ Пользователей БЕЗ телефона: {len(users_without_phone)}")
        if users_without_phone:
            print("   Список:")
            for user in users_without_phone[:10]:  # Показываем первые 10
                role_str = user.role.value if user.role else "unknown"
                print(f"   - ID: {user.telegram_id}, Имя: {user.full_name}, Роль: {role_str}")
            if len(users_without_phone) > 10:
                print(f"   ... и еще {len(users_without_phone) - 10} пользователей")
        print()
        
        # Водители
        drivers = db.query(Driver).all()
        print(f"🚗 Всего водителей: {len(drivers)}")
        
        drivers_without_phone = []
        for driver in drivers:
            user = db.query(User).filter(User.id == driver.user_id).first()
            if user and not user.phone_number:
                drivers_without_phone.append((driver, user))
        
        print(f"⚠️ Водителей БЕЗ телефона: {len(drivers_without_phone)}")
        if drivers_without_phone:
            print("   Список:")
            for driver, user in drivers_without_phone[:10]:
                verified = "✅" if driver.is_verified else "❌"
                print(f"   - {verified} Telegram ID: {user.telegram_id}, Имя: {user.full_name}")
                print(f"     Авто: {driver.car_model} ({driver.car_number})")
            if len(drivers_without_phone) > 10:
                print(f"   ... и еще {len(drivers_without_phone) - 10} водителей")
        print()
        
        # Забаненные пользователи
        banned_users = db.query(User).filter(User.is_banned == True).all()
        print(f"⛔ Забаненных пользователей: {len(banned_users)}")
        if banned_users:
            print("   Список:")
            for user in banned_users[:10]:
                print(f"   - ID: {user.telegram_id}, Имя: {user.full_name}, Телефон: {user.phone_number or 'нет'}")
        print()
        
        # Статистика по ролям
        print("📈 Статистика по ролям:")
        for role in UserRole:
            count = db.query(User).filter(User.role == role).count()
            print(f"   - {role.value}: {count}")
        print()
        
        # Верифицированные водители
        verified_drivers = db.query(Driver).filter(Driver.is_verified == True).all()
        print(f"✅ Верифицированных водителей: {len(verified_drivers)}")
        
        verified_without_phone = []
        for driver in verified_drivers:
            user = db.query(User).filter(User.id == driver.user_id).first()
            if user and not user.phone_number:
                verified_without_phone.append((driver, user))
        
        if verified_without_phone:
            print(f"⚠️ ВАЖНО: {len(verified_without_phone)} верифицированных водителей БЕЗ телефона!")
            print("   Это может быть причиной проблемы!")
            for driver, user in verified_without_phone:
                print(f"   - Telegram ID: {user.telegram_id}, Имя: {user.full_name}")
        print()
        
        print("=" * 70)
        print("💡 РЕКОМЕНДАЦИИ:")
        print("=" * 70)
        print()
        
        if users_without_phone:
            print("1. У многих пользователей нет телефона в базе.")
            print("   Это может вызывать проверку на бота при /start")
            print()
        
        if drivers_without_phone:
            print("2. У некоторых водителей нет телефона.")
            print("   Водители должны подтвердить телефон для работы.")
            print()
        
        print("3. Проверьте логи на сервере:")
        print("   ssh на сервер и выполните:")
        print("   journalctl -u taxi-bot -n 100 | grep -i 'start'")
        print()
        
        print("4. Если проблема в том, что Telegram показывает проверку,")
        print("   это может быть антиспам защита Telegram Bot API.")
        print("   В этом случае нужно:")
        print("   - Проверить, не забанен ли бот в Telegram")
        print("   - Обратиться в поддержку Telegram")
        print()
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()







