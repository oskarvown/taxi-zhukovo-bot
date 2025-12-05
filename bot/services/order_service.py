"""
Сервис управления заказами
"""
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

from bot.models import (
    Order,
    OrderStatus,
    User,
    Driver,
    IntercityOriginZone,
    OrderTariff,
)


class OrderService:
    """Сервис для работы с заказами"""
    
    @staticmethod
    def create_order(
        db: Session,
        customer: User,
        pickup_address: str,
        pickup_lat: Optional[float] = None,
        pickup_lon: Optional[float] = None,
        dropoff_address: str = "",
        dropoff_lat: Optional[float] = None,
        dropoff_lon: Optional[float] = None,
        pickup_district: Optional[str] = None,
        comment: Optional[str] = None,
        price: Optional[float] = None,
        dropoff_zone: Optional[str] = None,
        is_broadcast: bool = False,
    ) -> Order:
        """
        Создать новый заказ
        
        Args:
            db: Сессия БД
            customer: Пользователь-заказчик
            pickup_address: Адрес подачи
            pickup_lat: Широта подачи
            pickup_lon: Долгота подачи
            dropoff_address: Адрес назначения
            dropoff_lat: Широта назначения
            dropoff_lon: Долгота назначения
            pickup_district: Район подачи
            comment: Комментарий к заказу
            price: Фиксированная стоимость поездки
            dropoff_zone: Зона назначения (для справки)
            
        Returns:
            Созданный заказ
        """
        if price is None:
            raise ValueError("Для создания заказа требуется фиксированная стоимость.")

        dropoff_address_text = dropoff_address
        if dropoff_zone:
            dropoff_address_text = f"{dropoff_address} (зона: {dropoff_zone})"
        
        # Преобразуем район подачи в зону для системы очередей
        zone_key = None
        if pickup_district:
            from bot.handlers.user_queue import map_district_to_zone
            zone_key = map_district_to_zone(pickup_district)

        order = Order(
            customer_id=customer.id,
            pickup_district=pickup_district,
            pickup_address=pickup_address,
            pickup_latitude=pickup_lat,
            pickup_longitude=pickup_lon,
            dropoff_address=dropoff_address_text,
            dropoff_latitude=dropoff_lat,
            dropoff_longitude=dropoff_lon,
            distance_km=None,
            price=price,
            customer_comment=comment,
            status=OrderStatus.NEW if is_broadcast else OrderStatus.PENDING,
            zone=zone_key,
            tariff=OrderTariff.FIXED,
            is_intercity=False,
            is_broadcast=is_broadcast,
        )
        
        db.add(order)
        db.commit()
        db.refresh(order)
        
        return order
    
    @staticmethod
    def create_intercity_order(
        db: Session,
        customer: User,
        origin_zone: IntercityOriginZone,
        destination_text: str,
    ) -> Order:
        """Создать новый межгородской заказ"""
        origin_names = {
            IntercityOriginZone.DEMA: "Дёма",
            IntercityOriginZone.OLD_ZHUKOVO: "Жуково",
            IntercityOriginZone.MYSOVTSEVO: "Мысовцево",
        }
        pickup_address = origin_names.get(origin_zone, origin_zone.value)

        order = Order(
            customer_id=customer.id,
            pickup_address=pickup_address,
            dropoff_address=destination_text,
            price=0.0,
            status=OrderStatus.NEW,
            tariff=OrderTariff.NEGOTIATED,
            is_intercity=True,
            from_zone=origin_zone,
            to_text=destination_text,
        )

        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def get_pending_orders(db: Session) -> List[Order]:
        """Получить все заказы, ожидающие водителя"""
        return db.query(Order).filter(Order.status == OrderStatus.PENDING).all()
    
    @staticmethod
    def get_active_order_by_customer(db: Session, customer: User) -> Optional[Order]:
        """Получить активный заказ клиента"""
        active_statuses = [
            OrderStatus.PENDING,
            OrderStatus.NEW,
            OrderStatus.ASSIGNED,
            OrderStatus.FALLBACK,
            OrderStatus.ACCEPTED,
            OrderStatus.IN_PROGRESS,
        ]
        return (
            db.query(Order)
            .filter(
                Order.customer_id == customer.id,
                Order.status.in_(active_statuses),
            )
            .order_by(Order.created_at.desc())
            .first()
        )
    
    @staticmethod
    def get_active_order_by_driver(db: Session, driver: User) -> Optional[Order]:
        """Получить активный заказ водителя"""
        active_statuses = [
            OrderStatus.ASSIGNED,
            OrderStatus.ACCEPTED,
            OrderStatus.IN_PROGRESS,
        ]
        return (
            db.query(Order)
            .filter(
                Order.driver_id == driver.id,
                Order.status.in_(active_statuses),
            )
            .order_by(Order.created_at.desc())
            .first()
        )
    
    @staticmethod
    def accept_order(db: Session, order: Order, driver: User) -> Order:
        """Водитель принимает заказ"""
        order.driver_id = driver.id
        order.status = OrderStatus.ACCEPTED
        order.accepted_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def set_arrived(db: Session, order: Order) -> Order:
        """Водитель подъехал (идемпотентно)"""
        # Идемпотентность: если уже в нужном статусе, просто возвращаем
        if order.status == OrderStatus.ARRIVED:
            return order
        
        order.status = OrderStatus.ARRIVED
        if not order.arrived_at:
            order.arrived_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def set_started(db: Session, order: Order) -> Order:
        """Начать поездку (клиент в машине) (идемпотентно)"""
        # Идемпотентность: если уже в нужном статусе, просто возвращаем
        if order.status == OrderStatus.ONBOARD:
            return order
        
        order.status = OrderStatus.ONBOARD
        if not order.started_at:
            order.started_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def set_finished(db: Session, order: Order) -> Order:
        """
        Завершить поездку (идемпотентно)
        
        Автоматически инкрементирует счётчик завершённых поездок у водителя.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Идемпотентность: если уже в нужном статусе, просто возвращаем
        if order.status == OrderStatus.FINISHED:
            return order
        
        order.status = OrderStatus.FINISHED
        if not order.finished_at:
            order.finished_at = datetime.utcnow()
        # Для обратной совместимости
        if not order.completed_at:
            order.completed_at = datetime.utcnow()
        
        # Инкрементируем счётчик завершённых поездок у водителя
        if order.assigned_driver_id:
            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if driver:
                driver.completed_trips_count = (driver.completed_trips_count or 0) + 1
                logger.info(
                    f"driver_stats_updated driver={driver.id} trips={driver.completed_trips_count} "
                    f"avg={driver.rating_avg:.2f} cnt={driver.rating_count}"
                )
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def start_order(db: Session, order: Order) -> Order:
        """Начать выполнение заказа (DEPRECATED: используйте set_started)"""
        return OrderService.set_started(db, order)
    
    @staticmethod
    def complete_order(db: Session, order: Order) -> Order:
        """Завершить заказ (DEPRECATED: используйте set_finished)"""
        return OrderService.set_finished(db, order)
    
    @staticmethod
    def cancel_order(db: Session, order: Order) -> Order:
        """Отменить заказ"""
        from bot.models.driver import DriverStatus
        from bot.services.queue_manager import queue_manager
        
        order.status = OrderStatus.CANCELLED
        order.assigned_driver_id = None
        order.selected_driver_id = None
        
        # Находим водителя, у которого этот заказ в pending_order_id
        if order.id:
            driver_with_pending = db.query(Driver).filter(
                Driver.pending_order_id == order.id
            ).first()
            
            if driver_with_pending:
                # Очищаем pending_order_id и pending_until
                driver_with_pending.pending_order_id = None
                driver_with_pending.pending_until = None
                
                # Если водитель был в статусе PENDING_ACCEPTANCE, возвращаем его в ONLINE
                if driver_with_pending.status == DriverStatus.PENDING_ACCEPTANCE:
                    driver_with_pending.status = DriverStatus.ONLINE
                    # ВАЖНО: Не обновляем online_since - сохраняем FIFO порядок
                    # Водитель возвращается в очередь с тем же приоритетом
                    if driver_with_pending.online_since is None:
                        driver_with_pending.online_since = datetime.utcnow()
                    
                    # Возвращаем водителя в очередь
                    zone = driver_with_pending.current_zone.value if hasattr(driver_with_pending.current_zone, 'value') else driver_with_pending.current_zone
                    if zone and zone != "NONE":
                        queue_manager.add_driver(driver_with_pending.id, zone, db)
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def set_rating(db: Session, order: Order, rating: int, comment: Optional[str] = None) -> Order:
        """
        Оценить заказ (с поддержкой изменения оценки в течение 24ч)
        
        Автоматически пересчитывает средний рейтинг водителя на основе
        всех оценок в БД (истинный пересчёт).
        
        Args:
            db: Сессия БД
            order: Заказ для оценки
            rating: Оценка (1-5 звёзд)
            comment: Опциональный комментарий
            
        Returns:
            Обновлённый заказ
        """
        import logging
        from datetime import timedelta
        logger = logging.getLogger(__name__)
        
        # Проверка, можно ли изменить оценку (в течение 24ч после завершения)
        is_changed = order.rating is not None
        can_change = False
        if order.finished_at:
            time_since_finish = datetime.utcnow() - order.finished_at
            can_change = time_since_finish <= timedelta(hours=24)
        
        if is_changed and not can_change:
            logger.warning(f"rating_set order={order.id} stars={rating} changed=False (time limit exceeded)")
            return order
        
        # Сохраняем оценку
        old_rating = order.rating
        order.rating = rating
        order.rating_comment = comment
        # Для обратной совместимости
        if comment:
            order.feedback = comment
        
        db.commit()
        db.refresh(order)
        
        logger.info(f"rating_set order={order.id} stars={rating} changed={is_changed} old_rating={old_rating}")
        
        # Обновить рейтинг водителя через ИСТИННЫЙ пересчёт из БД
        if order.assigned_driver_id:
            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if driver:
                # Истинный пересчёт: AVG и COUNT по всем оценкам в orders
                from sqlalchemy import func
                result = db.query(
                    func.avg(Order.rating),
                    func.count(Order.rating)
                ).filter(
                    Order.assigned_driver_id == driver.id,
                    Order.rating.isnot(None)
                ).first()
                
                avg_rating = result[0] if result[0] is not None else 0.0
                rating_count = result[1] if result[1] is not None else 0
                
                driver.rating_avg = round(float(avg_rating), 2)
                driver.rating_count = rating_count
                # Обновляем и старое поле для совместимости
                driver.rating = round(float(avg_rating), 2)
                
                db.commit()
                
                logger.info(
                    f"driver_stats_updated driver={driver.id} trips={driver.completed_trips_count} "
                    f"avg={driver.rating_avg:.2f} cnt={driver.rating_count}"
                )
        
        return order
    
    @staticmethod
    def rate_order(db: Session, order: Order, rating: int, feedback: Optional[str] = None) -> Order:
        """Оценить заказ (DEPRECATED: используйте set_rating)"""
        return OrderService.set_rating(db, order, rating, feedback)
    
    @staticmethod
    def set_selected_driver(db: Session, order: Order, driver: Driver) -> Order:
        """Выбрать водителя для межгорода"""
        order.selected_driver_id = driver.id
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def confirm_intercity_order(db: Session, order: Order, driver: Driver) -> Order:
        """Подтвердить межгородской заказ после выбора клиента"""
        order.driver_id = driver.user_id
        order.selected_driver_id = driver.id
        order.assigned_driver_id = driver.id  # Для работы стадий поездки
        order.accepted_at = datetime.utcnow()
        order.status = OrderStatus.ACCEPTED
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_customer_history(db: Session, customer: User, limit: int = 10) -> List[Order]:
        """
        Получить историю заказов клиента (DEPRECATED: используйте get_user_order_history)
        """
        return db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.status == OrderStatus.COMPLETED
        ).order_by(Order.completed_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_driver_history(db: Session, driver: User, limit: int = 10) -> List[Order]:
        """
        Получить историю заказов водителя (DEPRECATED: используйте get_driver_order_history)
        """
        return db.query(Order).filter(
            Order.driver_id == driver.id,
            Order.status == OrderStatus.COMPLETED
        ).order_by(Order.completed_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_order_history(db: Session, user_id: int, limit: int = 10, offset: int = 0) -> List[Order]:
        """
        Получить историю заказов клиента (с пагинацией)
        
        Возвращает завершённые, отменённые и истёкшие заказы.
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            limit: Количество записей (по умолчанию 10)
            offset: Смещение для пагинации (по умолчанию 0)
            
        Returns:
            Список заказов (сортировка по finished_at DESC)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        history_statuses = [OrderStatus.FINISHED, OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.COMPLETED]
        
        orders = db.query(Order).filter(
            Order.customer_id == user_id,
            Order.status.in_(history_statuses)
        ).order_by(
            Order.finished_at.desc().nullslast(),
            Order.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        logger.info(f"history_user served uid={user_id} count={len(orders)} offset={offset}")
        
        return orders
    
    @staticmethod
    def get_driver_order_history(db: Session, driver_id: int, limit: int = 10, offset: int = 0) -> List[Order]:
        """
        Получить историю заказов водителя (с пагинацией)
        
        Возвращает завершённые и отменённые заказы, где водитель был назначен.
        
        Args:
            db: Сессия БД
            driver_id: ID водителя (Driver.id, не User.id)
            limit: Количество записей (по умолчанию 10)
            offset: Смещение для пагинации (по умолчанию 0)
            
        Returns:
            Список заказов (сортировка по finished_at DESC)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        history_statuses = [OrderStatus.FINISHED, OrderStatus.CANCELLED, OrderStatus.COMPLETED]
        
        orders = db.query(Order).filter(
            Order.assigned_driver_id == driver_id,
            Order.status.in_(history_statuses)
        ).order_by(
            Order.finished_at.desc().nullslast(),
            Order.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        logger.info(f"history_driver served driver_id={driver_id} count={len(orders)} offset={offset}")
        
        return orders

