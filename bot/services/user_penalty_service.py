"""
Сервис предупреждений и банов пользователей
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from bot.models import User

logger = logging.getLogger(__name__)

# ID пользователя, исключенного из системы предупреждений и банов
EXEMPT_USER_TELEGRAM_ID = 6840100810


class UserPenaltyService:
    """Логика предупреждений и перманентного бана"""

    WARNING_LIFETIME_DAYS = 60

    @classmethod
    def warn_or_ban(cls, db: Session, user: User) -> str:
        """
        Применить предупреждение или бан.

        Returns:
            "warning" | "banned" | "ignored"
        """
        # Проверяем, не является ли пользователь исключенным
        if user.telegram_id == EXEMPT_USER_TELEGRAM_ID:
            logger.info("penalty: exempt user_id=%s telegram_id=%s - skipping penalty", user.id, user.telegram_id)
            return "ignored"
        
        if user.is_banned:
            return "ignored"

        now = datetime.utcnow()
        cutoff = now - timedelta(days=cls.WARNING_LIFETIME_DAYS)

        recent_warning = (
            user.warning_count > 0 and user.last_warning_at and user.last_warning_at >= cutoff
        )

        if not recent_warning:
            user.warning_count = 1
            user.last_warning_at = now
            db.commit()
            logger.warning("penalty: warning user_id=%s phone=%s", user.id, user.phone_number)
            return "warning"

        user.is_banned = True
        user.warning_count = user.warning_count or 1
        user.last_warning_at = now
        db.commit()
        logger.error("penalty: banned user_id=%s phone=%s", user.id, user.phone_number)
        return "banned"

    @classmethod
    def clear_expired_warnings(cls, db: Session) -> int:
        """Сбросить предупреждения старше 60 дней"""
        cutoff = datetime.utcnow() - timedelta(days=cls.WARNING_LIFETIME_DAYS)
        affected_users = (
            db.query(User)
            .filter(
                User.is_banned.is_(False),
                User.warning_count > 0,
                User.last_warning_at.isnot(None),
                User.last_warning_at < cutoff,
            )
            .all()
        )

        for user in affected_users:
            user.warning_count = 0
            user.last_warning_at = None

        if affected_users:
            db.commit()
        return len(affected_users)

