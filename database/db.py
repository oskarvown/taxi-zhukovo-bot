"""
Настройка базы данных
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from bot.config import settings

# Создание движка БД
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db() -> Session:
    """Получить сессию БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация базы данных"""
    # Импортируем все модели
    from bot.models import User, Driver, Order
    
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    # Нормализуем значения статусов заказов (поддержка старых данных)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE orders
                SET status = lower(status)
                WHERE status IS NOT NULL AND status != lower(status)
                """
            )
        )
    
    print("✅ База данных инициализирована")

