"""
Сервис управления пользователями
"""
from typing import Optional
from sqlalchemy.orm import Session
from telegram import User as TelegramUser
from bot.models import User, UserRole


class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def get_or_create_user(db: Session, telegram_user: TelegramUser) -> User:
        """
        Получить или создать пользователя
        
        Args:
            db: Сессия БД
            telegram_user: Пользователь Telegram
            
        Returns:
            Объект User
        """
        user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
        
        if not user:
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                role=UserRole.CUSTOMER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return user
    
    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    
    @staticmethod
    def is_admin(telegram_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        from bot.config import settings
        return telegram_id in settings.admin_ids
    
    @staticmethod
    def update_phone(db: Session, user: User, phone_number: str) -> User:
        """Обновить номер телефона пользователя"""
        user.phone_number = phone_number
        db.commit()
        db.refresh(user)
        return user

