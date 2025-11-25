"""
Обработчики межгородских заявок для водителей
"""
from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update, Bot  # pyright: ignore[reportMissingImports]
from telegram.ext import ContextTypes  # pyright: ignore[reportMissingImports]

from database.db import SessionLocal
from bot.services import UserService, OrderService
from bot.models import UserRole, Driver, DriverStatus, OrderStatus, IntercityOriginZone
from bot.utils import Keyboards
from bot.services.queue_manager import queue_manager

logger = logging.getLogger(__name__)

REPLY_STATE_KEY = "intercity_reply_order_id"


async def intercity_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель нажал «Откликнуться»"""
    query = update.callback_query
    await query.answer()

    try:
        _, order_id = query.data.split(":")
        order_id = int(order_id)
    except ValueError:
        await query.answer("Некорректные данные", show_alert=True)
        return

    customer_chat_id = None
    driver_car = None
    driver_plate = None
    driver_telegram = None
    db = SessionLocal()
    try:
        user = UserService.get_user_by_telegram_id(db, query.from_user.id)
        if not user or user.role != UserRole.DRIVER:
            await query.answer("Доступ запрещён", show_alert=True)
            return

        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if not driver or not driver.is_verified:
            await query.answer("Профиль водителя не найден или не подтверждён", show_alert=True)
            return

        order = OrderService.get_order_by_id(db, order_id)
        if not order or not order.is_intercity:
            await query.answer("Заказ недоступен", show_alert=True)
            return

        if order.selected_driver_id:
            await query.answer("Клиент уже выбрал водителя", show_alert=True)
            return
    finally:
        db.close()

    context.user_data[REPLY_STATE_KEY] = order_id
    await query.message.reply_text(
        "✍️ Напишите короткое сообщение клиенту (цена, время, условия).\n"
        "При необходимости отправьте номер телефона текстом.",
        reply_markup=Keyboards.manual_input_with_cancel(),
    )


async def intercity_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Зафиксировать текстовое предложение водителя"""
    # Проверяем, что это именно отклик на межгород
    order_id = context.user_data.get(REPLY_STATE_KEY)
    if not order_id:
        # Не наше событие, пропускаем
        return

    text = (update.message.text or "").strip()
    if text == "❌ Отмена":
        context.user_data.pop(REPLY_STATE_KEY, None)
        await update.message.reply_text("Отклик отменён.")
        return

    if len(text) < 3:
        await update.message.reply_text(
            "Сообщение слишком короткое. Опишите условия поездки подробнее.",
            reply_markup=Keyboards.manual_input_with_cancel(),
        )
        return

    db = SessionLocal()
    try:
        user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if not user or user.role != UserRole.DRIVER:
            context.user_data.pop(REPLY_STATE_KEY, None)
            return

        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        order = OrderService.get_order_by_id(db, order_id)

        if not driver or not order or not order.is_intercity:
            await update.message.reply_text("Заказ недоступен.")
            context.user_data.pop(REPLY_STATE_KEY, None)
            return

        if order.selected_driver_id and order.selected_driver_id != driver.id:
            await update.message.reply_text("Клиент уже выбрал другого водителя.")
            context.user_data.pop(REPLY_STATE_KEY, None)
            return

        message = (
            f"🚗 <b>Отклик на межгород #{order.id}</b>\n\n"
            f"Водитель: {driver.user.full_name}\n"
            f"Авто: {driver.car_model} ({driver.car_number})\n"
            f"Сообщение: {text}"
        )

        await context.bot.send_message(
            chat_id=order.customer.telegram_id,
            text=message,
            parse_mode="HTML",
            reply_markup=Keyboards.intercity_proposal_actions(
                order.id, driver.id, driver.user.telegram_id
            ),
        )
        logger.info("intercity: driver %s replied", driver.id)
    finally:
        db.close()

    context.user_data.pop(REPLY_STATE_KEY, None)
    await update.message.reply_text("✅ Предложение отправлено клиенту.")


async def intercity_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель подтверждает поездку после выбора клиента"""
    query = update.callback_query
    await query.answer()

    try:
        _, order_id = query.data.split(":")
        order_id = int(order_id)
    except ValueError:
        await query.answer("Некорректные данные", show_alert=True)
        return

    db = SessionLocal()
    try:
        user = UserService.get_user_by_telegram_id(db, query.from_user.id)
        if not user or user.role != UserRole.DRIVER:
            await query.answer("Доступ запрещён", show_alert=True)
            return

        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        order = OrderService.get_order_by_id(db, order_id)

        if not driver or not order or not order.is_intercity:
            await query.answer("Заказ недоступен", show_alert=True)
            return

        if order.selected_driver_id != driver.id:
            await query.answer("Клиент выбрал другого водителя", show_alert=True)
            return

        OrderService.confirm_intercity_order(db, order, driver)
        driver.status = DriverStatus.BUSY
        driver.pending_order_id = None
        driver.pending_until = None
        db.commit()
        queue_manager.remove_driver(driver.id)
        logger.info("intercity: driver %s confirmed order %s", driver.id, order_id)
        
        # Сохраняем данные для использования после закрытия БД
        customer = order.customer
        driver_user = driver.user
    finally:
        db.close()

    await query.edit_message_text("✅ Поездка подтверждена. Удачной дороги!")

    # Уведомляем клиента с контактами водителя
    await notify_client_order_assigned(context.bot, order_id, order, customer, driver, driver_user)
    
    # Отправляем панель водителю с контактами клиента
    await send_driver_panel(context.bot, order_id, order, customer, driver)


async def intercity_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель отменяет подтверждение"""
    query = update.callback_query
    await query.answer()

    try:
        _, order_id = query.data.split(":")
        order_id = int(order_id)
    except ValueError:
        await query.answer("Некорректные данные", show_alert=True)
        return

    customer_chat_id = None
    db = SessionLocal()
    try:
        user = UserService.get_user_by_telegram_id(db, query.from_user.id)
        if not user or user.role != UserRole.DRIVER:
            await query.answer("Доступ запрещён", show_alert=True)
            return

        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        order = OrderService.get_order_by_id(db, order_id)

        if not driver or not order or not order.is_intercity:
            await query.answer("Заказ недоступен", show_alert=True)
            return

        if order.selected_driver_id != driver.id:
            await query.answer("Вы уже не выбраны клиентом", show_alert=True)
            return

        order.selected_driver_id = None
        order.driver_id = None
        order.accepted_at = None
        order.status = OrderStatus.NEW
        db.commit()
        logger.info("intercity: driver %s cancelled selection for order %s", driver.id, order_id)
        customer_chat_id = order.customer.telegram_id
    finally:
        db.close()

    await query.edit_message_text("❌ Предложение отменено.")

    if customer_chat_id:
        await context.bot.send_message(
            chat_id=customer_chat_id,
            text="⚠️ Водитель отменил подтверждение. Выберите другого водителя из предложений.",
        )


async def notify_client_order_assigned(bot: Bot, order_id: int, order, customer, driver: Driver, driver_user):
    """Уведомить клиента о назначении водителя для межгорода"""
    try:
        # Формируем информацию о машине
        car_info = f"{driver.car_model or 'машина'}"
        if driver.car_number:
            car_info += f" ({driver.car_number})"
        
        # Получаем контактные данные водителя
        username = getattr(driver_user, 'username', None)
        telegram_id = getattr(driver_user, 'telegram_id', None)
        phone = getattr(driver_user, 'phone', None)
        
        message = (
            "✅ <b>Водитель подтвердил поездку</b>\n\n"
            f"🚗 <b>{car_info}</b>\n"
            f"👤 <b>Водитель:</b> {driver_user.full_name}\n"
            f"⭐ <b>Рейтинг:</b> {driver.rating:.1f}\n\n"
            "<b>Связь:</b>\n"
        )
        
        # Добавляем телефон в текст (если есть)
        if phone:
            message += f"📞 Телефон: <code>{phone}</code>\n"
        
        # Добавляем Telegram
        if username:
            message += f"💬 Telegram: @{username}\n"
        elif telegram_id:
            message += f"💬 Telegram: ID {telegram_id}\n"
        
        # Создаем клавиатуру с контактами
        contact_keyboard = Keyboards.contact_driver(
            username=username,
            telegram_id=telegram_id,
            phone=phone
        )
        
        await bot.send_message(
            customer.telegram_id,
            message,
            parse_mode="HTML",
            reply_markup=contact_keyboard
        )
        
        logger.info(f"✅ Уведомление клиенту отправлено для межгорода {order_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления клиенту для межгорода {order_id}: {e}", exc_info=True)


async def send_driver_panel(bot: Bot, order_id: int, order, customer, driver: Driver):
    """Отправить панель водителю с кнопками стадий и контактами клиента"""
    try:
        # Получаем контактные данные клиента
        customer_phone = getattr(customer, 'phone', None)
        customer_username = getattr(customer, 'username', None)
        customer_telegram_id = getattr(customer, 'telegram_id', None)
        
        # Формируем информацию о маршруте
        origin_map = {
            IntercityOriginZone.DEMA: "Дёма",
            IntercityOriginZone.OLD_ZHUKOVO: "Жуково",
            IntercityOriginZone.MYSOVTSEVO: "Мысовцево",
        }
        from_zone_text = origin_map.get(order.from_zone, "—")
        to_text = order.to_text or order.dropoff_address or "—"
        
        # Формируем сообщение
        message = (
            f"🛣 <b>Межгород #{order_id}</b>\n\n"
            f"📍 <b>Откуда:</b> {from_zone_text}\n"
            f"📍 <b>Куда:</b> {to_text}\n\n"
            f"<b>Клиент:</b> {customer.full_name}\n"
        )
        
        # Добавляем контакты клиента в текст
        if customer_phone:
            message += f"📞 <b>Телефон:</b> {customer_phone}\n"
        if customer_username:
            message += f"💬 <b>Telegram:</b> @{customer_username}\n"
        elif customer_telegram_id:
            message += f"💬 <b>Telegram:</b> ID {customer_telegram_id}\n"
        
        # Создаем клавиатуру с кнопками стадий и контактами
        keyboard = Keyboards.driver_after_accept(
            order_id=order_id,
            customer_phone=customer_phone,
            customer_username=customer_username,
            customer_telegram_id=customer_telegram_id
        )
        
        await bot.send_message(
            driver.user.telegram_id,
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Панель водителя отправлена для межгорода {order_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки панели водителю для межгорода {order_id}: {e}", exc_info=True)

