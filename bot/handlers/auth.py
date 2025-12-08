"""
Обработчики аутентификации по номеру телефона
"""
from __future__ import annotations

import logging
from telegram import Update, KeyboardButton  # pyright: ignore[reportMissingImports]
from telegram.ext import (  # pyright: ignore[reportMissingImports]
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from database.db import SessionLocal
from bot.services import UserService
from bot.utils import Keyboards, Validators

logger = logging.getLogger(__name__)

MANUAL_PHONE_FLAG = "awaiting_manual_phone"


async def ensure_user_authenticated(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user,
) -> bool:
    """Убедиться, что у пользователя подтверждён телефон"""
    if not db_user or db_user.phone_number:
        return True

    logger.info(f"📱 Запрашиваем телефон у пользователя {update.effective_user.id if update.effective_user else 'unknown'}")
    await _prompt_phone(update, context)
    return False


async def _prompt_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = (
        "Чтобы пользоваться ботом, подтвердите номер телефона.\n\n"
        "Нажмите кнопку ниже или введите номер вручную."
    )

    if message:
        await message.reply_text(text, reply_markup=Keyboards.request_phone())
    else:
        chat_id = update.effective_user.id if update.effective_user else None
        if chat_id:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=Keyboards.request_phone())


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать отправку контакта"""
    contact = update.message.contact
    if not contact:
        return

    db = SessionLocal()
    try:
        db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if not db_user:
            return

        if db_user.phone_number:
            await update.message.reply_text("✅ Телефон уже подтверждён.")
            return

        normalized = Validators.normalize_phone(contact.phone_number)
        UserService.update_phone(db, db_user, normalized)
        logger.info("user_registered phone=%s telegram_id=%s", normalized, db_user.telegram_id)

        context.user_data.pop(MANUAL_PHONE_FLAG, None)
        await update.message.reply_text(
            "✅ Номер телефона подтверждён.\n\nДобро пожаловать!",
            reply_markup=Keyboards.main_menu(),
        )
    finally:
        db.close()


async def request_manual_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запросить ручной ввод телефона"""
    context.user_data[MANUAL_PHONE_FLAG] = True
    await update.message.reply_text(
        "✍️ Введите номер телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX.",
        reply_markup=Keyboards.manual_input_with_cancel("❌ Отмена"),
    )


async def handle_manual_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введённого вручную номера телефона"""
    if not context.user_data.get(MANUAL_PHONE_FLAG):
        return

    text = (update.message.text or "").strip()

    if text == "❌ Отмена":
        context.user_data.pop(MANUAL_PHONE_FLAG, None)
        await update.message.reply_text(
            "Отменено. Нажмите «Поделиться номером» или введите номер снова.",
            reply_markup=Keyboards.request_phone(),
        )
        return

    if not Validators.is_valid_phone(text):
        await update.message.reply_text(
            "⚠️ Некорректный номер. Введите формат +7XXXXXXXXXX.",
            reply_markup=Keyboards.manual_input_with_cancel("❌ Отмена"),
        )
        return

    normalized = Validators.normalize_phone(text)

    db = SessionLocal()
    try:
        db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if not db_user:
            return

        if db_user.phone_number:
            context.user_data.pop(MANUAL_PHONE_FLAG, None)
            await update.message.reply_text("✅ Телефон уже подтверждён.", reply_markup=Keyboards.main_menu())
            return

        UserService.update_phone(db, db_user, normalized)
        logger.info("user_registered phone=%s telegram_id=%s", normalized, db_user.telegram_id)
    finally:
        db.close()

    context.user_data.pop(MANUAL_PHONE_FLAG, None)
    await update.message.reply_text(
        "✅ Номер телефона подтверждён.\n\nВыберите действие в меню:",
        reply_markup=Keyboards.main_menu(),
    )


def register_auth_handlers(application: Application):
    """Регистрация хэндлеров аутентификации"""
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact), group=-2)
    application.add_handler(
        MessageHandler(filters.Regex('^✍️ Ввести номер вручную$'), request_manual_phone),
        group=-2,
    )
    manual_text_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_manual_phone,
        block=False,
    )
    application.add_handler(manual_text_handler, group=-2)

