"""
Обработчики системы очередей для водителей
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from database.db import SessionLocal
from bot.services.user_service import UserService
from bot.services.queue_manager import queue_manager
from bot.services.order_dispatcher import get_dispatcher
from bot.models.user import UserRole
from bot.models.driver import Driver, DriverStatus, DriverZone
from bot.models.order import Order, OrderStatus
from bot.utils.keyboards import Keyboards
from bot.constants import ZONES, PUBLIC_ZONE_LABELS, ZONE_KEY_MAP

logger = logging.getLogger(__name__)


async def driver_go_online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка кнопки '🟢 Я на линии'
    Показывает выбор зоны
    """
    db = SessionLocal()
    
    try:
        logger.info(f"driver_go_online вызван для пользователя {update.effective_user.id}")
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы как водитель.\n"
                "Для регистрации обратитесь к администратору."
            )
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        
        if not driver:
            await update.message.reply_text("❌ Профиль водителя не найден")
            return
        
        if not driver.is_verified:
            await update.message.reply_text(
                "⏳ Ваш профиль еще не верифицирован администратором.\n"
                "Ожидайте подтверждения."
            )
            return
        
        # Проверяем активный заказ (безопасно, без ошибок)
        active_order = None
        try:
            from bot.handlers.driver_trip import get_active_driver_order
            active_order = get_active_driver_order(db, driver)
            if active_order:
                logger.info(f"Найден активный заказ {active_order.id} для водителя {driver.id}")
        except Exception as e:
            logger.error(f"Ошибка при получении активного заказа: {e}", exc_info=True)
            active_order = None
        
        if active_order:
            try:
                # Показываем активный заказ с актуальными кнопками
                order_id = getattr(active_order, 'id', None)
                if not order_id:
                    logger.warning(f"Активный заказ не имеет ID, пропускаем")
                    active_order = None
                else:
                    status = active_order.status.value if hasattr(active_order.status, 'value') else str(active_order.status)
                    
                    # Безопасное получение адресов
                    pickup = getattr(active_order, 'pickup_address', 'не указан') or 'не указан'
                    dropoff = getattr(active_order, 'dropoff_address', 'не указан') or 'не указан'
                    price = getattr(active_order, 'price', 0) or 0
                    
                    keyboard = None
                    message = ""
                    
                    try:
                        if status == OrderStatus.ACCEPTED.value or status == "accepted":
                            keyboard = Keyboards.driver_after_accept(order_id)
                            message = (
                                f"✅ <b>У вас есть активный заказ #{order_id}</b>\n\n"
                                f"📍 Откуда: {pickup}\n"
                                f"📍 Куда: {dropoff}\n"
                                f"💰 Цена: {price:.0f} руб.\n\n"
                                "Едьте к клиенту. Когда подъедете, нажмите 'Подъехал'."
                            )
                        elif status == OrderStatus.ARRIVED.value or status == "arrived":
                            keyboard = Keyboards.driver_arrived(order_id)
                            message = (
                                f"✅ <b>Вы подъехали к заказу #{order_id}</b>\n\n"
                                f"📍 Откуда: {pickup}\n"
                                f"📍 Куда: {dropoff}\n\n"
                                "Ожидайте клиента. Когда клиент будет готов, нажмите 'Поехали'."
                            )
                        elif status == OrderStatus.ONBOARD.value or status == "onboard":
                            keyboard = Keyboards.driver_onboard(order_id)
                            message = (
                                f"🚗 <b>Поездка в процессе (заказ #{order_id})</b>\n\n"
                                f"📍 Откуда: {pickup}\n"
                                f"📍 Куда: {dropoff}\n\n"
                                "По завершении нажмите 'Завершить поездку'."
                            )
                        else:
                            message = f"У вас есть заказ #{order_id} в статусе {status}"
                    except Exception as kb_error:
                        logger.error(f"Ошибка при создании клавиатуры для заказа {order_id}: {kb_error}", exc_info=True)
                        message = f"У вас есть активный заказ #{order_id}"
                    
                    if message:
                        await update.message.reply_text(
                            message,
                            parse_mode='HTML',
                            reply_markup=keyboard
                        )
                        return
            except Exception as e:
                logger.error(f"Ошибка при обработке активного заказа: {e}", exc_info=True)
                # Если ошибка, просто продолжаем - показываем выбор зоны
                active_order = None
        
        # Показываем выбор зоны
        try:
            await update.message.reply_text(
                "🏘 <b>Выберите район, в котором вы находитесь:</b>\n\n"
                "Вы будете получать заказы из этого района в первую очередь.",
                parse_mode='HTML',
                reply_markup=Keyboards.driver_select_district()
            )
            logger.info(f"Показан выбор зоны для водителя {driver.id}")
        except Exception as e:
            logger.error(f"Ошибка при показе выбора зоны: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте еще раз.",
                reply_markup=Keyboards.driver_menu()
            )
        
    except Exception as e:
        logger.error(f"Критическая ошибка в driver_go_online: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                "❌ Произошла ошибка. Попробуйте еще раз.",
                reply_markup=Keyboards.driver_menu()
            )
        except:
            pass
    finally:
        db.close()


async def driver_select_zone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка выбора зоны водителем
    """
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            return
        
        message_text = update.message.text
        
        # Обработка кнопки "Назад"
        if message_text == "🔙 Назад":
            try:
                await update.message.reply_text(
                    "Выберите действие:",
                    reply_markup=Keyboards.driver_menu()
                )
            except Exception as e:
                # Если не можем ответить на сообщение, отправляем новое
                logger.warning(f"Не удалось ответить на сообщение, отправляем новое: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Выберите действие:",
                    reply_markup=Keyboards.driver_menu()
                )
            return
        
        # Проверяем что выбрана валидная зона
        zones_buttons = ["📍 Новое Жуково", "📍 Старое Жуково", "📍 Мысовцево", 
                        "📍 Авдон", "📍 Уптино", "📍 Дёма", "📍 Сергеевка"]
        
        if message_text not in zones_buttons:
            return
        
        # Удаляем эмодзи и получаем название зоны
        selected_zone_label = message_text.replace("📍 ", "")
        
        # Преобразуем в ключ зоны
        zone_key = ZONE_KEY_MAP.get(selected_zone_label)
        
        if not zone_key or zone_key not in ZONES:
            await update.message.reply_text("❌ Неизвестная зона")
            return
        
        # Обновляем статус водителя
        old_status = driver.status
        old_zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
        
        driver.status = DriverStatus.ONLINE
        driver.current_zone = zone_key
        driver.online_since = datetime.utcnow()
        db.commit()
        
        # Обновляем очередь
        if old_status == DriverStatus.ONLINE and old_zone in ZONES:
            # Смена зоны
            queue_manager.switch_zone(driver.id, zone_key, db)
            action = "переведены"
        else:
            # Первый вход онлайн
            queue_manager.add_driver(driver.id, zone_key, db)
            action = "вышли"
        
        # Получаем позицию в очереди
        position = queue_manager.get_queue_position(driver.id)
        
        try:
            await update.message.reply_text(
                f"✅ <b>Вы {action} на линию!</b>\n\n"
                f"🏘 <b>Район:</b> {selected_zone_label}\n"
                f"📊 <b>Ваша позиция в очереди:</b> {position}\n\n"
                f"Ожидайте заказы из вашего района!",
                parse_mode='HTML',
                reply_markup=Keyboards.driver_menu()
            )
        except Exception as e:
            # Если не можем ответить на сообщение, отправляем новое
            logger.warning(f"Не удалось ответить на сообщение, отправляем новое: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"✅ <b>Вы {action} на линию!</b>\n\n"
                    f"🏘 <b>Район:</b> {selected_zone_label}\n"
                    f"📊 <b>Ваша позиция в очереди:</b> {position}\n\n"
                    f"Ожидайте заказы из вашего района!"
                ),
                parse_mode='HTML',
                reply_markup=Keyboards.driver_menu()
            )
        
        logger.info(f"Водитель {driver.id} ({db_user.full_name}) вышел на линию в зоне {zone_key}, позиция {position}")
        
    finally:
        db.close()


async def driver_go_offline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка кнопки '🔴 Я оффлайн'
    """
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            return
        
        # Проверяем что водитель не занят заказом
        if driver.status == DriverStatus.BUSY:
            await update.message.reply_text(
                "⚠️ Вы не можете выйти оффлайн во время выполнения заказа.\n"
                "Сначала завершите текущий заказ."
            )
            return
        
        if driver.status == DriverStatus.PENDING_ACCEPTANCE:
            await update.message.reply_text(
                "⚠️ У вас есть ожидающий ответа заказ.\n"
                "Сначала примите или отклоните его."
            )
            return
        
        # Переводим оффлайн
        old_zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
        driver.status = DriverStatus.OFFLINE
        # current_zone оставляем как есть (история)
        driver.online_since = None
        db.commit()
        
        # Удаляем из очереди
        queue_manager.remove_driver(driver.id)
        
        await update.message.reply_text(
            "🔴 <b>Вы вышли из линии</b>\n\n"
            "Вы больше не будете получать заказы.\n"
            "Чтобы снова выйти на линию, нажмите '🟢 Я на линии'.",
            parse_mode='HTML',
            reply_markup=Keyboards.driver_menu()
        )
        
        logger.info(f"Водитель {driver.id} ({db_user.full_name}) вышел из линии (была зона {old_zone})")
        
    finally:
        db.close()


async def driver_accept_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка принятия заказа водителем
    Callback: order_accept:{order_id}
    """
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        # Парсим callback data
        _, order_id = query.data.split(":")
        order_id = int(order_id)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await query.edit_message_text("❌ Профиль водителя не найден")
            return
        
        # Обрабатываем принятие через диспетчер
        dispatcher = get_dispatcher()
        success = await dispatcher.handle_driver_accept(driver.id, order_id, db)
        
        if success:
            # Получаем заказ для показа клавиатуры
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                # Редактируем старое сообщение
                try:
                    await query.edit_message_text(
                        "✅ <b>Заказ принят!</b>\n\n"
                        "Едьте к клиенту. Когда подъедете, нажмите 'Подъехал'.",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отредактировать сообщение: {e}")
                
                # Отправляем НОВОЕ сообщение с актуальными кнопками
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=(
                        f"📋 <b>Заказ #{order.id}</b>\n\n"
                        f"📍 Откуда: {order.pickup_address}\n"
                        f"📍 Куда: {order.dropoff_address}\n"
                        f"💰 Цена: {order.price:.0f} руб.\n\n"
                        "Едьте к клиенту. Когда подъедете, нажмите 'Подъехал'."
                    ),
                    parse_mode='HTML',
                    reply_markup=Keyboards.driver_after_accept(order_id)
                )
            else:
                await query.edit_message_text(
                    "✅ <b>Заказ принят!</b>\n\n"
                    "Едьте к клиенту. Удачной поездки!",
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                "❌ Не удалось принять заказ.\n"
                "Возможно, он уже принят другим водителем."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при принятии заказа: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка при принятии заказа")
    finally:
        db.close()


async def driver_decline_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка отклонения заказа водителем
    Callback: order_decline:{order_id}
    """
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        # Парсим callback data
        _, order_id = query.data.split(":")
        order_id = int(order_id)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await query.edit_message_text("❌ Профиль водителя не найден")
            return
        
        # Обрабатываем отклонение через диспетчер
        dispatcher = get_dispatcher()
        success = await dispatcher.handle_driver_decline(driver.id, order_id, db)
        
        if success:
            await query.edit_message_text(
                "↩️ Заказ отклонён.\n\n"
                "Вы возвращены в конец очереди своей зоны."
            )
        else:
            await query.edit_message_text(
                "❌ Не удалось отклонить заказ.\n"
                "Возможно, время на ответ уже истекло."
            )
        
    except Exception as e:
        logger.error(f"Ошибка при отклонении заказа: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка при отклонении заказа")
    finally:
        db.close()


async def driver_my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать текущий статус водителя и позицию в очереди
    """
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            return
        
        # Формируем статус
        status_emoji = {
            DriverStatus.OFFLINE: "🔴",
            DriverStatus.ONLINE: "🟢",
            DriverStatus.PENDING_ACCEPTANCE: "⏳",
            DriverStatus.BUSY: "🚗",
        }
        
        status_text = {
            DriverStatus.OFFLINE: "Оффлайн",
            DriverStatus.ONLINE: "На линии",
            DriverStatus.PENDING_ACCEPTANCE: "Ожидает ответа на заказ",
            DriverStatus.BUSY: "Занят заказом",
        }
        
        driver_status = driver.status.value if hasattr(driver.status, 'value') else driver.status
        current_zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
        
        message = (
            f"{status_emoji.get(driver_status, '❓')} <b>Ваш статус:</b> {status_text.get(driver_status, 'Неизвестно')}\n\n"
        )
        
        if driver_status == "online":
            zone_label = PUBLIC_ZONE_LABELS.get(current_zone, current_zone)
            position = queue_manager.get_queue_position(driver.id)
            queue_info = queue_manager.get_queue_info(current_zone)
            
            message += (
                f"🏘 <b>Зона:</b> {zone_label}\n"
                f"📊 <b>Позиция в очереди:</b> {position}\n"
                f"👥 <b>Всего водителей в зоне:</b> {queue_info['count']}\n"
            )
        elif current_zone != "NONE":
            zone_label = PUBLIC_ZONE_LABELS.get(current_zone, current_zone)
            message += f"🏘 <b>Последняя зона:</b> {zone_label}\n"
        
        message += (
            f"\n⭐ <b>Рейтинг:</b> {driver.rating:.1f}\n"
            f"🛣️ <b>Выполнено поездок:</b> {driver.total_rides}"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    finally:
        db.close()

