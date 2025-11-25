"""
Межгородской сценарий для клиентов
"""
from __future__ import annotations

import logging
from typing import Tuple

from telegram import Update  # pyright: ignore[reportMissingImports]
from telegram.ext import (  # pyright: ignore[reportMissingImports]
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from database.db import SessionLocal
from bot.models import IntercityOriginZone, Driver, DriverStatus
from bot.services import UserService, OrderService
from bot.handlers.auth import ensure_user_authenticated
from bot.utils import Keyboards

logger = logging.getLogger(__name__)

INTERCITY_ORIGIN, INTERCITY_DESTINATION = range(2)
ORIGIN_LABELS: dict[str, Tuple[IntercityOriginZone, str]] = {
    "Дёма": (IntercityOriginZone.DEMA, "Дёма"),
    "Дема": (IntercityOriginZone.DEMA, "Дёма"),
    "Жуково": (IntercityOriginZone.OLD_ZHUKOVO, "Жуково"),
    "Мысовцево": (IntercityOriginZone.MYSOVTSEVO, "Мысовцево"),
}


async def start_intercity_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт межгородского сценария"""
    message = update.message
    if not message:
        return ConversationHandler.END

    db = SessionLocal()
    try:
        user = update.effective_user
        db_user = UserService.get_or_create_user(db, user)
        if not await ensure_user_authenticated(update, context, db_user):
            return ConversationHandler.END

        active_order = OrderService.get_active_order_by_customer(db, db_user)
        if active_order:
            await message.reply_text(
                "⚠️ У вас уже есть активный заказ.\n"
                "Сначала завершите или отмените его.",
                reply_markup=Keyboards.customer_cancel_order(active_order.id),
            )
            return ConversationHandler.END
    finally:
        db.close()

    context.user_data.pop("intercity_origin_zone", None)
    await message.reply_text(
        "🏁 Выберите, откуда начинается поездка:",
        reply_markup=Keyboards.intercity_origin_selector(),
    )
    return INTERCITY_ORIGIN


async def intercity_origin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = (update.message.text or "").strip()

    if message_text == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=Keyboards.main_menu())
        return ConversationHandler.END

    origin_info = ORIGIN_LABELS.get(message_text)
    if not origin_info:
        await update.message.reply_text(
            "Пожалуйста, выберите вариант из списка.",
            reply_markup=Keyboards.intercity_origin_selector(),
        )
        return INTERCITY_ORIGIN

    origin_zone, origin_label = origin_info
    context.user_data["intercity_origin_zone"] = origin_zone
    context.user_data["intercity_origin_label"] = origin_label

    await update.message.reply_text(
        "✍️ Введите населённый пункт или адрес назначения.",
        reply_markup=Keyboards.manual_input_with_cancel(),
    )
    return INTERCITY_DESTINATION


async def intercity_destination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=Keyboards.main_menu())
        return ConversationHandler.END

    if len(text) < 3:
        await update.message.reply_text(
            "Адрес слишком короткий. Укажите населённый пункт или улицу полностью.",
            reply_markup=Keyboards.manual_input_with_cancel(),
        )
        return INTERCITY_DESTINATION

    origin_zone = context.user_data.get("intercity_origin_zone")
    if not origin_zone:
        await update.message.reply_text(
            "Не удалось определить точку отправления. Начните заново.",
            reply_markup=Keyboards.main_menu(),
        )
        return ConversationHandler.END

    db = SessionLocal()
    try:
        user = update.effective_user
        db_user = UserService.get_or_create_user(db, user)
        if not await ensure_user_authenticated(update, context, db_user):
            return ConversationHandler.END

        order = OrderService.create_intercity_order(db, db_user, origin_zone, text)
        logger.info('intercity: created from=%s to="%s"', origin_zone.value, text)
    finally:
        db.close()

    origin_label = context.user_data.get("intercity_origin_label", "—")
    context.user_data.pop("intercity_origin_zone", None)
    context.user_data.pop("intercity_origin_label", None)

    await update.message.reply_text(
        "🛣 <b>Межгородской заказ создан</b>\n\n"
        f"Откуда: {origin_label}\n"
        f"Куда: {text}\n\n"
        "Мы отправили запрос всем онлайн-водителям.\n"
        "Как только появятся предложения, вы получите уведомления.",
        parse_mode="HTML",
        reply_markup=Keyboards.customer_cancel_order(order.id),
    )

    await broadcast_intercity_request(order.id, origin_label, text, context)
    return ConversationHandler.END


async def cancel_intercity_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=Keyboards.main_menu())
    context.user_data.pop("intercity_origin_zone", None)
    context.user_data.pop("intercity_origin_label", None)
    return ConversationHandler.END


async def broadcast_intercity_request(order_id: int, origin_label: str, destination: str, context):
    """Рассылка межгородского запроса всем онлайн-водителям"""
    db = SessionLocal()
    try:
        drivers = (
            db.query(Driver)
            .filter(
                Driver.status == DriverStatus.ONLINE,
                Driver.is_verified == True,  # noqa: E712
            )
            .all()
        )
        count = 0
        for driver in drivers:
            try:
                await context.bot.send_message(
                    chat_id=driver.user.telegram_id,
                    text=(
                        f"🛣 <b>Новый межгород #{order_id}</b>\n\n"
                        f"Откуда: {origin_label}\n"
                        f"Куда: {destination}\n\n"
                        "Нажмите «Откликнуться» и отправьте клиенту условия (цена/время/детали)."
                    ),
                    parse_mode="HTML",
                    reply_markup=Keyboards.intercity_driver_actions(order_id),
                )
                count += 1
            except Exception as exc:  # pragma: no cover - уведомление может не доставиться
                # Если водитель не активировал бота - это нормально, не пугаем владельца
                if "bot can't initiate conversation" in str(exc):
                    logger.warning(
                        "⚠️ Водитель %s (ID=%s) не активировал бота. "
                        "Попросите его нажать /start",
                        driver.user.full_name if driver.user else "неизвестен",
                        driver.id
                    )
                else:
                    logger.error("Не удалось уведомить водителя %s: %s", driver.id, exc)
        logger.info("intercity: broadcast sent to %s drivers", count)
    finally:
        db.close()


async def handle_intercity_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор водителя клиентом"""
    query = update.callback_query
    await query.answer()

    try:
        _, order_id, driver_id = query.data.split(":")
        order_id = int(order_id)
        driver_id = int(driver_id)
    except ValueError:
        await query.answer("Некорректные данные", show_alert=True)
        return

    driver_chat_id = None
    db = SessionLocal()
    try:
        order = OrderService.get_order_by_id(db, order_id)
        if not order or not order.is_intercity:
            await query.answer("Заказ не найден", show_alert=True)
            return

        if order.customer.telegram_id != query.from_user.id:
            await query.answer("Это не ваш заказ", show_alert=True)
            return

        if order.selected_driver_id:
            await query.answer("Вы уже выбрали водителя", show_alert=True)
            return

        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            await query.answer("Водитель недоступен", show_alert=True)
            return

        OrderService.set_selected_driver(db, order, driver)
        logger.info("intercity: user selected driver %s for order %s", driver_id, order_id)
        driver_chat_id = driver.user.telegram_id
    finally:
        db.close()

    await query.edit_message_text(
        "✅ Вы выбрали водителя. Ожидаем подтверждения поездки.",
        parse_mode="HTML",
    )

    if driver_chat_id:
        await context.bot.send_message(
            chat_id=driver_chat_id,
            text=(
                f"✅ Клиент выбрал вас для межгорода #{order_id}.\n"
                "Подтвердите поездку или отмените предложение."
            ),
            reply_markup=Keyboards.intercity_driver_confirm(order_id),
        )


def build_intercity_conversation() -> ConversationHandler:
    """Создать ConversationHandler для межгорода"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🚀 Заказать межгород$'), start_intercity_order)],
        states={
            INTERCITY_ORIGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, intercity_origin_handler)
            ],
            INTERCITY_DESTINATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, intercity_destination_handler)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), cancel_intercity_order)],
        allow_reentry=True,
    )


def build_intercity_select_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(handle_intercity_select, pattern=r"^intercity_select:\d+:\d+$")

