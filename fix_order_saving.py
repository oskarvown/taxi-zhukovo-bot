#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для исправления проблемы с сохранением заказов
"""
import sys
import os
import sqlite3
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_and_fix_database():
    """Проверка и исправление структуры БД"""
    print("=" * 70)
    print("ПРОВЕРКА И ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ")
    print("=" * 70)
    
    db_path = Path("taxi_zhukovo.db")
    
    if not db_path.exists():
        print(f"\nОШИБКА: База данных не найдена: {db_path}")
        return False
    
    print(f"\nПодключение к базе данных: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Шаг 1: Проверка структуры таблицы orders
        print("\n1. Проверка структуры таблицы orders...")
        cursor.execute("PRAGMA table_info(orders)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        print(f"   Найдено колонок: {len(columns)}")
        for col_name, col_type in columns.items():
            print(f"   - {col_name:25} {col_type}")
        
        # Проверяем необходимые поля
        required_fields = {
            'id': 'INTEGER',
            'customer_id': 'INTEGER',
            'driver_id': 'INTEGER',
            'pickup_address': 'VARCHAR',
            'dropoff_address': 'VARCHAR',
            'status': 'VARCHAR',
            'distance_km': 'FLOAT',
            'price': 'FLOAT',
            'pickup_district': 'VARCHAR',
            'created_at': 'DATETIME',
            'accepted_at': 'DATETIME',
            'completed_at': 'DATETIME'
        }
        
        missing_fields = []
        for field in required_fields:
            if field not in columns:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n   ВНИМАНИЕ: Отсутствуют поля: {', '.join(missing_fields)}")
            
            # Добавляем pickup_district если отсутствует
            if 'pickup_district' in missing_fields:
                print("\n   Добавление поля pickup_district...")
                cursor.execute("ALTER TABLE orders ADD COLUMN pickup_district VARCHAR")
                conn.commit()
                print("   ✓ Поле pickup_district добавлено")
        else:
            print("\n   ✓ Все необходимые поля присутствуют")
        
        # Шаг 2: Проверка структуры таблицы drivers
        print("\n2. Проверка структуры таблицы drivers...")
        cursor.execute("PRAGMA table_info(drivers)")
        driver_columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        print(f"   Найдено колонок: {len(driver_columns)}")
        for col_name, col_type in driver_columns.items():
            print(f"   - {col_name:25} {col_type}")
        
        # Добавляем поля районов если отсутствуют
        if 'current_district' not in driver_columns:
            print("\n   Добавление поля current_district...")
            cursor.execute("ALTER TABLE drivers ADD COLUMN current_district VARCHAR")
            conn.commit()
            print("   ✓ Поле current_district добавлено")
        
        if 'district_updated_at' not in driver_columns:
            print("\n   Добавление поля district_updated_at...")
            cursor.execute("ALTER TABLE drivers ADD COLUMN district_updated_at DATETIME")
            conn.commit()
            print("   ✓ Поле district_updated_at добавлено")
        
        # Шаг 3: Проверка данных в таблице orders
        print("\n3. Проверка данных в таблице orders...")
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        print(f"   Всего заказов в БД: {total_orders}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NOT NULL")
        orders_with_driver = cursor.fetchone()[0]
        print(f"   Заказов с водителем: {orders_with_driver}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NULL")
        orders_without_driver = cursor.fetchone()[0]
        print(f"   Заказов без водителя: {orders_without_driver}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'accepted'")
        accepted_orders = cursor.fetchone()[0]
        print(f"   Заказов в статусе 'accepted': {accepted_orders}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        completed_orders = cursor.fetchone()[0]
        print(f"   Заказов в статусе 'completed': {completed_orders}")
        
        # Шаг 4: Показываем последние заказы
        print("\n4. Последние 5 заказов:")
        cursor.execute("""
            SELECT id, customer_id, driver_id, status, price, 
                   pickup_address, created_at, completed_at
            FROM orders 
            ORDER BY id DESC 
            LIMIT 5
        """)
        orders = cursor.fetchall()
        
        if not orders:
            print("   Заказов не найдено")
        else:
            for order in orders:
                order_id, customer_id, driver_id, status, price, pickup, created, completed = order
                print(f"\n   Заказ #{order_id}:")
                print(f"   - Клиент ID: {customer_id}")
                print(f"   - Водитель ID: {driver_id if driver_id else 'НЕ НАЗНАЧЕН'}")
                print(f"   - Статус: {status}")
                print(f"   - Цена: {price} руб.")
                print(f"   - Откуда: {pickup}")
                print(f"   - Создан: {created}")
                print(f"   - Завершен: {completed if completed else 'не завершен'}")
        
        # Шаг 5: Проверка водителей
        print("\n5. Проверка водителей:")
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        print(f"   Всего водителей: {total_drivers}")
        
        cursor.execute("""
            SELECT d.id, d.user_id, u.full_name, d.car_model, d.car_number, 
                   d.is_online, d.total_rides
            FROM drivers d
            JOIN users u ON d.user_id = u.id
        """)
        drivers = cursor.fetchall()
        
        for driver in drivers:
            driver_id, user_id, name, car_model, car_number, is_online, total_rides = driver
            print(f"\n   Водитель: {name}")
            print(f"   - ID водителя: {driver_id}")
            print(f"   - User ID: {user_id}")
            print(f"   - Авто: {car_model} {car_number}")
            print(f"   - Статус: {'🟢 онлайн' if is_online else '🔴 оффлайн'}")
            print(f"   - Всего поездок: {total_rides}")
            
            # Проверяем заказы этого водителя
            cursor.execute("""
                SELECT COUNT(*) FROM orders WHERE driver_id = ?
            """, (user_id,))
            driver_orders_count = cursor.fetchone()[0]
            print(f"   - Заказов в БД с driver_id={user_id}: {driver_orders_count}")
            
            cursor.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE driver_id = ? AND status = 'completed'
            """, (user_id,))
            driver_completed = cursor.fetchone()[0]
            print(f"   - Завершенных заказов: {driver_completed}")
        
        print("\n" + "=" * 70)
        print("✓ ПРОВЕРКА ЗАВЕРШЕНА")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def test_order_creation_and_acceptance():
    """Тест создания и принятия заказа"""
    print("\n" + "=" * 70)
    print("ТЕСТ СОЗДАНИЯ И ПРИНЯТИЯ ЗАКАЗА")
    print("=" * 70)
    
    try:
        from database.db import SessionLocal
        from bot.models import User, Order, OrderStatus, Driver
        from bot.services import OrderService, UserService
        
        db = SessionLocal()
        
        try:
            # Создаем тестового клиента
            class FakeUser:
                id = 999999999
                first_name = "Test"
                last_name = "Client"
                username = "testclient"
                is_bot = False
            
            fake_user = FakeUser()
            test_client = UserService.get_or_create_user(db, fake_user)
            print(f"\n1. Создан тестовый клиент: {test_client.full_name} (ID: {test_client.id})")
            
            # Получаем реального водителя
            driver_user = db.query(User).join(Driver).first()
            if not driver_user:
                print("\n❌ ОШИБКА: В системе нет водителей!")
                return False
            
            print(f"2. Найден водитель: {driver_user.full_name} (ID: {driver_user.id})")
            
            # Создаем заказ
            order = OrderService.create_order(
                db=db,
                customer=test_client,
                pickup_district="Новое Жуково",
                pickup_address="ул. Ленина, 10",
                pickup_lat=54.7261,
                pickup_lon=55.9478,
                dropoff_address="ул. Советская, 25",
                dropoff_lat=54.7350,
                dropoff_lon=55.9580
            )
            
            print(f"\n3. Создан заказ #{order.id}")
            print(f"   - Статус: {order.status}")
            print(f"   - Клиент ID: {order.customer_id}")
            print(f"   - Водитель ID: {order.driver_id} (должен быть None)")
            print(f"   - Цена: {order.price} руб.")
            
            # Водитель принимает заказ
            OrderService.accept_order(db, order, driver_user)
            print(f"\n4. Водитель принял заказ")
            print(f"   - Статус: {order.status}")
            print(f"   - Водитель ID: {order.driver_id} (должен быть {driver_user.id})")
            
            # Проверяем в БД напрямую
            db.refresh(order)
            print(f"\n5. Проверка после refresh:")
            print(f"   - driver_id в объекте: {order.driver_id}")
            print(f"   - status в объекте: {order.status}")
            
            # Проверяем в БД через SQL
            conn = sqlite3.connect('taxi_zhukovo.db')
            cursor = conn.cursor()
            cursor.execute("SELECT driver_id, status FROM orders WHERE id = ?", (order.id,))
            result = cursor.fetchone()
            conn.close()
            
            print(f"\n6. Проверка через прямой SQL запрос:")
            print(f"   - driver_id в БД: {result[0]}")
            print(f"   - status в БД: {result[1]}")
            
            # Проверяем историю водителя
            history = OrderService.get_driver_history(db, driver_user)
            print(f"\n7. История водителя (завершенные):")
            print(f"   - Найдено: {len(history)} заказов")
            
            # Проверяем активный заказ
            active = OrderService.get_active_order_by_driver(db, driver_user)
            print(f"\n8. Активный заказ водителя:")
            print(f"   - Найден: {'Да' if active else 'Нет'}")
            if active:
                print(f"   - Заказ #{active.id}, статус: {active.status}")
            
            # Удаляем тестовый заказ
            db.delete(order)
            db.commit()
            print(f"\n9. Тестовый заказ удален")
            
            print("\n" + "=" * 70)
            print("✓ ТЕСТ УСПЕШНО ЗАВЕРШЕН")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ОШИБКА В ТЕСТЕ: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"\n❌ ОШИБКА ИМПОРТА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nЗАПУСК ДИАГНОСТИКИ И ИСПРАВЛЕНИЯ\n")
    
    # Шаг 1: Проверка и исправление БД
    if not check_and_fix_database():
        sys.exit(1)
    
    # Шаг 2: Тест создания и принятия заказа
    input("\n\nНажмите Enter для запуска теста создания заказа...")
    if not test_order_creation_and_acceptance():
        sys.exit(1)
    
    print("\n\nВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО! ✓")
    sys.exit(0)

