#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Проверка БД с записью в файл"""
import sqlite3
import sys
from datetime import datetime

output_file = "DB_CHECK_RESULT.txt"

def write_output(text):
    """Вывод и в консоль, и в файл"""
    print(text)
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(text + '\n')

try:
    # Очищаем файл
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Проверка базы данных - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
    
    write_output("Подключение к базе данных...")
    conn = sqlite3.connect('taxi_zhukovo.db')
    cursor = conn.cursor()
    
    write_output("\n" + "=" * 80)
    write_output("СТРУКТУРА ТАБЛИЦЫ ORDERS")
    write_output("=" * 80)
    cursor.execute("PRAGMA table_info(orders)")
    columns = cursor.fetchall()
    write_output(f"Всего колонок: {len(columns)}\n")
    for col in columns:
        write_output(f"  {col[1]:25} {col[2]}")
    
    # Проверяем наличие driver_id
    has_driver_id = any(col[1] == 'driver_id' for col in columns)
    if has_driver_id:
        write_output("\n✓ Поле driver_id ПРИСУТСТВУЕТ")
    else:
        write_output("\n✗ ОШИБКА: Поле driver_id ОТСУТСТВУЕТ!")
    
    write_output("\n" + "=" * 80)
    write_output("СТАТИСТИКА ЗАКАЗОВ")
    write_output("=" * 80)
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    total = cursor.fetchone()[0]
    write_output(f"Всего заказов: {total}")
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NOT NULL")
    with_driver = cursor.fetchone()[0]
    write_output(f"Заказов с водителем: {with_driver}")
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NULL")
    without_driver = cursor.fetchone()[0]
    write_output(f"Заказов без водителя: {without_driver}")
    
    write_output("\nСтатусы заказов:")
    cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
    status_rows = cursor.fetchall()
    if status_rows:
        for status, count in status_rows:
            write_output(f"  {status:15} {count}")
    else:
        write_output("  ⚠️  Нет заказов для отображения")
    
    write_output("\n" + "=" * 80)
    write_output("ПОСЛЕДНИЕ 10 ЗАКАЗОВ")
    write_output("=" * 80 + "\n")
    
    cursor.execute("""
        SELECT id, customer_id, driver_id, status, price, 
               pickup_address, created_at, accepted_at, completed_at
        FROM orders 
        ORDER BY id DESC 
        LIMIT 10
    """)
    
    orders = cursor.fetchall()
    if not orders:
        write_output("Заказов не найдено")
    else:
        for order in orders:
            oid, cust_id, drv_id, status, price, addr, created, accepted, completed_at = order
            write_output(f"Заказ #{oid}:")
            write_output(f"  Клиент ID: {cust_id}")
            write_output(f"  Водитель ID: {drv_id if drv_id else '⚠️  НЕ НАЗНАЧЕН'}")
            write_output(f"  Статус: {status}")
            write_output(f"  Цена: {price} руб.")
            write_output(f"  Откуда: {addr}")
            write_output(f"  Создан: {created}")
            write_output(f"  Принят: {accepted if accepted else 'не принят'}")
            write_output(f"  Завершен: {completed_at if completed_at else 'не завершен'}")
            write_output("")
    
    write_output("=" * 80)
    write_output("ВОДИТЕЛИ И ИХ ЗАКАЗЫ")
    write_output("=" * 80 + "\n")
    
    cursor.execute("""
        SELECT
            d.id,
            d.user_id,
            TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
            u.telegram_id,
            d.car_model,
            d.car_number,
            d.status,
            d.current_zone,
            d.online_since,
            d.total_rides
        FROM drivers d
        JOIN users u ON d.user_id = u.id
    """)
    
    drivers = cursor.fetchall()
    if not drivers:
        write_output("Водителей не найдено")
    else:
        for driver in drivers:
            (
                drv_id,
                user_id,
                name,
                tg_id,
                car_model,
                car_number,
                driver_status,
                current_zone,
                online_since,
                total_rides,
            ) = driver
            write_output(f"Водитель: {name}")
            write_output(f"  ID водителя: {drv_id}")
            write_output(f"  User ID: {user_id}")
            write_output(f"  Telegram ID: {tg_id}")
            write_output(f"  Автомобиль: {car_model} {car_number}")
            zone_text = current_zone if current_zone else 'NONE'
            write_output(f"  Статус: {driver_status or 'unknown'} (зона: {zone_text})")
            if online_since:
                write_output(f"  На линии с: {online_since}")
            write_output(f"  Поездок в профиле: {total_rides}")
            
            # Проверяем заказы этого водителя
            cursor.execute("""
                SELECT COUNT(*) FROM orders WHERE driver_id = ?
            """, (user_id,))
            driver_orders = cursor.fetchone()[0]
            write_output(f"  ⚠️  Всего заказов в БД (driver_id={user_id}): {driver_orders}")
            
            cursor.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE driver_id = ? AND status = 'accepted'
            """, (user_id,))
            driver_accepted = cursor.fetchone()[0]
            write_output(f"  Принятых заказов: {driver_accepted}")
            
            cursor.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE driver_id = ? AND status = 'completed'
            """, (user_id,))
            driver_completed = cursor.fetchone()[0]
            write_output(f"  Завершенных заказов: {driver_completed}")
            
            # Показываем последние заказы водителя
            cursor.execute("""
                SELECT id, status, price, created_at, completed_at
                FROM orders 
                WHERE driver_id = ?
                ORDER BY id DESC
                LIMIT 3
            """, (user_id,))
            
            driver_order_list = cursor.fetchall()
            if driver_order_list:
                write_output(f"  Последние заказы:")
                for dorder in driver_order_list:
                    doid, dstatus, dprice, dcreated, dcompleted = dorder
                    write_output(f"    - Заказ #{doid}: {dstatus}, {dprice} руб., {dcreated}")
            else:
                write_output(f"  ⚠️  У этого водителя НЕТ заказов в БД!")
            
            write_output("")
    
    conn.close()
    
    write_output("=" * 80)
    write_output("✓ ПРОВЕРКА ЗАВЕРШЕНА")
    write_output("=" * 80)
    
    print(f"\n\nРезультаты сохранены в файл: {output_file}")
    print("Вы можете открыть его для просмотра детальной информации.")
    
except Exception as e:
    write_output(f"\n✗ ОШИБКА: {e}")
    import traceback
    error_text = traceback.format_exc()
    write_output(error_text)
    sys.exit(1)

