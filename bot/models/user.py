"""
Модель пользователя
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
)
from database.db import Base


class UserRole(str, Enum):
    """Роли пользователей"""
    CUSTOMER = "customer"
    DRIVER = "driver"
    ADMIN = "admin"


class User(Base):
    """Пользователь системы"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    is_banned = Column(Boolean, default=False, nullable=False, index=True)
    warning_count = Column(Integer, default=0, nullable=False, index=True)
    last_warning_at = Column(DateTime, nullable=True, index=True)
    role = Column(SQLEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        parts = [self.first_name, self.last_name]
        return " ".join([p for p in parts if p]) or self.username or f"User {self.telegram_id}"

