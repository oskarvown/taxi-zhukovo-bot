#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Миграция для добавления системы очередей
Добавляет новые поля для Driver и Order
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from database.db import SessionLocal, engine


def migrate():
    """Применить миграцию"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("МИГРАЦИЯ: Добавление системы очередей")
        print("=" * 70)
        
        # 1. Добавляем новые поля в таблицу drivers
        print("\n1. Добавление полей в таблицу drivers...")
        
        migrations = [
            # Новые поля для системы очередей
            "ALTER TABLE drivers ADD COLUMN status TEXT DEFAULT 'offline' NOT NULL",
            "ALTER TABLE drivers ADD COLUMN current_zone TEXT DEFAULT 'NONE' NOT NULL",
            "ALTER TABLE drivers ADD COLUMN online_since TIMESTAMP NULL",
            "ALTER TABLE drivers ADD COLUMN pending_order_id INTEGER NULL",
            "ALTER TABLE drivers ADD COLUMN pending_until TIMESTAMP NULL",
        ]
        
        for migration in migrations:
            try:
                db.execute(text(migration))
                print(f"  ✓ {migration[:60]}...")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  ⚠ Поле уже существует, пропускаем")
                else:
                    print(f"  ⚠ Ошибка: {e}")
        
        # 2. Добавляем новые поля в таблицу orders
        print("\n2. Добавление полей в таблицу orders...")
        
        order_migrations = [
            "ALTER TABLE orders ADD COLUMN zone TEXT NULL",
            "ALTER TABLE orders ADD COLUMN assigned_driver_id INTEGER NULL",
        ]
        
        for migration in order_migrations:
            try:
                db.execute(text(migration))
                print(f"  ✓ {migration[:60]}...")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  ⚠ Поле уже существует, пропускаем")
                else:
                    print(f"  ⚠ Ошибка: {e}")
        
        # 3. Мигрируем данные
        print("\n3. Миграция данных...")
        
        # Инициализируем новые поля для существующих водителей
        db.execute(text("""
            UPDATE drivers 
            SET status = 'offline',
                current_zone = 'NONE'
            WHERE status IS NULL OR current_zone IS NULL
        """))
        print("  ✓ Установлены начальные значения для водителей")
        
        # Мигрируем старые статусы заказов
        db.execute(text("""
            UPDATE orders 
            SET zone = CASE 
                WHEN pickup_district = 'Новое Жуково' THEN 'NEW_ZHUKOVO'
                WHEN pickup_district = 'Старое Жуково' THEN 'OLD_ZHUKOVO'
                WHEN pickup_district = 'Мысовцево' THEN 'MYSOVTSEVO'
                WHEN pickup_district = 'Авдон' THEN 'AVDON'
                WHEN pickup_district = 'Уптино' THEN 'UPTINO'
                WHEN pickup_district = 'Дёма' THEN 'DEMA'
                ELSE NULL
            END
            WHERE zone IS NULL AND pickup_district IS NOT NULL
        """))
        print("  ✓ Мигрированы зоны заказов из pickup_district")
        
        db.commit()
        
        print("\n" + "=" * 70)
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 70)
        print("\nДобавлены поля:")
        print("  Drivers:")
        print("    - status (offline/online/pending_acceptance/busy)")
        print("    - current_zone (NONE/NEW_ZHUKOVO/OLD_ZHUKOVO/MYSOVTSEVO/AVDON/UPTINO/DEMA)")
        print("    - online_since (время входа на линию)")
        print("    - pending_order_id (ID заказа ожидающего ответа)")
        print("    - pending_until (дедлайн для ответа)")
        print("  Orders:")
        print("    - zone (зона заказа)")
        print("    - assigned_driver_id (ID текущего назначенного водителя)")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ОШИБКА МИГРАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔄 СИСТЕМА МИГРАЦИИ БД\n")
    input("Нажмите Enter для запуска миграции...")
    
    success = migrate()
    
    if success:
        print("\n✅ Миграция применена успешно!")
        print("\nТеперь можно запускать бота с новой системой очередей.")
    else:
        print("\n❌ Миграция завершилась с ошибками.")
        print("Проверьте лог выше и исправьте проблемы.")
    
    input("\nНажмите Enter для выхода...")
    sys.exit(0 if success else 1)

