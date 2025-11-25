#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Проверка истории заказов водителя
"""
from database.db import SessionLocal
from bot.models import User, Driver, Order, OrderStatus
from bot.services import OrderService

telegram_id = 6840100810  # Ваш Telegram ID

print("=" * 70)
print("ПРОВЕРКА ИСТОРИИ ЗАКАЗОВ ВОДИТЕЛЯ")
print("=" * 70)

db = SessionLocal()

try:
    # Находим водителя
    driver_user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not driver_user:
        print("\n❌ Пользователь не найден!")
    else:
        print(f"\n✅ Водитель: {driver_user.full_name}")
        print(f"   User ID в БД: {driver_user.id}")
        print(f"   Telegram ID: {driver_user.telegram_id}")
        
        # Проверяем все заказы где водитель - это мы
        all_orders = db.query(Order).filter(Order.driver_id == driver_user.id).all()
        
        print(f"\n📊 Всего заказов с driver_id={driver_user.id}: {len(all_orders)}")
        
        if all_orders:
            print("\n📋 Все заказы:")
            for order in all_orders:
                print(f"\n   Заказ #{order.id}")
                print(f"   Статус: {order.status}")
                print(f"   Customer ID: {order.customer_id}")
                print(f"   Driver ID: {order.driver_id}")
                print(f"   Откуда: {order.pickup_address}")
                print(f"   Куда: {order.dropoff_address}")
                print(f"   Цена: {order.price} руб.")
                if order.completed_at:
                    print(f"   Завершен: {order.completed_at}")
                print(f"   Создан: {order.created_at}")
        
        # Проверяем COMPLETED заказы
        completed = db.query(Order).filter(
            Order.driver_id == driver_user.id,
            Order.status == OrderStatus.COMPLETED
        ).all()
        
        print(f"\n✅ Завершенных заказов: {len(completed)}")
        
        if completed:
            print("\n📋 Завершенные заказы:")
            for order in completed:
                print(f"\n   Заказ #{order.id}")
                print(f"   Откуда: {order.pickup_address}")
                print(f"   Куда: {order.dropoff_address}")
                print(f"   Цена: {order.price} руб.")
                if order.rating:
                    print(f"   Оценка: {order.rating}/5")
                print(f"   Завершен: {order.completed_at}")
        
        # Проверяем через сервис
        print("\n" + "=" * 70)
        print("ПРОВЕРКА ЧЕРЕЗ OrderService.get_driver_history():")
        print("=" * 70)
        
        history = OrderService.get_driver_history(db, driver_user)
        print(f"\nНайдено заказов через сервис: {len(history)}")
        
        if history:
            for i, order in enumerate(history, 1):
                print(f"\n{i}. Заказ #{order.id}")
                print(f"   Статус: {order.status}")
                print(f"   Откуда: {order.pickup_address}")
                print(f"   Куда: {order.dropoff_address}")
                print(f"   Цена: {order.price} руб.")
        
        # Проверяем все заказы в БД вообще
        print("\n" + "=" * 70)
        print("ВСЕ ЗАКАЗЫ В БД:")
        print("=" * 70)
        
        all_orders_db = db.query(Order).all()
        print(f"\nВсего заказов в БД: {len(all_orders_db)}")
        
        for order in all_orders_db:
            print(f"\nЗаказ #{order.id}")
            print(f"   Статус: {order.status}")
            print(f"   Customer ID: {order.customer_id}")
            print(f"   Driver ID: {order.driver_id}")
            if order.driver_id == driver_user.id:
                print(f"   ✅ ЭТО ВАШ ЗАКАЗ!")
            if order.customer_id == driver_user.id:
                print(f"   ⚠️ Вы клиент этого заказа")

except Exception as e:
    print(f"\n❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n" + "=" * 70)

