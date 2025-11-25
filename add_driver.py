#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для добавления водителя
"""
import sys
from database.db import SessionLocal
from bot.models import User, UserRole, Driver

def add_driver():
    """Добавить водителя в систему"""
    
    print("=" * 70)
    print("ДОБАВЛЕНИЕ ВОДИТЕЛЯ В СИСТЕМУ")
    print("=" * 70)
    
    # Запрашиваем данные
    print("\n📝 Введите данные водителя:\n")
    
    telegram_id = input("Telegram ID (числовой ID пользователя): ").strip()
    if not telegram_id.isdigit():
        print("❌ Ошибка: Telegram ID должен быть числом")
        return False
    
    telegram_id = int(telegram_id)
    
    first_name = input("Имя: ").strip()
    if not first_name:
        print("❌ Ошибка: Имя обязательно")
        return False
    
    last_name = input("Фамилия: ").strip()
    username = input("Username (без @, можно пропустить): ").strip() or None
    
    print("\n🚗 Данные автомобиля:\n")
    car_model = input("Модель автомобиля (например: Toyota Camry): ").strip()
    if not car_model:
        print("❌ Ошибка: Модель автомобиля обязательна")
        return False
    
    car_number = input("Номер автомобиля (например: А123БВ): ").strip()
    if not car_number:
        print("❌ Ошибка: Номер автомобиля обязателен")
        return False
    
    car_color = input("Цвет автомобиля (можно пропустить): ").strip() or None
    
    license_number = input("Номер водительского удостоверения: ").strip()
    if not license_number:
        print("❌ Ошибка: Номер ВУ обязателен")
        return False
    
    # Подтверждение
    print("\n" + "=" * 70)
    print("ПРОВЕРЬТЕ ДАННЫЕ:")
    print("=" * 70)
    print(f"Telegram ID: {telegram_id}")
    print(f"Имя: {first_name} {last_name}")
    if username:
        print(f"Username: @{username}")
    print(f"Автомобиль: {car_model} ({car_number})")
    if car_color:
        print(f"Цвет: {car_color}")
    print(f"Водительское удостоверение: {license_number}")
    print("=" * 70)
    
    confirm = input("\nВсе верно? (да/нет): ").strip().lower()
    if confirm not in ['да', 'yes', 'y', 'д']:
        print("❌ Отменено")
        return False
    
    # Добавляем в БД
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
                
                update = input("Обновить данные? (да/нет): ").strip().lower()
                if update in ['да', 'yes', 'y', 'д']:
                    existing_driver.car_model = car_model
                    existing_driver.car_number = car_number
                    existing_driver.car_color = car_color
                    existing_driver.license_number = license_number
                    existing_driver.is_verified = True
                    db.commit()
                    print("✅ Данные водителя обновлены!")
                    return True
                else:
                    print("❌ Отменено")
                    return False
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
        
        # Обновляем роль на водителя
        user.role = UserRole.DRIVER
        
        # Создаем профиль водителя
        driver = Driver(
            user_id=user.id,
            car_model=car_model,
            car_number=car_number,
            car_color=car_color,
            license_number=license_number,
            is_verified=True  # Сразу верифицируем
        )
        
        db.add(driver)
        db.commit()
        db.refresh(driver)
        
        print("\n" + "=" * 70)
        print("✅ ВОДИТЕЛЬ УСПЕШНО ДОБАВЛЕН!")
        print("=" * 70)
        print(f"\n👤 {user.full_name}")
        print(f"🚗 {driver.car_model} ({driver.car_number})")
        print(f"⭐ Рейтинг: {driver.rating}")
        print(f"✅ Верифицирован: Да")
        print(f"\n📱 Водитель может войти в бота через Telegram ID: {telegram_id}")
        print("\n💡 ИНСТРУКЦИЯ ДЛЯ ВОДИТЕЛЯ:")
        print("   1. Откройте бота в Telegram")
        print("   2. Нажмите /start")
        print("   3. Вы увидите меню водителя с кнопками:")
        print("      - 🟢 Я на линии (выйти онлайн)")
        print("      - 🔴 Я оффлайн (выйти оффлайн)")
        print("      - 📋 Мои заказы")
        print("      - 📊 Статистика")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🚖 СИСТЕМА ДОБАВЛЕНИЯ ВОДИТЕЛЕЙ\n")
    print("💡 Для добавления водителя вам понадобится его Telegram ID")
    print("   Чтобы узнать Telegram ID, попросите пользователя:")
    print("   1. Написать боту @userinfobot")
    print("   2. Скопировать число из строки 'Id: XXXXXXX'\n")
    
    input("Нажмите Enter для продолжения...")
    
    success = add_driver()
    
    if success:
        print("\n" + "=" * 70)
        print("Теперь водитель может пользоваться ботом!")
        print("=" * 70)
    
    input("\nНажмите Enter для выхода...")
    sys.exit(0 if success else 1)

