"""
Обработчики для broadcast-уведомлений
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.db import SessionLocal
from bot.models.driver import Driver
from bot.models.user import User
from bot.services.broadcast_service import BroadcastService


async def broadcast_accept_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель принимает broadcast-заказ"""
    query = update.callback_query
    await query.answer()
    
    # Парсим order_id из callback_data
    try:
        _, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка: неверный формат данных")
        return
    
    db = SessionLocal()
    try:
        # Находим водителя
        user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
        if not user:
            await query.edit_message_text("❌ Вы не зарегистрированы в системе")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if not driver:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        # Принимаем заказ
        success, message = await BroadcastService.accept_broadcast_order(
            db, order_id, driver, context.bot, context
        )
        
        if success:
            # Редактируем старое сообщение (убираем кнопку принятия)
            try:
                await query.edit_message_text(f"✅ {message}")
            except Exception as e:
                pass  # Если не удалось отредактировать, не критично
            
            # Новое сообщение с кнопками уже отправлено в BroadcastService.accept_broadcast_order
        else:
            await query.edit_message_text(f"⚠️ {message}")
    
    finally:
        db.close()


async def broadcast_reserve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Занятый водитель резервирует broadcast-заказ"""
    query = update.callback_query
    await query.answer()
    
    # Парсим order_id из callback_data
    try:
        _, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка: неверный формат данных")
        return
    
    db = SessionLocal()
    try:
        # Находим водителя
        user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
        if not user:
            await query.edit_message_text("❌ Вы не зарегистрированы в системе")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if not driver:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        # Резервируем заказ
        success, message = await BroadcastService.reserve_broadcast_order(
            db, order_id, driver, context.bot, context
        )
        
        if success:
            await query.edit_message_text(f"📌 {message}")
        else:
            await query.edit_message_text(f"⚠️ {message}")
    
    finally:
        db.close()


async def confirm_reserve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Клиент подтверждает ожидание зарезервированного водителя"""
    query = update.callback_query
    await query.answer()
    
    # Парсим order_id из callback_data
    try:
        _, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка: неверный формат данных")
        return
    
    db = SessionLocal()
    try:
        success, message = await BroadcastService.confirm_reserve(
            db, order_id, context.bot, context
        )
        
        if success:
            await query.edit_message_text(f"✅ {message}")
        else:
            await query.edit_message_text(f"⚠️ {message}")
    
    finally:
        db.close()


async def decline_reserve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Клиент отклоняет резервацию"""
    query = update.callback_query
    await query.answer()
    
    # Парсим order_id из callback_data
    try:
        _, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка: неверный формат данных")
        return
    
    db = SessionLocal()
    try:
        success, message = await BroadcastService.decline_reserve(db, order_id)
        
        if success:
            await query.edit_message_text(f"⚠️ {message}")
        else:
            await query.edit_message_text(f"❌ {message}")
    
    finally:
        db.close()


def register_broadcast_handlers(application):
    """Регистрирует обработчики broadcast-уведомлений"""
    application.add_handler(
        CallbackQueryHandler(
            broadcast_accept_callback,
            pattern=r"^broadcast_accept:\d+$"
        )
    )
    
    application.add_handler(
        CallbackQueryHandler(
            broadcast_reserve_callback,
            pattern=r"^broadcast_reserve:\d+$"
        )
    )
    
    application.add_handler(
        CallbackQueryHandler(
            confirm_reserve_callback,
            pattern=r"^confirm_reserve:\d+$"
        )
    )
    
    application.add_handler(
        CallbackQueryHandler(
            decline_reserve_callback,
            pattern=r"^decline_reserve:\d+$"
        )
    )
    
    print("✅ Broadcast-обработчики зарегистрированы")

