"""
Миграция: Добавление полей для этапов поездки и рейтингов
"""
import sqlite3
import os
from pathlib import Path

def run_migration():
    """Выполнить миграцию"""
    import sys
    import io
    # Устанавливаем UTF-8 для вывода
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # Путь к БД
    db_path = Path(__file__).parent.parent.parent / "taxi_zhukovo.db"
    
    if not db_path.exists():
        print(f"База данных не найдена: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("Начало миграции: добавление полей для этапов поездки...")
        
        # Проверяем существующие колонки в orders
        cursor.execute("PRAGMA table_info(orders)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Добавляем новые поля в orders
        new_columns_orders = [
            ("arrived_at", "DATETIME NULL"),
            ("finished_at", "DATETIME NULL"),
            ("rating_comment", "TEXT NULL"),
        ]
        
        for col_name, col_type in new_columns_orders:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
                    print(f"  + Добавлена колонка orders.{col_name}")
                except sqlite3.OperationalError as e:
                    print(f"  ! Ошибка добавления orders.{col_name}: {e}")
            else:
                print(f"  i Колонка orders.{col_name} уже существует")
        
        # Проверяем существующие колонки в drivers
        cursor.execute("PRAGMA table_info(drivers)")
        existing_columns_drivers = [row[1] for row in cursor.fetchall()]
        
        # Добавляем новые поля в drivers
        new_columns_drivers = [
            ("rating_avg", "REAL DEFAULT 5.0"),
            ("rating_count", "INTEGER DEFAULT 0"),
        ]
        
        for col_name, col_type in new_columns_drivers:
            if col_name not in existing_columns_drivers:
                try:
                    cursor.execute(f"ALTER TABLE drivers ADD COLUMN {col_name} {col_type}")
                    print(f"  + Добавлена колонка drivers.{col_name}")
                except sqlite3.OperationalError as e:
                    print(f"  ! Ошибка добавления drivers.{col_name}: {e}")
            else:
                print(f"  i Колонка drivers.{col_name} уже существует")
        
        # Обновляем rating_avg из rating для существующих водителей
        cursor.execute("""
            UPDATE drivers 
            SET rating_avg = rating 
            WHERE rating_avg IS NULL OR rating_avg = 0
        """)
        
        # Подсчитываем rating_count для существующих водителей
        cursor.execute("""
            UPDATE drivers 
            SET rating_count = (
                SELECT COUNT(*) 
                FROM orders 
                WHERE orders.driver_id = drivers.user_id 
                AND orders.rating IS NOT NULL
            )
        """)
        
        conn.commit()
        print("Миграция успешно завершена!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()

