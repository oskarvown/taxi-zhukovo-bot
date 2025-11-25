#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест принятия заказа
"""
from database.db import SessionLocal
from bot.models import User, UserRole, Driver, Order, OrderStatus
from bot.services import OrderService

print("=" * 70)
print("ТЕСТ ПРИНЯТИЯ ЗАКАЗА")
print("=" * 70)

db = SessionLocal()

try:
    # Находим водителя
    driver_user = db.query(User).filter(User.telegram_id == 6840100810).first()
    
    if not driver_user:
        print("\n❌ Водитель не найден!")
        print("Выполните: python q.py")
    else:
        print(f"\n✅ Водитель: {driver_user.full_name}")
        print(f"   Роль: {driver_user.role}")
        
        driver_profile = db.query(Driver).filter(Driver.user_id == driver_user.id).first()
        if driver_profile:
            print(f"   Автомобиль: {driver_profile.car_model} ({driver_profile.car_number})")
            print(f"   Верифицирован: {'Да' if driver_profile.is_verified else 'Нет'}")
            print(f"   Онлайн: {'Да' if driver_profile.is_online else 'Нет'}")
        
        # Ищем pending заказы
        pending_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING).all()
        
        if not pending_orders:
            print("\n⚠️ Нет pending заказов")
            print("Создайте заказ через бота")
        else:
            print(f"\n📋 Найдено {len(pending_orders)} pending заказов:")
            for order in pending_orders:
                print(f"\n   Заказ #{order.id}")
                print(f"   Район: {order.pickup_district}")
                print(f"   Откуда: {order.pickup_address}")
                print(f"   Куда: {order.dropoff_address}")
                print(f"   Статус: {order.status}")
                print(f"   Цена: {order.price} руб.")
                
                # Проверяем, может ли водитель принять заказ
                if driver_user.role != UserRole.DRIVER:
                    print(f"   ❌ Водитель не имеет роль DRIVER")
                elif not driver_profile:
                    print(f"   ❌ Нет профиля водителя")
                elif not driver_profile.is_verified:
                    print(f"   ❌ Водитель не верифицирован")
                else:
                    # Проверяем активные заказы
                    active_order = OrderService.get_active_order_by_driver(db, driver_user)
                    if active_order:
                        print(f"   ⚠️ У водителя уже есть активный заказ #{active_order.id}")
                    else:
                        print(f"   ✅ Водитель МОЖЕТ принять этот заказ")
                        
                        # Спрашиваем, принять ли заказ для теста
                        answer = input(f"\n   Принять заказ #{order.id} для теста? (да/нет): ")
                        if answer.lower() in ['да', 'yes', 'y', 'д']:
                            try:
                                OrderService.accept_order(db, order, driver_user)
                                print(f"   ✅ Заказ #{order.id} успешно принят!")
                                print(f"   Статус изменен на: {order.status}")
                            except Exception as e:
                                print(f"   ❌ Ошибка: {e}")
                                import traceback
                                traceback.print_exc()

except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n" + "=" * 70)

