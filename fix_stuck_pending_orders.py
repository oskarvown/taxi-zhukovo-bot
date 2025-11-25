"""
Скрипт для очистки зависших pending_order_id у водителей

Использование: python fix_stuck_pending_orders.py
"""
import sys
from database.db import SessionLocal, engine
from bot.models.driver import Driver, DriverStatus
from bot.models.order import Order, OrderStatus
from bot.services.queue_manager import queue_manager
from datetime import datetime

def fix_stuck_pending_orders():
    """Очистить зависшие pending_order_id у водителей"""
    db = SessionLocal()
    
    try:
        # Находим всех водителей с pending_order_id
        drivers_with_pending = db.query(Driver).filter(
            Driver.pending_order_id.isnot(None)
        ).all()
        
        print(f"Найдено водителей с pending_order_id: {len(drivers_with_pending)}")
        
        fixed_count = 0
        
        for driver in drivers_with_pending:
            order_id = driver.pending_order_id
            order = db.query(Order).filter(Order.id == order_id).first()
            
            # Проверяем статус заказа
            if not order:
                # Заказ не найден - очищаем
                print(f"  Водитель {driver.id}: заказ {order_id} не найден, очищаем pending_order_id")
                driver.pending_order_id = None
                driver.pending_until = None
                if driver.status == DriverStatus.PENDING_ACCEPTANCE:
                    driver.status = DriverStatus.ONLINE
                    driver.online_since = datetime.utcnow()
                fixed_count += 1
            elif order.status in [OrderStatus.CANCELLED, OrderStatus.COMPLETED, OrderStatus.EXPIRED]:
                # Заказ уже завершен/отменен - очищаем
                print(f"  Водитель {driver.id}: заказ {order_id} в статусе {order.status}, очищаем pending_order_id")
                driver.pending_order_id = None
                driver.pending_until = None
                if driver.status == DriverStatus.PENDING_ACCEPTANCE:
                    driver.status = DriverStatus.ONLINE
                    driver.online_since = datetime.utcnow()
                    # Возвращаем в очередь
                    zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
                    if zone and zone != "NONE":
                        queue_manager.add_driver(driver.id, zone, db)
                fixed_count += 1
            else:
                print(f"  Водитель {driver.id}: заказ {order_id} в статусе {order.status} - оставляем как есть")
        
        if fixed_count > 0:
            db.commit()
            print(f"\nИсправлено водителей: {fixed_count}")
        else:
            print("\nЗависших pending_order_id не найдено")
        
        # Показываем текущее состояние
        print("\nТекущее состояние водителей с pending_order_id:")
        drivers_with_pending_after = db.query(Driver).filter(
            Driver.pending_order_id.isnot(None)
        ).all()
        
        for driver in drivers_with_pending_after:
            order = db.query(Order).filter(Order.id == driver.pending_order_id).first()
            order_status = order.status if order else "НЕ НАЙДЕН"
            print(f"  Водитель {driver.id}: pending_order_id={driver.pending_order_id}, статус заказа={order_status}")
        
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    import io
    # Устанавливаем UTF-8 для вывода
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("Очистка зависших pending_order_id у водителей...\n")
    fix_stuck_pending_orders()
    print("\nГотово!")

