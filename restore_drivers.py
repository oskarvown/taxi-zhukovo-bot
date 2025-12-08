#!/usr/bin/env python3
"""
Скрипт для экспорта водителей из локальной базы данных
"""
import json
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from database.db import SessionLocal
from bot.models.driver import Driver
from bot.models.user import User

def export_drivers():
    """Экспорт всех водителей в JSON"""
    db = SessionLocal()
    
    try:
        drivers = db.query(Driver).join(User).all()
        
        data = []
        for driver in drivers:
            user = driver.user
            data.append({
                'telegram_id': user.telegram_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'car_model': driver.car_model,
                'car_number': driver.car_number,
                'car_color': driver.car_color,
                'license_number': driver.license_number,
                'rating': driver.rating,
                'rating_avg': driver.rating_avg,
                'rating_count': driver.rating_count,
                'completed_trips_count': driver.completed_trips_count,
                'is_verified': driver.is_verified
            })
        
        output_file = root_dir / 'drivers_backup.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f'✅ Экспортировано {len(data)} водителей в {output_file}')
        return output_file
        
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    export_drivers()













