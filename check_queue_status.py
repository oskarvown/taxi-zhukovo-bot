"""Проверка статуса очередей"""
from database.db import SessionLocal
from bot.models.driver import Driver, DriverStatus
from bot.services.queue_manager import queue_manager

db = SessionLocal()
try:
    print("Перестройка очередей...")
    queue_manager.rebuild_from_db(db)
    
    print("\nВодители в БД (онлайн):")
    drivers = db.query(Driver).filter(Driver.status == DriverStatus.ONLINE).all()
    for d in drivers:
        zone = d.current_zone.value if hasattr(d.current_zone, 'value') else d.current_zone
        print(f"  Driver {d.id}: status={d.status}, zone={zone}, pending={d.pending_order_id}")
    
    print("\nСостояние очередей:")
    for zone, queue in queue_manager._queues.items():
        if queue:
            print(f"  {zone}: {len(queue)} водителей {queue}")
        else:
            print(f"  {zone}: пусто")
finally:
    db.close()

