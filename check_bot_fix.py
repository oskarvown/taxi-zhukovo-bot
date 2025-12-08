#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Быстрая диагностика проблем с ботом после обновления
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("ДИАГНОСТИКА БОТА ПОСЛЕ ОБНОВЛЕНИЯ")
print("=" * 70)

errors = []

# 1. Проверка импортов
print("\n1. Проверка импортов...")
try:
    from bot.models import DriverZone, DriverStatus
    print("   ✓ DriverZone импортируется")
except Exception as e:
    print(f"   ✗ Ошибка импорта DriverZone: {e}")
    errors.append(f"Импорт DriverZone: {e}")

try:
    from bot.handlers.admin import admin_reset_drivers, admin_check_dema_drivers
    print("   ✓ Административные функции импортируются")
except Exception as e:
    print(f"   ✗ Ошибка импорта admin функций: {e}")
    errors.append(f"Импорт admin функций: {e}")

try:
    from bot.services.queue_manager import queue_manager
    print("   ✓ QueueManager импортируется")
except Exception as e:
    print(f"   ✗ Ошибка импорта QueueManager: {e}")
    errors.append(f"Импорт QueueManager: {e}")

# 2. Проверка методов QueueManager
print("\n2. Проверка методов QueueManager...")
try:
    from bot.services.queue_manager import queue_manager
    if hasattr(queue_manager, '_remove_driver_from_all_zones'):
        print("   ✓ Метод _remove_driver_from_all_zones существует")
    else:
        print("   ✗ Метод _remove_driver_from_all_zones не найден!")
        errors.append("Метод _remove_driver_from_all_zones не найден")
    
    if hasattr(queue_manager, 'add_driver'):
        print("   ✓ Метод add_driver существует")
    else:
        print("   ✗ Метод add_driver не найден!")
        errors.append("Метод add_driver не найден")
except Exception as e:
    print(f"   ✗ Ошибка проверки методов: {e}")
    errors.append(f"Проверка методов: {e}")

# 3. Проверка синтаксиса файлов
print("\n3. Проверка синтаксиса файлов...")
files_to_check = [
    "bot/handlers/admin.py",
    "bot/handlers/driver_queue.py",
    "bot/handlers/driver_trip.py",
    "bot/services/queue_manager.py",
    "bot/services/order_service.py",
]

for file_path in files_to_check:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        print(f"   ✓ {file_path}")
    except SyntaxError as e:
        print(f"   ✗ Синтаксическая ошибка в {file_path}: {e}")
        errors.append(f"Синтаксис {file_path}: {e}")
    except Exception as e:
        print(f"   ⚠ Не удалось проверить {file_path}: {e}")

# 4. Проверка импортов в bot/models/__init__.py
print("\n4. Проверка экспортов в bot/models/__init__.py...")
try:
    from bot.models import DriverZone
    print("   ✓ DriverZone экспортируется через bot.models")
except Exception as e:
    print(f"   ✗ DriverZone не экспортируется: {e}")
    errors.append(f"Экспорт DriverZone: {e}")

# Итог
print("\n" + "=" * 70)
if errors:
    print(f"❌ НАЙДЕНО ОШИБОК: {len(errors)}")
    for error in errors:
        print(f"   - {error}")
    print("\nНужно исправить эти ошибки!")
else:
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("\nБот должен работать. Если есть проблемы - проверьте логи запуска.")
print("=" * 70)




