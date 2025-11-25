"""
Миграция: Добавление полей для районов

Добавляет:
- pickup_district в таблицу orders
- current_district и district_updated_at в таблицу drivers
"""
import sqlite3
from pathlib import Path


def migrate():
    """Применить миграцию"""
    # Путь к базе данных
    db_path = Path(__file__).parent.parent.parent / "taxi_zhukovo.db"
    
    print(f"🔄 Применение миграции к базе данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Добавляем поле pickup_district в orders
        print("📝 Добавление поля pickup_district в таблицу orders...")
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN pickup_district TEXT")
            print("✅ Поле pickup_district добавлено")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️ Поле pickup_district уже существует")
            else:
                raise
        
        # Добавляем поле current_district в drivers
        print("📝 Добавление поля current_district в таблицу drivers...")
        try:
            cursor.execute("ALTER TABLE drivers ADD COLUMN current_district TEXT")
            print("✅ Поле current_district добавлено")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️ Поле current_district уже существует")
            else:
                raise
        
        # Добавляем поле district_updated_at в drivers
        print("📝 Добавление поля district_updated_at в таблицу drivers...")
        try:
            cursor.execute("ALTER TABLE drivers ADD COLUMN district_updated_at TIMESTAMP")
            print("✅ Поле district_updated_at добавлено")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️ Поле district_updated_at уже существует")
            else:
                raise
        
        conn.commit()
        print("✅ Миграция успешно применена!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при применении миграции: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

