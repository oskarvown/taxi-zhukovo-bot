#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Проверка новых водителей в базе данных
"""
from database.db import SessionLocal
from bot.models import User, Driver, UserRole

# Список Telegram ID новых водителей
NEW_DRIVERS = [
    8485379242,  # Айрат Миргалеев
    1314300349,  # Дмитрий Мигунов
    5960184090,  # Евгений Вакуленко
    640476667,   # Артем Гаврилов
]

db = SessionLocal()

try:
    print("=" * 70)
    print("ПРОВЕРКА НОВЫХ ВОДИТЕЛЕЙ В БАЗЕ ДАННЫХ")
    print("=" * 70)
    
    for telegram_id in NEW_DRIVERS:
        print(f"\n🔍 Проверка Telegram ID: {telegram_id}")
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            print(f"  ❌ Пользователь НЕ НАЙДЕН в базе данных!")
            continue
        
        print(f"  ✅ Пользователь найден: {user.full_name}")
        print(f"     ID пользователя: {user.id}")
        print(f"     Роль: {user.role.value}")
        
        if user.role != UserRole.DRIVER:
            print(f"  ⚠️  ПРОБЛЕМА: Роль пользователя = {user.role.value}, должна быть DRIVER!")
        
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        
        if not driver:
            print(f"  ❌ ПРОБЛЕМА: Профиль водителя НЕ НАЙДЕН!")
            continue
        
        print(f"  ✅ Профиль водителя найден:")
        print(f"     ID водителя: {driver.id}")
        print(f"     Автомобиль: {driver.car_model} ({driver.car_number})")
        print(f"     Цвет: {driver.car_color or 'не указан'}")
        print(f"     Верифицирован: {'✅ Да' if driver.is_verified else '❌ Нет'}")
        print(f"     Статус: {driver.status.value}")
        print(f"     Зона: {driver.current_zone.value}")
        
        if not driver.is_verified:
            print(f"  ⚠️  ПРОБЛЕМА: Водитель НЕ верифицирован!")
        
        if user.role != UserRole.DRIVER:
            print(f"  ⚠️  ПРОБЛЕМА: Роль пользователя должна быть DRIVER!")
    
    print("\n" + "=" * 70)
    print("ИТОГИ ПРОВЕРКИ")
    print("=" * 70)
    
    # Проверяем всех водителей в системе
    all_drivers = db.query(Driver).join(User).filter(User.role == UserRole.DRIVER).all()
    print(f"\nВсего водителей в системе: {len(all_drivers)}")
    
    for driver in all_drivers:
        user = driver.user
        print(f"  - {user.full_name} (ID: {user.telegram_id}, верифицирован: {driver.is_verified})")
    
except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

