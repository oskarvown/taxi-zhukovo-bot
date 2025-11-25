#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Диагностика и тестирование создания заказов
"""
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 70)
    print("ДИАГНОСТИКА СИСТЕМЫ ЗАКАЗОВ")
    print("=" * 70)
    
    # Шаг 1: Проверка импортов
    print("\n1. Проверка импортов...")
    try:
        from database.db import SessionLocal, Base, engine
        print("   OK database.db")
    except Exception as e:
        print(f"   ERROR database.db: {e}")
        return False
    
    try:
        from bot.models import User, Order, OrderStatus, Driver
        print("   OK bot.models")
    except Exception as e:
        print(f"   ERROR bot.models: {e}")
        return False
    
    try:
        from bot.services import OrderService, UserService
        print("   OK bot.services")
    except Exception as e:
        print(f"   ERROR bot.services: {e}")
        return False
    
    # Шаг 2: Проверка БД
    print("\n2. Проверка базы данных...")
    try:
        import sqlite3
        conn = sqlite3.connect('taxi_zhukovo.db')
        cursor = conn.cursor()
        
        # Проверяем таблицу orders
        cursor.execute("PRAGMA table_info(orders)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        required_columns = ['id', 'customer_id', 'pickup_address', 'dropoff_address', 
                          'status', 'distance_km', 'price', 'pickup_district']
        
        missing = [col for col in required_columns if col not in columns]
        
        if missing:
            print(f"   WARNING: Missing columns: {missing}")
            
            # Добавляем pickup_district если отсутствует
            if 'pickup_district' in missing:
                print("   FIXING: Adding pickup_district...")
                cursor.execute("ALTER TABLE orders ADD COLUMN pickup_district TEXT")
                conn.commit()
                print("   OK: pickup_district added")
        else:
            print("   OK: All required columns exist")
        
        conn.close()
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Шаг 3: Тестирование создания заказа
    print("\n3. Тестирование создания заказа...")
    
    db = SessionLocal()
    
    try:
        # Создаем или получаем тестового пользователя
        class FakeTgUser:
            id = 111111111
            first_name = "Test"
            last_name = "User"  
            username = "testuser"
            is_bot = False
        
        fake_user = FakeTgUser()
        test_user = UserService.get_or_create_user(db, fake_user)
        print(f"   OK: Test user created: {test_user.full_name}")
        
        # Создаем заказ
        order = OrderService.create_order(
            db=db,
            customer=test_user,
            pickup_district="Новое Жуково",
            pickup_address="ул. Ленина, 10",
            pickup_lat=54.7261,
            pickup_lon=55.9478,
            dropoff_address="ул. Советская, 25",
            dropoff_lat=54.7350,
            dropoff_lon=55.9580,
            price=150.0,  # Добавлена фиксированная цена
            dropoff_zone="По Жуково"
        )
        
        print(f"   OK: Order created #{order.id}")
        print(f"      Status: {order.status}")
        print(f"      District: {order.pickup_district}")
        print(f"      Price: {order.price} rub")
        
        # Проверяем display_info
        print(f"\n   Display info:")
        for line in order.display_info.split('\n'):
            print(f"      {line}")
        
        # Удаляем тестовый заказ
        db.delete(order)
        db.commit()
        print(f"\n   OK: Test order deleted")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
    
    print("\n" + "=" * 70)
    print("SUCCESS: All checks passed!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

