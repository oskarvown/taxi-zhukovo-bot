
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Исправление 'зависших' заказов
Находит заказы, которые приняты водителями, но не завершены
"""
import sqlite3
import sys
from datetime import datetime

def main():
    print("=" * 70)
    print("ИСПРАВЛЕНИЕ 'ЗАВИСШИХ' ЗАКАЗОВ")
    print("=" * 70)
    
    try:
        conn = sqlite3.connect('taxi_zhukovo.db')
        cursor = conn.cursor()
        
        # Проверяем заказы в разных статусах
        print("\n1. Статистика заказов:")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        print(f"   Ожидают водителя (pending): {pending_count}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'accepted'")
        accepted_count = cursor.fetchone()[0]
        print(f"   Приняты водителем (accepted): {accepted_count}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'in_progress'")
        in_progress_count = cursor.fetchone()[0]
        print(f"   В процессе (in_progress): {in_progress_count}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        completed_count = cursor.fetchone()[0]
        print(f"   Завершены (completed): {completed_count}")
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'cancelled'")
        cancelled_count = cursor.fetchone()[0]
        print(f"   Отменены (cancelled): {cancelled_count}")
        
        # Находим "зависшие" заказы
        print("\n2. Поиск 'зависших' заказов...")
        
        cursor.execute("""
            SELECT id, customer_id, driver_id, status, created_at, accepted_at
            FROM orders 
            WHERE status IN ('accepted', 'in_progress') 
              AND driver_id IS NOT NULL
            ORDER BY id DESC
        """)
        
        stuck_orders = cursor.fetchall()
        
        if not stuck_orders:
            print("   ✓ 'Зависших' заказов не найдено!")
        else:
            print(f"   ⚠️  Найдено 'зависших' заказов: {len(stuck_orders)}")
            print("\n3. Детали 'зависших' заказов:")
            
            for order in stuck_orders:
                order_id, customer_id, driver_id, status, created_at, accepted_at = order
                
                # Получаем информацию о водителе
                cursor.execute("""
                    SELECT
                        TRIM(
                            COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')
                        ) AS full_name,
                        u.telegram_id
                    FROM users u
                    WHERE u.id = ?
                """, (driver_id,))
                driver_info = cursor.fetchone()
                driver_name = driver_info[0] if driver_info else "Неизвестен"
                
                # Получаем информацию о клиенте
                cursor.execute("""
                    SELECT TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name
                    FROM users u
                    WHERE u.id = ?
                """, (customer_id,))
                customer_info = cursor.fetchone()
                customer_name = customer_info[0] if customer_info else "Неизвестен"
                
                print(f"\n   Заказ #{order_id}:")
                print(f"   - Статус: {status}")
                print(f"   - Клиент: {customer_name} (ID: {customer_id})")
                print(f"   - Водитель: {driver_name} (ID: {driver_id})")
                print(f"   - Создан: {created_at}")
                print(f"   - Принят: {accepted_at}")
            
            # Спрашиваем, нужно ли исправить
            print("\n4. Исправление 'зависших' заказов...")
            print("\n   ⚠️  ВНИМАНИЕ: Эти заказы будут помечены как завершенные!")
            print("   Это позволит им появиться в истории водителей.")
            
            response = input("\n   Завершить эти заказы? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y', 'да', 'д']:
                for order in stuck_orders:
                    order_id = order[0]
                    cursor.execute("""
                        UPDATE orders 
                        SET status = 'completed',
                            completed_at = COALESCE(completed_at, datetime('now')),
                            started_at = COALESCE(started_at, accepted_at, datetime('now'))
                        WHERE id = ?
                    """, (order_id,))
                
                conn.commit()
                print(f"\n   ✅ Завершено заказов: {len(stuck_orders)}")
                
                # Обновляем статистику водителей
                print("\n5. Обновление статистики водителей...")
                
                # Группируем по водителям
                driver_ids = set(order[2] for order in stuck_orders)
                
                for driver_id in driver_ids:
                    # Подсчитываем завершенные заказы
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM orders 
                        WHERE driver_id = ? AND status = 'completed'
                    """, (driver_id,))
                    completed_rides = cursor.fetchone()[0]
                    
                    # Обновляем профиль водителя
                    cursor.execute("""
                        UPDATE drivers
                        SET total_rides = ?
                        WHERE user_id = ?
                    """, (completed_rides, driver_id))
                    
                    cursor.execute("""
                        SELECT TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name
                        FROM users u
                        WHERE u.id = ?
                    """, (driver_id,))
                    driver_name = cursor.fetchone()[0]
                    
                    print(f"   ✓ {driver_name}: обновлено на {completed_rides} поездок")
                
                conn.commit()
                print("\n   ✅ Статистика водителей обновлена!")
            else:
                print("\n   ⚠️  Исправление отменено пользователем")
        
        # Итоговая статистика
        print("\n" + "=" * 70)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 70)
        
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        final_completed = cursor.fetchone()[0]
        print(f"Завершенных заказов: {final_completed}")
        
        cursor.execute("""
            SELECT
                d.user_id,
                TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
                d.total_rides,
                (
                    SELECT COUNT(*) FROM orders
                    WHERE driver_id = d.user_id AND status = 'completed'
                ) as actual_rides
            FROM drivers d
            JOIN users u ON d.user_id = u.id
        """)
        
        print("\nВодители:")
        for driver in cursor.fetchall():
            user_id, name, profile_rides, actual_rides = driver
            match = "✓" if profile_rides == actual_rides else "⚠️"
            print(f"  {match} {name}: профиль={profile_rides}, БД={actual_rides}")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✓ ПРОВЕРКА ЗАВЕРШЕНА")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    input("\nНажмите Enter для выхода...")
    sys.exit(0 if success else 1)

