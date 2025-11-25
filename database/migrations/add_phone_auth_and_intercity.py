
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Миграция v1.1: телефонная аутентификация, санкции и межгород
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text  # pylint: disable=wrong-import-position
from database.db import SessionLocal, engine  # pylint: disable=wrong-import-position


def migrate():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("МИГРАЦИЯ v1.1 — телефонная аутентификация и межгород")
        print("=" * 70)

        with engine.begin() as connection:
            print("\n1. Поля users...")
            user_alters = [
                "ALTER TABLE users ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT 0",
                "ALTER TABLE users ADD COLUMN warning_count INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE users ADD COLUMN last_warning_at TIMESTAMP NULL",
            ]
            for ddl in user_alters:
                try:
                    connection.execute(text(ddl))
                    print(f"  ✓ {ddl}")
                except Exception as exc:
                    if "duplicate column name" in str(exc).lower():
                        print("  ⚠ Поле уже существует, пропускаем")
                    else:
                        raise

            index_statements = [
                "CREATE INDEX IF NOT EXISTS ix_users_is_banned ON users(is_banned)",
                "CREATE INDEX IF NOT EXISTS ix_users_warning_count ON users(warning_count)",
                "CREATE INDEX IF NOT EXISTS ix_users_last_warning_at ON users(last_warning_at)",
            ]
            for ddl in index_statements:
                connection.execute(text(ddl))
                print(f"  ✓ {ddl}")

            print("\n2. Поля orders...")
            order_alters = [
                "ALTER TABLE orders ADD COLUMN tariff TEXT NOT NULL DEFAULT 'fixed'",
                "ALTER TABLE orders ADD COLUMN is_intercity BOOLEAN NOT NULL DEFAULT 0",
                "ALTER TABLE orders ADD COLUMN from_zone TEXT NULL",
                "ALTER TABLE orders ADD COLUMN to_text TEXT NULL",
                "ALTER TABLE orders ADD COLUMN selected_driver_id INTEGER NULL",
            ]
            for ddl in order_alters:
                try:
                    connection.execute(text(ddl))
                    print(f"  ✓ {ddl}")
                except Exception as exc:
                    if "duplicate column name" in str(exc).lower():
                        print("  ⚠ Поле уже существует, пропускаем")
                    else:
                        raise

            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_orders_is_intercity ON orders(is_intercity);
                    """
                )
            )
            print("  ✓ Создан индекс ix_orders_is_intercity")

            print("\n3. Приведение существующих данных...")
            connection.execute(text("UPDATE orders SET tariff = 'fixed' WHERE tariff IS NULL"))
            connection.execute(
                text("UPDATE orders SET is_intercity = 0 WHERE is_intercity IS NULL")
            )

        db.commit()
        print("\n✅ Миграция завершена успешно")
        return True
    except Exception as exc:  # pylint: disable=broad-except
        db.rollback()
        print(f"\n❌ Ошибка миграции: {exc}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    input("Нажмите Enter для запуска миграции...")
    success = migrate()
    input("\nНажмите Enter для выхода...")
    sys.exit(0 if success else 1)

