#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Применение миграции для добавления полей районов
"""
import sqlite3
from pathlib import Path

db_path = Path("taxi_zhukovo.db")

if not db_path.exists():
    print(f"ОШИБКА: База данных не найдена: {db_path}")
    exit(1)

print(f"Подключение к базе данных: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Добавляем pickup_district в orders
    print("\nДобавление поля pickup_district в таблицу orders...")
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN pickup_district TEXT")
        conn.commit()
        print("SUCCESS: Поле pickup_district добавлено")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("INFO: Поле pickup_district уже существует")
        else:
            raise
    
    # Добавляем current_district в drivers
    print("\nДобавление поля current_district в таблицу drivers...")
    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN current_district TEXT")
        conn.commit()
        print("SUCCESS: Поле current_district добавлено")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("INFO: Поле current_district уже существует")
        else:
            raise
    
    # Добавляем district_updated_at в drivers
    print("\nДобавление поля district_updated_at в таблицу drivers...")
    try:
        cursor.execute("ALTER TABLE drivers ADD COLUMN district_updated_at TIMESTAMP")
        conn.commit()
        print("SUCCESS: Поле district_updated_at добавлено")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("INFO: Поле district_updated_at уже существует")
        else:
            raise
    
    print("\nМиграция успешно применена!")
    
    # Проверяем структуру таблицы orders
    print("\n" + "="*60)
    print("Структура таблицы orders:")
    cursor.execute("PRAGMA table_info(orders)")
    for col in cursor.fetchall():
        print(f"  {col[1]:25} {col[2]}")
    
    print("\n" + "="*60)
    print("Структура таблицы drivers:")
    cursor.execute("PRAGMA table_info(drivers)")
    for col in cursor.fetchall():
        print(f"  {col[1]:25} {col[2]}")
    
except Exception as e:
    conn.rollback()
    print(f"\nОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()

