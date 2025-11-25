#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматическое добавление водителя
"""
from database.db import SessionLocal
from bot.models import User, UserRole, Driver

# Данные водителя
telegram_id = 6840100810
first_name = "Аскар"
last_name = "Курбангулов"
username = None  # будет взято из профиля, если есть
car_model = "Toyota Camry"
car_number = "А123БВ"
car_color = None
license_number = "+79852869872"  # Используем номер телефона как идентификатор

print("=" * 70)
print("ДОБАВЛЕНИЕ ВОДИТЕЛЯ В СИСТЕМУ")
print("=" * 70)
print(f"\nДанные водителя:")
print(f"  Telegram ID: {telegram_id}")
print(f"  Имя: {first_name} {last_name}")
print(f"  Автомобиль: {car_model} ({car_number})")
print(f"  Контакт: {license_number}")
print("=" * 70)

db = SessionLocal()

try:
    # Проверяем, существует ли пользователь
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if user:
        print(f"\n✓ Пользователь найден: {user.full_name}")
        
        # Проверяем, не является ли он уже водителем
        existing_driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if existing_driver:
            print("⚠️ Этот пользователь уже зарегистрирован как водитель!")
            print("Обновляем данные...")
            
            existing_driver.car_model = car_model
            existing_driver.car_number = car_number
            existing_driver.car_color = car_color
            existing_driver.license_number = license_number
            existing_driver.is_verified = True
            db.commit()
            print("✅ Данные водителя обновлены!")
        else:
            # Создаем профиль водителя
            user.role = UserRole.DRIVER
            
            driver = Driver(
                user_id=user.id,
                car_model=car_model,
                car_number=car_number,
                car_color=car_color,
                license_number=license_number,
                is_verified=True
            )
            
            db.add(driver)
            db.commit()
            db.refresh(driver)
            
            print("✅ Профиль водителя создан!")
    else:
        # Создаем нового пользователя
        print(f"\n✓ Создаем нового пользователя...")
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            role=UserRole.DRIVER
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ Пользователь создан: {user.full_name}")
        
        # Создаем профиль водителя
        driver = Driver(
            user_id=user.id,
            car_model=car_model,
            car_number=car_number,
            car_color=car_color,
            license_number=license_number,
            is_verified=True
        )
        
        db.add(driver)
        db.commit()
        db.refresh(driver)
        
        print("✅ Профиль водителя создан!")
    
    print("\n" + "=" * 70)
    print("✅ ВОДИТЕЛЬ УСПЕШНО ДОБАВЛЕН!")
    print("=" * 70)
    
    # Получаем обновленные данные
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    driver = db.query(Driver).filter(Driver.user_id == user.id).first()
    
    print(f"\n👤 {user.full_name}")
    print(f"🚗 {driver.car_model} ({driver.car_number})")
    print(f"⭐ Рейтинг: {driver.rating}")
    print(f"✅ Верифицирован: Да")
    print(f"📱 Telegram ID: {telegram_id}")
    
    print("\n💡 ИНСТРУКЦИЯ ДЛЯ ВОДИТЕЛЯ:")
    print("   1. Откройте бота в Telegram")
    print("   2. Нажмите /start")
    print("   3. Вы увидите меню водителя:")
    print("      ┌────────────────────────────┐")
    print("      │ 🟢 Я на линии │ 🔴 Я оффлайн │")
    print("      ├────────────────────────────┤")
    print("      │ 📋 Мои заказы │ 📊 Статистика │")
    print("      └────────────────────────────┘")
    print("\n   4. Нажмите '🟢 Я на линии'")
    print("   5. Выберите район (например, 'Новое Жуково')")
    print("   6. Готово! Ожидайте заказы 🚖")
    
    print("\n" + "=" * 70)
    print("Теперь водитель может пользоваться ботом!")
    print("=" * 70)
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

