"""
Обработчики этапов поездки для водителя
"""
import asyncio
import logging
from datetime import datetime
from typing import Tuple
from telegram import Update
from telegram.ext import ContextTypes

from database.db import SessionLocal
from bot.services.user_service import UserService
from bot.services.order_service import OrderService
from bot.services.queue_manager import queue_manager
from bot.models.user import UserRole
from bot.models.driver import Driver, DriverStatus
from bot.models.order import Order, OrderStatus
from bot.utils.keyboards import Keyboards

logger = logging.getLogger(__name__)


async def _send_main_menu_to_client(bot, customer_telegram_id: int, order_id: int):
    """
    Отправить главное меню клиенту через 60 сек если он не поставил оценку
    """
    try:
        db = SessionLocal()
        try:
            order = OrderService.get_order_by_id(db, order_id)
            
            # Если клиент уже поставил оценку, не отправляем меню
            if order and order.rating is not None:
                logger.info(f"Клиент {customer_telegram_id} уже поставил оценку для заказа {order_id}, пропускаем автовозврат в меню")
                return
            
            # Отправляем главное меню
            await bot.send_message(
                customer_telegram_id,
                "Главное меню 👇\n\n"
                "Вы можете оценить поездку позже из раздела '🧾 Мои поездки' (доступно в течение 24 часов).",
                reply_markup=Keyboards.main_user()
            )
            logger.info(f"Главное меню автоматически отправлено клиенту {customer_telegram_id} (таймер 60 сек)")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Ошибка при отправке главного меню клиенту {customer_telegram_id}: {e}", exc_info=True)


def validate_driver_order_access(db, driver: Driver, order: Order, allowed_statuses: list) -> Tuple[bool, str]:
    """
    Валидация доступа водителя к заказу
    
    Returns:
        (is_valid, error_message)
    """
    if not order:
        return False, "Заказ не найден"
    
    # Проверяем права доступа
    has_access = (
        order.assigned_driver_id == driver.id or
        order.reserved_driver_id == driver.id or
        order.driver_id == driver.user_id
    )
    
    if not has_access:
        return False, "Заказ уже закрыт или переназначен. Обновите панель задач: /my_orders"
    
    # Проверяем статус
    if order.status not in allowed_statuses:
        status_name = order.status.value if hasattr(order.status, 'value') else str(order.status)
        return False, f"Заказ уже закрыт или переназначен. Обновите панель задач: /my_orders"
    
    return True, ""


def get_active_driver_order(db, driver: Driver):
    """Получить активный заказ водителя"""
    try:
        return db.query(Order).filter(
            Order.assigned_driver_id == driver.id,
            Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.ARRIVED, OrderStatus.ONBOARD])
        ).first()
    except Exception as e:
        logger.error(f"Ошибка при получении активного заказа водителя {driver.id}: {e}", exc_info=True)
        return None


async def driver_arrived_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель подъехал"""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        # Парсим callback data: trip:arrived:order_id
        _, action, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await query.edit_message_text("❌ Профиль водителя не найден")
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        # Валидация
        is_valid, error_msg = validate_driver_order_access(
            db, driver, order, [OrderStatus.ACCEPTED]
        )
        
        if not is_valid:
            await query.edit_message_text(f"⚠️ {error_msg}")
            return
        
        # Получаем контакты клиента
        customer = order.customer
        customer_phone = getattr(customer, 'phone', None)
        customer_username = getattr(customer, 'username', None)
        customer_telegram_id = getattr(customer, 'telegram_id', None)
        
        # Идемпотентность: если уже в статусе ARRIVED, просто возвращаем OK
        if order.status == OrderStatus.ARRIVED:
            await query.edit_message_text(
                "✅ <b>Вы уже подъехали!</b>\n\n"
                "Ожидайте клиента. Когда клиент будет готов, нажмите 'Поехали'.",
                parse_mode='HTML',
                reply_markup=Keyboards.driver_arrived(
                    order_id,
                    customer_phone=customer_phone,
                    customer_username=customer_username,
                    customer_telegram_id=customer_telegram_id
                )
            )
            return
        
        # Обновляем статус заказа
        OrderService.set_arrived(db, order)
        
        # Обновляем клавиатуру
        await query.edit_message_text(
            "✅ <b>Вы подъехали!</b>\n\n"
            "Ожидайте клиента. Когда клиент будет готов, нажмите 'Поехали'.",
            parse_mode='HTML',
            reply_markup=Keyboards.driver_arrived(
                order_id,
                customer_phone=customer_phone,
                customer_username=customer_username,
                customer_telegram_id=customer_telegram_id
            )
        )
        
        # Уведомляем клиента согласно ТЗ
        try:
            message = (
                "🚗 <b>Водитель подъехал к адресу подачи.</b>\n\n"
                "Готовы выходить?"
            )
            
            # Кнопки действий для клиента
            client_keyboard = Keyboards.client_arrived_actions(order_id)
            
            await context.bot.send_message(
                order.customer.telegram_id,
                message,
                parse_mode='HTML',
                reply_markup=client_keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления клиенту: {e}", exc_info=True)
        
        logger.info(f"Водитель {driver.id} подъехал к заказу {order_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке подъезда водителя: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка")
    finally:
        db.close()


async def driver_waiting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель ждет клиента"""
    query = update.callback_query
    await query.answer("Клиент уведомлен, что вы ждете")
    
    db = SessionLocal()
    
    try:
        _, action, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        # Валидация
        is_valid, _ = validate_driver_order_access(
            db, driver, order, [OrderStatus.ACCEPTED, OrderStatus.ARRIVED]
        )
        
        if not is_valid:
            return
        
        # Уведомляем клиента
        try:
            await context.bot.send_message(
                order.customer.telegram_id,
                "⏳ <b>Водитель ждет вас</b>\n\n"
                "Пожалуйста, выходите к месту подачи.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления клиенту: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке ожидания водителя: {e}", exc_info=True)
    finally:
        db.close()


async def driver_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель начал поездку"""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        _, action, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await query.edit_message_text("❌ Профиль водителя не найден")
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        # Валидация
        is_valid, error_msg = validate_driver_order_access(
            db, driver, order, [OrderStatus.ARRIVED]
        )
        
        if not is_valid:
            await query.edit_message_text(f"⚠️ {error_msg}")
            return
        
        # Получаем контакты клиента
        customer = order.customer
        customer_phone = getattr(customer, 'phone', None)
        customer_username = getattr(customer, 'username', None)
        customer_telegram_id = getattr(customer, 'telegram_id', None)
        
        # Идемпотентность: если уже в статусе ONBOARD, просто возвращаем OK
        if order.status == OrderStatus.ONBOARD:
            await query.edit_message_text(
                "✅ <b>Поездка уже началась!</b>\n\n"
                "Удачной дороги! По завершении нажмите 'Завершить поездку'.",
                parse_mode='HTML',
                reply_markup=Keyboards.driver_onboard(
                    order_id,
                    customer_phone=customer_phone,
                    customer_username=customer_username,
                    customer_telegram_id=customer_telegram_id
                )
            )
            return
        
        # Обновляем статус заказа
        OrderService.set_started(db, order)
        
        # Обновляем клавиатуру
        await query.edit_message_text(
            "🚗 <b>Поездка началась!</b>\n\n"
            "Удачной дороги! По завершении нажмите 'Завершить поездку'.",
            parse_mode='HTML',
            reply_markup=Keyboards.driver_onboard(
                order_id,
                customer_phone=customer_phone,
                customer_username=customer_username,
                customer_telegram_id=customer_telegram_id
            )
        )
        
        # Уведомляем клиента
        try:
            await context.bot.send_message(
                order.customer.telegram_id,
                "🚗 <b>Поездка началась!</b>\n\n"
                "Приятной дороги!",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления клиенту: {e}", exc_info=True)
        
        logger.info(f"Водитель {driver.id} начал поездку {order_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при начале поездки: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка")
    finally:
        db.close()


async def driver_finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель завершил поездку"""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        _, action, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await query.edit_message_text("❌ Профиль водителя не найден")
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        # Валидация
        is_valid, error_msg = validate_driver_order_access(
            db, driver, order, [OrderStatus.ONBOARD]
        )
        
        if not is_valid:
            await query.edit_message_text(f"⚠️ {error_msg}")
            return
        
        # Идемпотентность: если уже в статусе FINISHED, просто возвращаем OK
        if order.status == OrderStatus.FINISHED:
            await query.edit_message_text(
                "✅ <b>Поездка уже завершена!</b>\n\n"
                "Спасибо за работу! Чтобы снова выйти на линию, нажмите '🟢 Я на линии'.",
                parse_mode='HTML'
            )
            return
        
        # Обновляем статус заказа
        OrderService.set_finished(db, order)
        
        # ВАЖНО: Водитель выходит из очереди после завершения поездки
        # Он должен вручную нажать "Я на линии", чтобы вернуться в очередь
        queue_manager.remove_driver(driver.id)
        
        # Переводим водителя в OFFLINE статус (как будто он не на линии)
        driver.status = DriverStatus.OFFLINE
        driver.online_since = None
        driver.pending_order_id = None
        driver.pending_until = None
        # current_zone оставляем как есть (история, но водитель не в очереди)
        db.commit()
        
        # Обновляем сообщение водителю
        await query.edit_message_text(
            "✅ <b>Поездка завершена!</b>\n\n"
            "Спасибо за работу!\n\n"
            "Чтобы снова выйти на линию и принимать заказы, нажмите '🟢 Я на линии'.",
            parse_mode='HTML'
        )
        
        # Отправляем водителю главное меню
        try:
            await context.bot.send_message(
                user.id,
                "Главное меню 👇",
                reply_markup=Keyboards.main_driver()
            )
        except Exception as e:
            logger.error(f"Ошибка отправки главного меню водителю: {e}", exc_info=True)
        
        # Уведомляем клиента с запросом оценки
        try:
            logger.info(f"Отправка запроса на оценку клиенту {order.customer.telegram_id} для заказа {order_id}")
            
            rating_keyboard = Keyboards.client_rating(order_id)
            
            await context.bot.send_message(
                order.customer.telegram_id,
                "🏁 <b>Поездка завершена!</b>\n\n"
                "Пожалуйста, оцените поездку:",
                parse_mode='HTML',
                reply_markup=rating_keyboard
            )
            
            logger.info(f"✅ Запрос на оценку успешно отправлен клиенту {order.customer.telegram_id}")
            
            # Запускаем таймер на 60 секунд для автоматического возврата в главное меню
            # Используем asyncio.create_task вместо job_queue, так как JobQueue не установлен
            async def send_main_menu_after_delay():
                await asyncio.sleep(60)
                await _send_main_menu_to_client(context.bot, order.customer.telegram_id, order_id)
            
            asyncio.create_task(send_main_menu_after_delay())
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки запроса на оценку клиенту {order.customer.telegram_id}: {e}", exc_info=True)
        
        logger.info(f"Водитель {driver.id} завершил поездку {order_id}, вышел из очереди (должен вручную вернуться на линию)")
        
    except Exception as e:
        logger.error(f"Ошибка при завершении поездки: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка")
    finally:
        db.close()


async def driver_cancel_trip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель отменяет поездку"""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        _, action, order_id_str = query.data.split(":")
        order_id = int(order_id_str)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await query.edit_message_text("❌ Профиль водителя не найден")
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        # Валидация - можно отменять из любого активного статуса
        is_valid, error_msg = validate_driver_order_access(
            db, driver, order, [OrderStatus.ACCEPTED, OrderStatus.ARRIVED, OrderStatus.ONBOARD]
        )
        
        if not is_valid:
            await query.edit_message_text(f"⚠️ {error_msg}")
            return
        
        # Для межгорода запрашиваем причину
        if order.is_intercity:
            context.user_data['cancel_order_id'] = order_id
            context.user_data['cancel_reason_required'] = True
            await query.edit_message_text(
                "✍️ <b>Укажите причину отмены</b>\n\n"
                "Напишите короткое сообщение (например: 'Техническая неисправность', 'Изменение планов').",
                parse_mode='HTML',
                reply_markup=Keyboards.manual_input_with_cancel()
            )
            return
        
        # Для обычных заказов отменяем сразу
        cancel_reason = None
        await _process_cancel_order(context, order, driver, cancel_reason, db)
        
    except Exception as e:
        logger.error(f"Ошибка при отмене поездки: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка")
    finally:
        db.close()


async def driver_cancel_reason_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода причины отмены для межгорода"""
    # Проверяем, что это именно запрос причины отмены
    if not context.user_data.get('cancel_reason_required'):
        # Не наше событие, пропускаем
        return
    
    order_id = context.user_data.get('cancel_order_id')
    if not order_id:
        context.user_data.pop('cancel_reason_required', None)
        context.user_data.pop('cancel_order_id', None)
        return
    
    text = (update.message.text or "").strip()
    
    if text == "❌ Отмена":
        context.user_data.pop('cancel_reason_required', None)
        context.user_data.pop('cancel_order_id', None)
        await update.message.reply_text("Отмена отмены заказа отменена.")
        return
    
    if len(text) < 3:
        await update.message.reply_text(
            "Сообщение слишком короткое. Опишите причину отмены подробнее.",
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        return
    
    db = SessionLocal()
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            context.user_data.pop('cancel_reason_required', None)
            context.user_data.pop('cancel_order_id', None)
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        order = OrderService.get_order_by_id(db, order_id)
        
        if not driver or not order:
            await update.message.reply_text("Заказ не найден.")
            context.user_data.pop('cancel_reason_required', None)
            context.user_data.pop('cancel_order_id', None)
            return
        
        await _process_cancel_order(context, order, driver, text, db)
        
    finally:
        db.close()
        context.user_data.pop('cancel_reason_required', None)
        context.user_data.pop('cancel_order_id', None)


async def _process_cancel_order(context: ContextTypes.DEFAULT_TYPE, order, driver: Driver, cancel_reason: str, db):
    """Обработать отмену заказа (общая логика)"""
    try:
        # Отменяем заказ со стороны водителя: переводим заказ обратно в поиск
        # 1) Возвращаем водителя в online (штрафуем в конец очереди)
        driver.status = DriverStatus.ONLINE
        driver.online_since = datetime.utcnow()
        driver.pending_order_id = None
        driver.pending_until = None

        # 2) Снимаем назначение с заказа, переводим в NEW и запускаем перераспределение
        from bot.services.order_dispatcher import get_dispatcher
        from bot.services.scheduler import scheduler

        # Отменяем таймер водителя, если был
        try:
            await scheduler.cancel_driver_timeout(driver.id)
        except Exception:
            pass

        order.assigned_driver_id = None
        order.selected_driver_id = None
        order.driver_id = None
        order.status = OrderStatus.NEW
        db.commit()

        # Запускаем перераспределение (по очереди)
        dispatcher = get_dispatcher()
        await dispatcher.create_and_dispatch_order(order.id, db)
        
        # Если есть причина, сохраняем её в комментарий
        if cancel_reason:
            order.customer_comment = f"Отмена водителем: {cancel_reason}"
            db.commit()
        
        # Возвращаем в очередь (с сохранением FIFO порядка)
        zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
        if zone and zone != "NONE":
            queue_manager.add_driver(driver.id, zone, db)
        
        # Уведомляем водителя
        try:
            await context.bot.send_message(
                driver.user.telegram_id,
                "❌ <b>Заказ отменен</b>\n\n"
                "Вы вернулись в очередь.",
                parse_mode='HTML'
            )
            # Отправляем главное меню водителю
            await context.bot.send_message(
                driver.user.telegram_id,
                "Главное меню 👇",
                reply_markup=Keyboards.main_driver()
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления водителю: {e}", exc_info=True)
        
        # Уведомляем клиента
        try:
            message = "❌ <b>Заказ отменен водителем</b>\n\n"
            if cancel_reason:
                message += f"Причина: {cancel_reason}\n\n"
            if order.is_intercity:
                message += "Вы можете выбрать другого водителя из предложений или создать новый заказ."
            else:
                message += "Мы ищем другого водителя..."
            
            await context.bot.send_message(
                order.customer.telegram_id,
                message,
                parse_mode='HTML'
            )
            # Отправляем главное меню клиенту
            await context.bot.send_message(
                order.customer.telegram_id,
                "Главное меню 👇",
                reply_markup=Keyboards.main_user()
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления клиенту: {e}", exc_info=True)
        
        logger.info(f"Водитель {driver.id} отменил заказ {order.id}, причина: {cancel_reason or 'не указана'}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке отмены заказа: {e}", exc_info=True)
