"""Проверка зоны водителя"""
from database.db import SessionLocal
from bot.models.driver import Driver
from bot.constants import ZONE_KEY_MAP

db = SessionLocal()
try:
    driver = db.query(Driver).filter(Driver.id == 1).first()
    if driver:
        zone_enum = driver.current_zone
        zone_value = zone_enum.value if hasattr(zone_enum, 'value') else zone_enum
        print(f"Driver ID 1:")
        print(f"  current_zone (enum): {zone_enum}")
        print(f"  current_zone (value): {zone_value}")
        print(f"\nZONE_KEY_MAP:")
        for key, value in ZONE_KEY_MAP.items():
            print(f"  '{key}' -> {value}")
finally:
    db.close()

