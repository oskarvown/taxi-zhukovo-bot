"""
Миграция: добавление полей для broadcast-режима
Добавляет поля для широковещательных уведомлений и резервации занятых водителей
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from bot.config import settings


def upgrade():
    """Применить миграцию"""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("🔄 Начинаем миграцию: добавление broadcast-полей...")
        
        # Проверяем и добавляем поля в таблицу drivers
        try:
            # Проверяем существование столбца next_finish_zone
            result = conn.execute(text("PRAGMA table_info(drivers);"))
            columns = [row[1] for row in result]
            
            if 'next_finish_zone' not in columns:
                conn.execute(text("ALTER TABLE drivers ADD COLUMN next_finish_zone VARCHAR;"))
                print("✅ Поле next_finish_zone добавлено в drivers")
            else:
                print("ℹ️  Поле next_finish_zone уже существует в drivers")
            
            if 'eta_to_finish' not in columns:
                conn.execute(text("ALTER TABLE drivers ADD COLUMN eta_to_finish INTEGER;"))
                print("✅ Поле eta_to_finish добавлено в drivers")
            else:
                print("ℹ️  Поле eta_to_finish уже существует в drivers")
        except Exception as e:
            print(f"❌ Ошибка при добавлении полей в drivers: {e}")
        
        # Проверяем и добавляем поля в таблицу orders
        try:
            result = conn.execute(text("PRAGMA table_info(orders);"))
            columns = [row[1] for row in result]
            
            if 'is_broadcast' not in columns:
                conn.execute(text("ALTER TABLE orders ADD COLUMN is_broadcast BOOLEAN DEFAULT 0 NOT NULL;"))
                print("✅ Поле is_broadcast добавлено в orders")
            else:
                print("ℹ️  Поле is_broadcast уже существует в orders")
            
            # Создаем индекс (CREATE INDEX IF NOT EXISTS работает в SQLite)
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_orders_is_broadcast 
                ON orders(is_broadcast);
            """))
            print("✅ Индекс idx_orders_is_broadcast создан")
            
            if 'reserved_driver_id' not in columns:
                conn.execute(text("ALTER TABLE orders ADD COLUMN reserved_driver_id INTEGER;"))
                print("✅ Поле reserved_driver_id добавлено в orders")
            else:
                print("ℹ️  Поле reserved_driver_id уже существует в orders")
            
            if 'reserve_expires_at' not in columns:
                conn.execute(text("ALTER TABLE orders ADD COLUMN reserve_expires_at TIMESTAMP;"))
                print("✅ Поле reserve_expires_at добавлено в orders")
            else:
                print("ℹ️  Поле reserve_expires_at уже существует в orders")
        except Exception as e:
            print(f"❌ Ошибка при добавлении полей в orders: {e}")
        
        conn.commit()
        print("✅ Миграция успешно завершена!")


def downgrade():
    """Откатить миграцию"""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("🔄 Откат миграции: удаление broadcast-полей...")
        
        # SQLite не поддерживает DROP COLUMN, поэтому нужно пересоздать таблицы
        print("⚠️  ВНИМАНИЕ: SQLite не поддерживает DROP COLUMN.")
        print("⚠️  Для полного отката нужно пересоздать таблицы или использовать резервную копию БД.")
        print("⚠️  Новые поля останутся в БД, но не будут использоваться приложением.")
        
        # Удаляем только индекс (это работает в SQLite)
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_orders_is_broadcast;"))
            print("✅ Индекс idx_orders_is_broadcast удален")
        except Exception as e:
            print(f"⚠️  Ошибка при удалении индекса: {e}")
        
        conn.commit()
        print("ℹ️  Откат миграции завершен (частично - поля остались в таблицах)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Миграция для broadcast-режима")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Применить или откатить миграцию"
    )
    
    args = parser.parse_args()
    
    if args.action == "upgrade":
        upgrade()
    else:
        downgrade()

