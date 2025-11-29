#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления новых водителей на сервере
Использовать на сервере после обновления кода

Запуск:
  cd /opt/taxi-zhukovo
  source venv/bin/activate
  python3 add_drivers_to_server.py
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import SessionLocal
from bot.models import User, UserRole, Driver

# Список новых водителей для добавления
NEW_DRIVERS = [
    {
        "telegram_id": 8485379242,
        "first_name": "Айрат",
        "last_name": "Миргалеев",
        "car_model": "Hyundai Solaris",
        "car_number": "С918УВ102",
        "car_color": "белый",
        "phone": "+79656444644"
    },
    {
        "telegram_id": 1314300349,
        "first_name": "Дмитрий",
        "last_name": "Мигунов",
        "car_model": "Ford Focus",
        "car_number": "Н167УН702",
        "car_color": "черный",
        "phone": "+79876159830"
    },
    {
        "telegram_id": 5960184090,
        "first_name": "Евгений",
        "last_name": "Вакуленко",
        "car_model": "Lada Granta",
        "car_number": "Н259ОР702",
        "car_color": "серебристый",
        "phone": "+79965821515"
    },
    {
        "telegram_id": 640476667,
        "first_name": "Артем",
        "last_name": "Гаврилов",
        "car_model": "Lada Kalina",
        "car_number": "Н698ТУ702",
        "car_color": "Синий",
        "phone": "+79177917067"
    },
]

db = SessionLocal()

try:
    print("=" * 70)
    print("ДОБАВЛЕНИЕ НОВЫХ ВОДИТЕЛЕЙ НА СЕРВЕРЕ")
    print("=" * 70)
    
    for driver_data in NEW_DRIVERS:
        telegram_id = driver_data["telegram_id"]
        print(f"\n🔍 Обработка водителя: {driver_data['first_name']} {driver_data['last_name']} (ID: {telegram_id})")
        
        # Проверяем, существует ли пользователь
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            print(f"  ✓ Пользователь найден: {user.full_name}")
            
            # Проверяем роль
            if user.role != UserRole.DRIVER:
                print(f"  ⚠️  Роль = {user.role.value}, обновляем на DRIVER...")
                user.role = UserRole.DRIVER
                db.commit()
            
            # Проверяем профиль водителя
            driver = db.query(Driver).filter(Driver.user_id == user.id).first()
            
            if driver:
                print(f"  ✓ Профиль водителя уже существует")
                if not driver.is_verified:
                    print(f"  ⚠️  Водитель не верифицирован, верифицируем...")
                    driver.is_verified = True
                    db.commit()
            else:
                print(f"  ⚠️  Профиль водителя не найден, создаем...")
                driver = Driver(
                    user_id=user.id,
                    car_model=driver_data["car_model"],
                    car_number=driver_data["car_number"],
                    car_color=driver_data["car_color"],
                    license_number=driver_data["phone"],
                    is_verified=True
                )
                db.add(driver)
                db.commit()
                print(f"  ✅ Профиль водителя создан!")
        else:
            print(f"  ⚠️  Пользователь не найден, создаем...")
            user = User(
                telegram_id=telegram_id,
                first_name=driver_data["first_name"],
                last_name=driver_data["last_name"],
                username=None,
                role=UserRole.DRIVER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"  ✅ Пользователь создан: {user.full_name}")
            
            # Создаем профиль водителя
            driver = Driver(
                user_id=user.id,
                car_model=driver_data["car_model"],
                car_number=driver_data["car_number"],
                car_color=driver_data["car_color"],
                license_number=driver_data["phone"],
                is_verified=True
            )
            db.add(driver)
            db.commit()
            print(f"  ✅ Профиль водителя создан!")
    
    print("\n" + "=" * 70)
    print("✅ ВСЕ ВОДИТЕЛИ ОБРАБОТАНЫ!")
    print("=" * 70)
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

