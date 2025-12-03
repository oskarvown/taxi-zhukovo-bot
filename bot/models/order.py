"""
Модель заказа такси
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
    Boolean,
)
from sqlalchemy.orm import relationship
from database.db import Base


class OrderStatus(str, Enum):
    """Статусы заказа"""
    # Новая система очередей
    NEW = "new"  # Только создан, ищем водителя
    ASSIGNED = "assigned"  # Назначен водителю, ждём ответа
    ACCEPTED = "accepted"  # Водитель принял заказ
    ARRIVED = "arrived"  # Водитель подъехал
    ONBOARD = "onboard"  # Поездка началась (клиент в машине)
    FINISHED = "finished"  # Поездка завершена
    FALLBACK = "fallback"  # Поиск по всем зонам (после 3 минут)
    EXPIRED = "expired"  # Никто не принял
    # Старые статусы (для обратной совместимости)
    PENDING = "pending"  # Ожидает водителя (deprecated, mapping -> NEW)
    IN_PROGRESS = "in_progress"  # Поездка в процессе (deprecated, mapping -> ONBOARD)
    COMPLETED = "completed"  # Завершен (deprecated, mapping -> FINISHED)
    CANCELLED = "cancelled"  # Отменен


class District(str, Enum):
    """Районы обслуживания"""
    NOVOE_ZHUKOVO = "Новое Жуково"
    STAROE_ZHUKOVO = "Старое Жуково"
    MYSOVTSEVO = "Мысовцево"
    AVDON = "Авдон"
    UPTINO = "Уптино"
    DEMA = "Дёма"


class OrderZone(str, Enum):
    """Зоны для заказов (синхронизировано с DriverZone)"""
    NEW_ZHUKOVO = "NEW_ZHUKOVO"
    OLD_ZHUKOVO = "OLD_ZHUKOVO"
    MYSOVTSEVO = "MYSOVTSEVO"
    AVDON = "AVDON"
    UPTINO = "UPTINO"
    DEMA = "DEMA"
    SERGEEVKA = "SERGEEVKA"


class OrderTariff(str, Enum):
    """Тип тарифа заказа"""
    FIXED = "fixed"
    NEGOTIATED = "negotiated"


class IntercityOriginZone(str, Enum):
    """Откуда стартует межгород"""
    DEMA = "DEMA"
    OLD_ZHUKOVO = "OLD_ZHUKOVO"
    MYSOVTSEVO = "MYSOVTSEVO"


class Order(Base):
    """Заказ такси"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Участники
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Новая система очередей
    zone = Column(
        SQLEnum(
            OrderZone,
            name="order_zone",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=True,  # nullable для старых заказов
    )
    assigned_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)  # Текущий назначенный водитель
    
    # Адреса
    pickup_district = Column(String, nullable=True)  # Район забора
    pickup_address = Column(String, nullable=False)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    
    dropoff_address = Column(String, nullable=False)
    dropoff_latitude = Column(Float, nullable=True)
    dropoff_longitude = Column(Float, nullable=True)
    
    # Информация о заказе
    status = Column(
        SQLEnum(
            OrderStatus,
            name="order_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    distance_km = Column(Float, nullable=True)
    price = Column(Float, nullable=False)
    tariff = Column(
        SQLEnum(
            OrderTariff,
            name="order_tariff",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        default=OrderTariff.FIXED,
        nullable=False,
    )
    is_intercity = Column(Boolean, default=False, nullable=False, index=True)
    from_zone = Column(
        SQLEnum(
            IntercityOriginZone,
            name="intercity_origin_zone",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=True,
    )
    to_text = Column(Text, nullable=True)
    selected_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    
    # Broadcast-режим для специальных зон
    is_broadcast = Column(Boolean, default=False, nullable=False, index=True)  # Режим широковещания
    reserved_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)  # Водитель-резерв
    reserve_expires_at = Column(DateTime, nullable=True)  # Когда истечет резерв
    
    # Комментарии и оценка
    customer_comment = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    feedback = Column(Text, nullable=True)
    rating_comment = Column(Text, nullable=True)  # Комментарий к оценке
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)  # Водитель подъехал
    started_at = Column(DateTime, nullable=True)  # Поездка началась
    finished_at = Column(DateTime, nullable=True)  # Поездка завершена
    completed_at = Column(DateTime, nullable=True)  # DEPRECATED: используйте finished_at
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], backref="orders_as_customer")
    driver = relationship("User", foreign_keys=[driver_id], backref="orders_as_driver")
    selected_driver = relationship("Driver", foreign_keys=[selected_driver_id], backref="intercity_orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, status={self.status}, price={self.price})>"
    
    @property
    def display_info(self) -> str:
        """Информация для отображения (с ценой, для водителей/админов)"""
        status_emoji = {
            OrderStatus.PENDING: "⏳",
            OrderStatus.NEW: "🆕",
            OrderStatus.ASSIGNED: "📤",
            OrderStatus.ACCEPTED: "✅",
            OrderStatus.IN_PROGRESS: "🚗",
            OrderStatus.COMPLETED: "✔️",
            OrderStatus.CANCELLED: "❌"
        }
        
        if self.is_intercity:
            origin_map = {
                IntercityOriginZone.DEMA: "Дёма",
                IntercityOriginZone.OLD_ZHUKOVO: "Жуково",
                IntercityOriginZone.MYSOVTSEVO: "Мысовцево",
            }
            origin = origin_map.get(self.from_zone, self.pickup_address or "—")
            created = self.created_at.strftime('%d.%m.%Y %H:%M')
            return (
                f"{status_emoji.get(self.status, '🛣')} Межгород #{self.id}\n"
                f"🏁 Откуда: {origin}\n"
                f"🎯 Куда: {self.to_text or self.dropoff_address}\n"
                f"📅 Создан: {created}"
            )
        
        district_text = f"🏘 Район: {self.pickup_district}\n" if self.pickup_district else ""
        price_text = f"{self.price:.0f} руб." if self.price else "—"
        
        return (
            f"{status_emoji.get(self.status, '📋')} Заказ #{self.id}\n"
            f"{district_text}"
            f"📍 Откуда: {self.pickup_address}\n"
            f"📍 Куда: {self.dropoff_address}\n"
            f"💰 Цена: {price_text}\n"
            f"📅 Создан: {self.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

    @property
    def display_info_public(self) -> str:
        """Информация для отображения клиенту (БЕЗ цены)"""
        status_emoji = {
            OrderStatus.PENDING: "⏳",
            OrderStatus.NEW: "🆕",
            OrderStatus.ASSIGNED: "📤",
            OrderStatus.ACCEPTED: "✅",
            OrderStatus.IN_PROGRESS: "🚗",
            OrderStatus.COMPLETED: "✔️",
            OrderStatus.CANCELLED: "❌"
        }
        
        if self.is_intercity:
            origin_map = {
                IntercityOriginZone.DEMA: "Дёма",
                IntercityOriginZone.OLD_ZHUKOVO: "Жуково",
                IntercityOriginZone.MYSOVTSEVO: "Мысовцево",
            }
            origin = origin_map.get(self.from_zone, self.pickup_address or "—")
            created = self.created_at.strftime('%d.%m.%Y %H:%M')
            return (
                f"{status_emoji.get(self.status, '🛣')} Межгород #{self.id}\n"
                f"🏁 Откуда: {origin}\n"
                f"🎯 Куда: {self.to_text or self.dropoff_address}\n"
                f"📅 Создан: {created}"
            )
        
        district_text = f"🏘 Район: {self.pickup_district}\n" if self.pickup_district else ""
        
        return (
            f"{status_emoji.get(self.status, '📋')} Заказ #{self.id}\n"
            f"{district_text}"
            f"📍 Откуда: {self.pickup_address}\n"
            f"📍 Куда: {self.dropoff_address}\n"
            f"📅 Создан: {self.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

