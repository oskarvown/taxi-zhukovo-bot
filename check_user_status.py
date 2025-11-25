#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Проверка статуса пользователя в БД
"""
from database.db import SessionLocal
from bot.models import User, UserRole, Driver

telegram_id = 6840100810

print("=" * 70)
print("ПРОВЕРКА СТАТУСА ПОЛЬЗОВАТЕЛЯ")
print("=" * 70)
print(f"\nПроверка Telegram ID: {telegram_id}\n")

db = SessionLocal()

try:
    # Ищем пользователя
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        print("❌ Пользователь не найден в базе данных!")
        print("\n💡 Выполните скрипт добавления водителя:")
        print("   python q.py")
    else:
        print(f"✅ Пользователь найден!")
        print(f"\n📋 Информация:")
        print(f"   ID в БД: {user.id}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Имя: {user.full_name}")
        print(f"   Username: @{user.username}" if user.username else "   Username: не указан")
        print(f"   Роль: {user.role.value}")
        
        # Если водитель, показываем дополнительную информацию
        if user.role == UserRole.DRIVER:
            driver = db.query(Driver).filter(Driver.user_id == user.id).first()
            
            if driver:
                print(f"\n🚗 Профиль водителя:")
                print(f"   Автомобиль: {driver.car_model}")
                print(f"   Номер: {driver.car_number}")
                if driver.car_color:
                    print(f"   Цвет: {driver.car_color}")
                print(f"   Телефон: {driver.license_number}")
                print(f"   Рейтинг: {driver.rating:.1f}/5.0")
                print(f"   Поездок: {driver.total_rides}")
                print(f"   Верифицирован: {'✅ Да' if driver.is_verified else '❌ Нет'}")
                print(f"   Онлайн: {'🟢 Да' if driver.is_online else '🔴 Нет'}")
                if driver.current_district:
                    print(f"   Текущий район: {driver.current_district}")
                
                print("\n" + "=" * 70)
                if driver.is_verified:
                    print("✅ ВСЕ НАСТРОЕНО ПРАВИЛЬНО!")
                    print("=" * 70)
                    print("\n📱 Откройте бота в Telegram:")
                    print("   1. Найдите вашего бота")
                    print("   2. Нажмите /start")
                    print("   3. Вы увидите меню водителя:")
                    print("\n   ┌────────────────────────────┐")
                    print("   │ 🟢 Я на линии │ 🔴 Я оффлайн │")
                    print("   ├────────────────────────────┤")
                    print("   │ 📋 Мои заказы │ 📊 Статистика │")
                    print("   └────────────────────────────┘")
                else:
                    print("⚠️ ПРОФИЛЬ НЕ ВЕРИФИЦИРОВАН!")
                    print("=" * 70)
                    print("\n📞 Свяжитесь с администратором для активации")
            else:
                print("\n❌ Профиль водителя не найден!")
                print("\n💡 Выполните скрипт добавления водителя:")
                print("   python q.py")
        else:
            print(f"\n💡 Роль пользователя: {user.role.value}")
            print("   Если нужно сделать водителем, выполните:")
            print("   python q.py")
    
except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n")

