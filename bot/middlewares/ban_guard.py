"""
Middleware, блокирующий действия забаненных пользователей
"""
from __future__ import annotations

import logging
from telegram import Update  # pyright: ignore[reportMissingImports]
from telegram.ext import (  # pyright: ignore[reportMissingImports]
    Application,
    ContextTypes,
    TypeHandler,
    ApplicationHandlerStop,
)

from database.db import SessionLocal
from bot.services import UserService
from bot.services.user_penalty_service import EXEMPT_USER_TELEGRAM_ID

logger = logging.getLogger(__name__)


async def _ban_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверить, не заблокирован ли пользователь"""
    tg_user = update.effective_user
    if not tg_user:
        return

    # Пропускаем проверку для исключенного пользователя
    if tg_user.id == EXEMPT_USER_TELEGRAM_ID:
        return

    db = SessionLocal()
    try:
        db_user = UserService.get_user_by_telegram_id(db, tg_user.id)
        if db_user and db_user.is_banned:
            await context.bot.send_message(
                chat_id=tg_user.id,
                text=(
                    "⛔ Аккаунт заблокирован за повторную отмену поездок в течение 2 месяцев.\n"
                    "Для разблокировки обратитесь к администратору @mrbrennan"
                ),
            )
            logger.warning("Блокируем событие от забаненного пользователя %s", tg_user.id)
            raise ApplicationHandlerStop()
    finally:
        db.close()


def install_ban_guard(application: Application):
    """Добавить middleware в стек обработчиков"""
    application.add_handler(TypeHandler(Update, _ban_guard), group=-1)

