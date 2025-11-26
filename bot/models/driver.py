"""
Модель водителя
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database.db import Base


class DriverStatus(str, Enum):
    """Статусы водителя"""
    OFFLINE = "offline"
    ONLINE = "online"
    PENDING_ACCEPTANCE = "pending_acceptance"
    BUSY = "busy"


class DriverZone(str, Enum):
    """Зоны обслуживания"""
    NONE = "NONE"
    NEW_ZHUKOVO = "NEW_ZHUKOVO"
    OLD_ZHUKOVO = "OLD_ZHUKOVO"
    MYSOVTSEVO = "MYSOVTSEVO"
    AVDON = "AVDON"
    UPTINO = "UPTINO"
    DEMA = "DEMA"
    SERGEEVKA = "SERGEEVKA"


class Driver(Base):
    """Водитель такси"""
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Информация о автомобиле
    car_model = Column(String, nullable=False)
    car_number = Column(String, nullable=False)
    car_color = Column(String, nullable=True)
    
    # Документы
    license_number = Column(String, nullable=False)
    
    # Статус и рейтинг
    rating = Column(Float, default=5.0)  # Средний рейтинг (DEPRECATED: используйте rating_avg)
    rating_avg = Column(Float, default=0.0)  # Средний рейтинг (истинный)
    rating_count = Column(Integer, default=0)  # Количество оценок
    total_rides = Column(Integer, default=0)  # Общее количество поездок (DEPRECATED: используйте completed_trips_count)
    completed_trips_count = Column(Integer, default=0)  # Счётчик завершённых поездок
    is_verified = Column(Boolean, default=False)
    
    # Новая система статусов и очередей
    status = Column(
        SQLEnum(
            DriverStatus,
            name="driver_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        default=DriverStatus.OFFLINE,
        nullable=False,
    )
    current_zone = Column(
        SQLEnum(
            DriverZone,
            name="driver_zone",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        default=DriverZone.NONE,
        nullable=False,
    )
    online_since = Column(DateTime, nullable=True)  # Время когда вышел на линию в текущей зоне
    pending_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Заказ ожидающий ответа
    pending_until = Column(DateTime, nullable=True)  # Дедлайн для ответа на заказ
    
    # Broadcast-резервация для занятых водителей
    next_finish_zone = Column(String, nullable=True)  # Зона, где завершится текущая поездка
    eta_to_finish = Column(Integer, nullable=True)  # Минуты до завершения текущей поездки
    
    # DEPRECATED: старые поля для обратной совместимости (будут удалены после миграции)
    is_online = Column(Boolean, default=False)
    current_district = Column(String, nullable=True)
    district_updated_at = Column(DateTime, nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="driver_profile", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<Driver(id={self.id}, car={self.car_model} {self.car_number}, rating={self.rating})>"
    
    @property
    def display_info(self) -> str:
        """Информация для отображения клиенту"""
        rating_display = f"{self.rating_avg:.1f}" if self.rating_count > 0 else "Новый"
        trips_display = self.completed_trips_count if self.completed_trips_count > 0 else self.total_rides
        return (
            f"🚗 {self.car_model}\n"
            f"🔢 {self.car_number}\n"
            f"⭐ Рейтинг: {rating_display}\n"
            f"🛣️ Поездок: {trips_display}"
        )

