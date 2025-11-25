"""
Миграция: добавление полей статистики для водителей
- completed_trips_count: счётчик завершённых поездок
- rating_avg: средний рейтинг водителя
- rating_count: количество оценок

+ Индекс для быстрой выборки истории заказов водителя
"""
import sqlite3
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from bot.config import settings

def check_column_exists(cursor, table: str, column: str) -> bool:
    """Проверить существование колонки в таблице"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def check_index_exists(cursor, index_name: str) -> bool:
    """Проверить существование индекса"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None

def run_migration():
    """Запуск миграции"""
    # Получаем путь к БД из настроек
    db_path = settings.database_url.replace("sqlite:///", "").replace("./", "")
    
    print(f"🔧 Подключение к БД: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # === 1. Добавление полей статистики в drivers ===
        print("\n📊 Добавление полей статистики в таблицу drivers...")
        
        # completed_trips_count
        if not check_column_exists(cursor, "drivers", "completed_trips_count"):
            print("  ➕ Добавление completed_trips_count (INT DEFAULT 0)")
            cursor.execute("""
                ALTER TABLE drivers 
                ADD COLUMN completed_trips_count INTEGER DEFAULT 0
            """)
            print("  ✅ completed_trips_count добавлен")
        else:
            print("  ⏭️  completed_trips_count уже существует")
        
        # rating_avg
        if not check_column_exists(cursor, "drivers", "rating_avg"):
            print("  ➕ Добавление rating_avg (REAL DEFAULT 0.0)")
            cursor.execute("""
                ALTER TABLE drivers 
                ADD COLUMN rating_avg REAL DEFAULT 0.0
            """)
            print("  ✅ rating_avg добавлен")
        else:
            print("  ⏭️  rating_avg уже существует")
        
        # rating_count
        if not check_column_exists(cursor, "drivers", "rating_count"):
            print("  ➕ Добавление rating_count (INT DEFAULT 0)")
            cursor.execute("""
                ALTER TABLE drivers 
                ADD COLUMN rating_count INTEGER DEFAULT 0
            """)
            print("  ✅ rating_count добавлен")
        else:
            print("  ⏭️  rating_count уже существует")
        
        # === 2. Создание индекса для истории заказов ===
        print("\n🔍 Создание индекса для быстрой выборки истории заказов...")
        
        index_name = "idx_orders_driver_finished"
        if not check_index_exists(cursor, index_name):
            print(f"  ➕ Создание индекса {index_name}")
            cursor.execute("""
                CREATE INDEX idx_orders_driver_finished 
                ON orders(assigned_driver_id, finished_at DESC)
            """)
            print(f"  ✅ Индекс {index_name} создан")
        else:
            print(f"  ⏭️  Индекс {index_name} уже существует")
        
        # === 3. Инициализация значений для существующих водителей ===
        print("\n🔄 Инициализация статистики для существующих водителей...")
        
        # Получаем всех водителей
        cursor.execute("SELECT id FROM drivers")
        drivers = cursor.fetchall()
        
        if drivers:
            print(f"  📋 Найдено водителей: {len(drivers)}")
            
            for (driver_id,) in drivers:
                # Считаем завершённые поездки
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM orders 
                    WHERE assigned_driver_id = ? AND status = 'finished'
                """, (driver_id,))
                completed_count = cursor.fetchone()[0]
                
                # Считаем средний рейтинг и количество оценок
                cursor.execute("""
                    SELECT AVG(rating), COUNT(*) 
                    FROM orders 
                    WHERE assigned_driver_id = ? AND rating IS NOT NULL
                """, (driver_id,))
                result = cursor.fetchone()
                avg_rating = result[0] if result[0] is not None else 0.0
                rating_count = result[1]
                
                # Обновляем водителя
                cursor.execute("""
                    UPDATE drivers 
                    SET completed_trips_count = ?,
                        rating_avg = ?,
                        rating_count = ?
                    WHERE id = ?
                """, (completed_count, avg_rating, rating_count, driver_id))
                
                print(f"  ✅ Водитель ID {driver_id}: поездок={completed_count}, рейтинг={avg_rating:.2f} ({rating_count} оценок)")
        else:
            print("  ⏭️  Водителей в БД не найдено")
        
        # Коммит изменений
        conn.commit()
        print("\n✅ Миграция успешно завершена!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка при выполнении миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Устанавливаем UTF-8 для вывода в консоль Windows
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("=" * 60)
    print("🚀 Миграция: Добавление статистики водителей")
    print("=" * 60)
    run_migration()
    print("=" * 60)

