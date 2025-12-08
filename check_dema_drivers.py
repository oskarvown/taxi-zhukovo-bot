#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для проверки водителей в зоне DEMA
Выводит всех водителей, у которых current_zone = "DEMA"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.db import SessionLocal
from bot.models.driver import Driver, DriverZone, DriverStatus
from bot.constants import PUBLIC_ZONE_LABELS

db = SessionLocal()
try:
    # Находим всех водителей в зоне DEMA
    dema_drivers = db.query(Driver).filter(
        Driver.current_zone == DriverZone.DEMA
    ).all()
    
    print("=" * 70)
    print(f"ВОДИТЕЛИ В ЗОНЕ DEMA (всего: {len(dema_drivers)})")
    print("=" * 70)
    
    if not dema_drivers:
        print("\n✅ В зоне DEMA нет водителей")
    else:
        print(f"\nНайдено {len(dema_drivers)} водителей в зоне DEMA:\n")
        
        for driver in dema_drivers:
            status_value = driver.status.value if hasattr(driver.status, 'value') else str(driver.status)
            zone_value = driver.current_zone.value if hasattr(driver.current_zone, 'value') else str(driver.current_zone)
            
            print(f"ID: {driver.id}")
            if driver.user:
                print(f"  Имя: {driver.user.full_name}")
                print(f"  Telegram ID: {driver.user.telegram_id}")
            else:
                print(f"  ⚠️ User не найден!")
            print(f"  Статус: {status_value}")
            print(f"  Зона: {zone_value} ({PUBLIC_ZONE_LABELS.get(zone_value, 'неизвестно')})")
            print(f"  Online since: {driver.online_since}")
            print(f"  Pending order: {driver.pending_order_id}")
            print(f"  Авто: {driver.car_model} ({driver.car_number})")
            print("-" * 70)
    
    # Проверяем также водителей с ONLINE статусом в зоне DEMA
    online_dema = db.query(Driver).filter(
        Driver.current_zone == DriverZone.DEMA,
        Driver.status == DriverStatus.ONLINE
    ).all()
    
    print(f"\nОнлайн водителей в зоне DEMA: {len(online_dema)}")
    
    # Проверяем водителей с невалидными зонами
    from bot.constants import ZONES
    all_drivers = db.query(Driver).all()
    invalid_zone_drivers = []
    
    for driver in all_drivers:
        zone_value = driver.current_zone.value if hasattr(driver.current_zone, 'value') else str(driver.current_zone)
        if zone_value not in ZONES and zone_value != "NONE":
            invalid_zone_drivers.append((driver.id, zone_value))
    
    if invalid_zone_drivers:
        print(f"\n⚠️ Водители с невалидными зонами: {len(invalid_zone_drivers)}")
        for driver_id, zone in invalid_zone_drivers:
            print(f"  Водитель {driver_id}: зона '{zone}'")
    else:
        print("\n✅ Все водители имеют валидные зоны")
        
finally:
    db.close()




