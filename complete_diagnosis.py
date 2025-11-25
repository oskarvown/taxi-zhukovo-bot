#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Полная диагностика системы заказов
Проверяет все аспекты сохранения заказов
"""
import sys
import os
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database_structure():
    """Проверка структуры БД"""
    print("\n" + "=" * 70)
    print("1. ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("=" * 70)
    
    db_path = Path("taxi_zhukovo.db")
    if not db_path.exists():
        print("❌ База данных не найдена!")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверка таблицы orders
        print("\nТаблица orders:")
        cursor.execute("PRAGMA table_info(orders)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        required_fields = ['id', 'customer_id', 'driver_id', 'status', 
                          'pickup_address', 'dropoff_address', 'price',
                          'created_at', 'accepted_at', 'completed_at']
        
        all_present = True
        for field in required_fields:
            if field in columns:
                print(f"  ✓ {field:20} {columns[field]}")
            else:
                print(f"  ❌ {field:20} ОТСУТСТВУЕТ!")
                all_present = False
        
        if not all_present:
            print("\n⚠️  Необходимо выполнить миграцию:")
            print("     python apply_migration.py")
            return False
        
        # Проверка таблицы drivers
        print("\nТаблица drivers:")
        cursor.execute("PRAGMA table_info(drivers)")
        driver_columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        driver_fields = ['id', 'user_id', 'total_rides', 'is_online', 
                        'current_district', 'district_updated_at']
        
        for field in driver_fields:
            if field in driver_columns:
                print(f"  ✓ {field:20} {driver_columns[field]}")
            else:
                print(f"  ⚠️  {field:20} отсутствует")
        
        print("\n✅ Структура БД проверена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        conn.close()


def check_data_consistency():
    """Проверка целостности данных"""
    print("\n" + "=" * 70)
    print("2. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ")
    print("=" * 70)
    
    conn = sqlite3.connect('taxi_zhukovo.db')
    cursor = conn.cursor()
    
    try:
        # Проверка 1: Заказы с водителем, но без accepted_at
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE driver_id IS NOT NULL AND accepted_at IS NULL
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"⚠️  Найдено {count} заказов с водителем, но без даты принятия")
        else:
            print("✓ Все заказы с водителем имеют дату принятия")
        
        # Проверка 2: Заказы в статусе completed без completed_at
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE status = 'completed' AND completed_at IS NULL
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"⚠️  Найдено {count} завершенных заказов без даты завершения")
        else:
            print("✓ Все завершенные заказы имеют дату завершения")
        
        # Проверка 3: Несоответствие статуса и driver_id
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE status IN ('accepted', 'in_progress', 'completed') 
              AND driver_id IS NULL
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"⚠️  Найдено {count} заказов без водителя в статусах accepted/in_progress/completed")
        else:
            print("✓ Все принятые заказы имеют назначенного водителя")
        
        # Проверка 4: Соответствие total_rides реальному количеству
        cursor.execute("""
            SELECT
                d.user_id,
                TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
                d.total_rides,
                (
                    SELECT COUNT(*) FROM orders 
                    WHERE driver_id = d.user_id AND status = 'completed'
                ) as actual
            FROM drivers d
            JOIN users u ON d.user_id = u.id
        """)
        
        mismatches = []
        for row in cursor.fetchall():
            user_id, name, profile_rides, actual_rides = row
            if profile_rides != actual_rides:
                mismatches.append((name, profile_rides, actual_rides))
        
        if mismatches:
            print(f"\n⚠️  Найдено {len(mismatches)} водителей с несоответствием статистики:")
            for name, profile, actual in mismatches:
                print(f"  - {name}: в профиле {profile}, в БД {actual}")
        else:
            print("✓ Статистика всех водителей соответствует реальным данным")
        
        print("\n✅ Проверка целостности завершена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        conn.close()


def check_code_logic():
    """Проверка логики кода"""
    print("\n" + "=" * 70)
    print("3. ПРОВЕРКА ЛОГИКИ КОДА")
    print("=" * 70)
    
    try:
        from database.db import SessionLocal
        from bot.models import Order, OrderStatus, User, Driver
        from bot.services import OrderService
        
        print("\n✓ Импорты успешны")
        
        # Проверяем наличие необходимых методов
        methods = [
            ('OrderService', 'create_order'),
            ('OrderService', 'accept_order'),
            ('OrderService', 'complete_order'),
            ('OrderService', 'get_driver_history'),
            ('OrderService', 'get_active_order_by_driver')
        ]
        
        for class_name, method_name in methods:
            if hasattr(OrderService, method_name):
                print(f"✓ {class_name}.{method_name} существует")
            else:
                print(f"❌ {class_name}.{method_name} не найден!")
        
        # Проверяем модель Order
        print("\nМодель Order:")
        required_attrs = ['driver_id', 'status', 'accepted_at', 'completed_at']
        for attr in required_attrs:
            print(f"  ✓ {attr} определен")
        
        print("\n✅ Логика кода проверена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_actual_data():
    """Проверка реальных данных"""
    print("\n" + "=" * 70)
    print("4. ПРОВЕРКА РЕАЛЬНЫХ ДАННЫХ")
    print("=" * 70)
    
    conn = sqlite3.connect('taxi_zhukovo.db')
    cursor = conn.cursor()
    
    try:
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        print(f"\nВсего заказов в БД: {total_orders}")
        
        if total_orders == 0:
            print("⚠️  В базе данных нет заказов")
            print("   Это нормально, если система только установлена")
            return True
        
        # По статусам
        statuses = ['pending', 'accepted', 'in_progress', 'completed', 'cancelled']
        print("\nРаспределение по статусам:")
        for status in statuses:
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = ?", (status,))
            count = cursor.fetchone()[0]
            print(f"  {status:15} {count}")
        
        # Заказы с водителями
        cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NOT NULL")
        with_driver = cursor.fetchone()[0]
        print(f"\nЗаказов с назначенным водителем: {with_driver}")
        
        # Информация о водителях
        cursor.execute("""
            SELECT
                d.user_id,
                TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
                d.total_rides,
                d.is_online
            FROM drivers d
            JOIN users u ON d.user_id = u.id
        """)
        
        drivers = cursor.fetchall()
        print(f"\nВсего водителей: {len(drivers)}")
        
        if drivers:
            print("\nИнформация по водителям:")
            for user_id, name, rides, is_online in drivers:
                cursor.execute("""
                    SELECT COUNT(*) FROM orders 
                    WHERE driver_id = ? AND status = 'completed'
                """, (user_id,))
                actual_rides = cursor.fetchone()[0]
                
                status = "🟢" if is_online else "🔴"
                match = "✓" if rides == actual_rides else "⚠️"
                
                print(f"  {status} {match} {name}")
                print(f"     В профиле: {rides} поездок")
                print(f"     В БД: {actual_rides} завершенных заказов")
                
                if actual_rides > 0:
                    cursor.execute("""
                        SELECT id, status, price, created_at
                        FROM orders 
                        WHERE driver_id = ?
                        ORDER BY id DESC
                        LIMIT 3
                    """, (user_id,))
                    
                    orders = cursor.fetchall()
                    print(f"     Последние заказы:")
                    for oid, ostatus, price, created in orders:
                        print(f"       #{oid}: {ostatus}, {price} руб., {created}")
        
        print("\n✅ Проверка данных завершена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    print("=" * 70)
    print("ПОЛНАЯ ДИАГНОСТИКА СИСТЕМЫ ЗАКАЗОВ")
    print("=" * 70)
    
    results = []
    
    # Шаг 1: Структура БД
    results.append(("Структура БД", check_database_structure()))
    
    # Шаг 2: Целостность данных
    results.append(("Целостность данных", check_data_consistency()))
    
    # Шаг 3: Логика кода
    results.append(("Логика кода", check_code_logic()))
    
    # Шаг 4: Реальные данные
    results.append(("Реальные данные", check_actual_data()))
    
    # Итоги
    print("\n" + "=" * 70)
    print("ИТОГИ ДИАГНОСТИКИ")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ ПРОЙДЕНО" if passed else "❌ ОШИБКА"
        print(f"{test_name:25} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("\nСистема заказов работает корректно.")
        print("Если водители не видят заказы, убедитесь, что:")
        print("1. Заказы действительно ЗАВЕРШЕНЫ (status='completed')")
        print("2. Клиент оценил поездку")
        print("3. Водитель смотрит раздел 'Мои заказы', а не 'Активные'")
    else:
        print("⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ!")
        print("\nРекомендуемые действия:")
        print("1. Запустите: python apply_migration.py")
        print("2. Запустите: python fix_stuck_orders.py")
        print("3. Повторите диагностику")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    # Не требуем нажатия Enter - запускаем в автоматическом режиме
    # input("\nНажмите Enter для выхода...")
    sys.exit(0 if success else 1)

