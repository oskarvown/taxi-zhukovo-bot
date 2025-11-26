"""
Обработчики команд для водителей
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.ext import ContextTypes
from database.db import SessionLocal
from bot.services import UserService, OrderService
from bot.utils import Keyboards
from bot.models import UserRole, Driver, OrderStatus, Order
from datetime import datetime
from sqlalchemy import func

logger = logging.getLogger(__name__)

from bot.handlers.driver_intercity import (
    intercity_reply_callback,
    intercity_reply_message,
    intercity_confirm_callback,
    intercity_cancel_callback,
    REPLY_STATE_KEY,
)


async def driver_status_online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перевести статус водителя в онлайн - выбор района"""
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await update.message.reply_text(
                "Вы не зарегистрированы как водитель.\n"
                "Для регистрации обратитесь к администратору."
            )
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        
        if not driver:
            await update.message.reply_text("Профиль водителя не найден")
            return
        
        if not driver.is_verified:
            await update.message.reply_text(
                "Ваш профиль еще не верифицирован администратором.\n"
                "Ожидайте подтверждения."
            )
            return
        
        # Предлагаем выбрать район
        await update.message.reply_text(
            "🏘 <b>Выберите район, в котором вы находитесь:</b>\n\n"
            "Это поможет получать заказы из вашего района в приоритете!",
            parse_mode='HTML',
            reply_markup=Keyboards.driver_select_district()
        )
        
        # Отправляем список доступных заказов
        pending_orders = OrderService.get_pending_orders(db)
        if pending_orders:
            for order in pending_orders:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🚖 <b>Новый заказ!</b>\n\n{order.display_info}",
                    parse_mode='HTML',
                    reply_markup=Keyboards.driver_order_action(order.id)
                )
    finally:
        db.close()


async def driver_select_district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района водителем"""
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            return
        
        # Проверяем, что выбран валидный район
        districts = ["📍 Новое Жуково", "📍 Старое Жуково", "📍 Мысовцево", "📍 Авдон", "📍 Уптино", "📍 Дёма", "📍 Сергеевка"]
        
        if update.message.text == "🔙 Назад":
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=Keyboards.driver_menu()
            )
            return
        
        if update.message.text not in districts:
            return
        
        # Удаляем эмодзи из названия района
        selected_district = update.message.text.replace("📍 ", "")
        
        # Обновляем район водителя
        driver.current_district = selected_district
        driver.district_updated_at = datetime.utcnow()
        driver.is_online = True
        db.commit()
        
        await update.message.reply_text(
            f"🟢 <b>Отлично!</b>\n\n"
            f"Вы в сети в районе: <b>{selected_district}</b>\n\n"
            f"Ожидайте заказы из вашего района! 🚖",
            parse_mode='HTML',
            reply_markup=Keyboards.driver_menu()
        )
        
        # Отправляем список доступных заказов
        pending_orders = OrderService.get_pending_orders(db)
        if pending_orders:
            for order in pending_orders:
                order_info = (
                    f"🚖 <b>Доступный заказ #{order.id}</b>\n\n"
                    f"{order.display_info}"
                )
                await update.message.reply_text(
                    order_info,
                    parse_mode='HTML',
                    reply_markup=Keyboards.driver_order_action(order.id)
                )
    finally:
        db.close()


async def driver_status_offline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перевести статус водителя в оффлайн"""
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await update.message.reply_text("Вы не зарегистрированы как водитель")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        
        if not driver:
            await update.message.reply_text("Профиль водителя не найден")
            return
        
        # Проверяем наличие активных заказов
        active_order = OrderService.get_active_order_by_driver(db, db_user)
        if active_order:
            await update.message.reply_text(
                "У вас есть активный заказ. Завершите его перед выходом из сети."
            )
            return
        
        driver.is_online = False
        db.commit()
        
        await update.message.reply_text(
            "🔴 Вы оффлайн. Заказы не будут приходить.",
            reply_markup=Keyboards.driver_menu()
        )
    finally:
        db.close()


async def accept_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Водитель принимает заказ"""
    query = update.callback_query
    await query.answer()
    
    print(f"🔔 accept_order_callback вызван! Data: {query.data}")
    
    try:
        action, order_id = query.data.split(':')
        order_id = int(order_id)
        print(f"   Action: {action}, Order ID: {order_id}")
    except Exception as e:
        print(f"❌ Ошибка парсинга callback data: {e}")
        await query.answer("Ошибка обработки запроса", show_alert=True)
        return
    
    db = SessionLocal()
    try:
        user = query.from_user
        print(f"   Пользователь: {user.id} (@{user.username})")
        
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            print(f"❌ Пользователь не найден в БД")
            await query.edit_message_text("❌ Вы не зарегистрированы в системе")
            return
        
        print(f"   Роль пользователя: {db_user.role}")
        
        if db_user.role != UserRole.DRIVER:
            print(f"❌ Пользователь не водитель")
            await query.edit_message_text("❌ Вы не зарегистрированы как водитель")
            return
        
        order = OrderService.get_order_by_id(db, order_id)
        
        if not order:
            print(f"❌ Заказ #{order_id} не найден")
            await query.edit_message_text("❌ Заказ не найден")
            return
        
        print(f"   Статус заказа: {order.status}")
        
        if order.status != OrderStatus.PENDING:
            print(f"❌ Заказ уже не в статусе pending")
            await query.edit_message_text(f"❌ Заказ уже принят другим водителем или отменен")
            return
        
        if action == "accept_order":
            print(f"✓ Водитель принимает заказ #{order_id}")
            
            # Проверяем, нет ли у водителя других активных заказов
            active_order = OrderService.get_active_order_by_driver(db, db_user)
            if active_order:
                print(f"⚠️ У водителя уже есть активный заказ #{active_order.id}")
                await query.answer("У вас уже есть активный заказ!", show_alert=True)
                return
            
            # Принимаем заказ
            OrderService.accept_order(db, order, db_user)
            print(f"✅ Заказ #{order_id} принят водителем {db_user.full_name}")
            
            driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
            
            await query.edit_message_text(
                f"✅ <b>Вы приняли заказ #{order.id}</b>\n\n"
                f"{order.display_info}\n\n"
                f"Свяжитесь с клиентом: @{order.customer.username or 'клиент'}",
                parse_mode='HTML',
                reply_markup=Keyboards.order_status_actions(order.id, "accepted")
            )
            
            # Уведомляем клиента
            try:
                await context.bot.send_message(
                    chat_id=order.customer.telegram_id,
                    text=(
                        f"✅ <b>Водитель найден!</b>\n\n"
                        f"{driver.display_info}\n\n"
                        f"Свяжитесь с водителем: @{db_user.username or 'водитель'}"
                    ),
                    parse_mode='HTML'
                )
                print(f"✅ Клиент уведомлен")
            except Exception as e:
                print(f"❌ Ошибка уведомления клиента: {e}")
        
        elif action == "decline_order":
            print(f"⚠️ Водитель отклонил заказ #{order_id}")
            await query.edit_message_text("❌ Вы отклонили заказ")
    except Exception as e:
        print(f"❌ ОШИБКА в accept_order_callback: {e}")
        import traceback
        traceback.print_exc()
        await query.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)
    finally:
        db.close()


async def start_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать выполнение заказа"""
    query = update.callback_query
    await query.answer()
    
    _, order_id = query.data.split(':')
    order_id = int(order_id)
    
    db = SessionLocal()
    try:
        order = OrderService.get_order_by_id(db, order_id)
        
        if not order or order.status != OrderStatus.ACCEPTED:
            await query.answer("Заказ недоступен", show_alert=True)
            return
        
        OrderService.start_order(db, order)
        
        await query.edit_message_text(
            f"🚗 <b>Поездка началась</b>\n\n{order.display_info}",
            parse_mode='HTML',
            reply_markup=Keyboards.order_status_actions(order.id, "in_progress")
        )
        
        # Уведомляем клиента
        await context.bot.send_message(
            chat_id=order.customer.telegram_id,
            text="🚗 Поездка началась!",
            parse_mode='HTML'
        )
    finally:
        db.close()


async def complete_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершить заказ"""
    query = update.callback_query
    await query.answer()
    
    _, order_id = query.data.split(':')
    order_id = int(order_id)
    
    db = SessionLocal()
    try:
        order = OrderService.get_order_by_id(db, order_id)
        
        if not order or order.status != OrderStatus.IN_PROGRESS:
            await query.answer("Заказ недоступен", show_alert=True)
            return
        
        OrderService.complete_order(db, order)
        
        # Обновляем статистику водителя
        driver = db.query(Driver).filter(Driver.user_id == order.driver_id).first()
        if driver:
            driver.total_rides += 1
            db.commit()
        
        await query.edit_message_text(
            f"✅ <b>Поездка завершена!</b>\n\n{order.display_info}",
            parse_mode='HTML'
        )
        
        # Просим клиента оценить поездку
        await context.bot.send_message(
            chat_id=order.customer.telegram_id,
            text="✅ Поездка завершена!\n\nОцените водителя:",
            reply_markup=Keyboards.rate_driver(order.id)
        )
    finally:
        db.close()


async def rate_driver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оценка водителя клиентом"""
    query = update.callback_query
    await query.answer()
    
    _, order_id, rating = query.data.split(':')
    order_id = int(order_id)
    rating = int(rating)
    
    db = SessionLocal()
    try:
        order = OrderService.get_order_by_id(db, order_id)
        
        if not order:
            await query.answer("Заказ не найден", show_alert=True)
            return
        
        OrderService.rate_order(db, order, rating)
        
        await query.edit_message_text(
            f"⭐ Спасибо за оценку! Вы поставили {rating}/5 звезд.",
            parse_mode='HTML'
        )
        
        # Уведомляем водителя
        if order.driver:
            await context.bot.send_message(
                chat_id=order.driver.telegram_id,
                text=f"⭐ Клиент оценил вашу поездку на {rating}/5"
            )
    finally:
        db.close()


async def driver_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы водителя"""
    print(f"📋 driver_orders вызван! Пользователь: {update.effective_user.id}")
    
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            print(f"❌ Пользователь не водитель")
            await update.message.reply_text("Вы не зарегистрированы как водитель")
            return
        
        print(f"✓ Водитель: {db_user.full_name} (ID: {db_user.id})")
        
        driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver:
            await update.message.reply_text("❌ Профиль водителя не найден")
            return
        
        # Используем новую функцию для получения активного заказа
        from bot.handlers.driver_trip import get_active_driver_order
        active_order = get_active_driver_order(db, driver)
        
        if active_order:
            print(f"✓ Есть активный заказ #{active_order.id}")
            # Показываем активный заказ с актуальными кнопками
            status = active_order.status.value if hasattr(active_order.status, 'value') else active_order.status
            
            # Получаем контакты клиента
            customer = active_order.customer
            customer_phone = getattr(customer, 'phone', None)
            customer_username = getattr(customer, 'username', None)
            customer_telegram_id = getattr(customer, 'telegram_id', None)
            
            if status == OrderStatus.ACCEPTED.value:
                keyboard = Keyboards.driver_after_accept(
                    active_order.id,
                    customer_phone=customer_phone,
                    customer_username=customer_username,
                    customer_telegram_id=customer_telegram_id
                )
                message = (
                    f"✅ <b>Активный заказ #{active_order.id}</b>\n\n"
                    f"📍 Откуда: {active_order.pickup_address}\n"
                    f"📍 Куда: {active_order.dropoff_address}\n"
                    f"💰 Цена: {active_order.price:.0f} руб.\n\n"
                    "Едьте к клиенту. Когда подъедете, нажмите 'Подъехал'."
                )
            elif status == OrderStatus.ARRIVED.value:
                keyboard = Keyboards.driver_arrived(
                    active_order.id,
                    customer_phone=customer_phone,
                    customer_username=customer_username,
                    customer_telegram_id=customer_telegram_id
                )
                message = (
                    f"✅ <b>Вы подъехали к заказу #{active_order.id}</b>\n\n"
                    f"📍 Откуда: {active_order.pickup_address}\n"
                    f"📍 Куда: {active_order.dropoff_address}\n\n"
                    "Ожидайте клиента. Когда клиент будет готов, нажмите 'Поехали'."
                )
            elif status == OrderStatus.ONBOARD.value:
                keyboard = Keyboards.driver_onboard(
                    active_order.id,
                    customer_phone=customer_phone,
                    customer_username=customer_username,
                    customer_telegram_id=customer_telegram_id
                )
                message = (
                    f"🚗 <b>Поездка в процессе (заказ #{active_order.id})</b>\n\n"
                    f"📍 Откуда: {active_order.pickup_address}\n"
                    f"📍 Куда: {active_order.dropoff_address}\n\n"
                    "По завершении нажмите 'Завершить поездку'."
                )
            else:
                keyboard = None
                message = f"У вас есть заказ #{active_order.id} в статусе {status}"
            
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            return
        else:
            print(f"⚠️ Нет активного заказа")
        
        # История поездок
        print(f"🔍 Ищем историю заказов для driver_id={db_user.id}...")
        history = OrderService.get_driver_history(db, db_user)
        print(f"✓ Найдено завершенных заказов: {len(history)}")
        
        # Дополнительная диагностика
        all_driver_orders = db.query(Order).filter(Order.driver_id == db_user.id).all()
        print(f"   Всего заказов с driver_id={db_user.id}: {len(all_driver_orders)}")
        
        completed_orders = db.query(Order).filter(
            Order.driver_id == db_user.id,
            Order.status == OrderStatus.COMPLETED
        ).all()
        print(f"   Из них завершенных: {len(completed_orders)}")
        
        if not history:
            await update.message.reply_text(
                "📋 <b>Мои заказы</b>\n\n"
                "У вас пока нет завершенных поездок.\n\n"
                "🚖 Нажмите \"🟢 Я на линии\", чтобы начать принимать заказы!",
                parse_mode='HTML'
            )
        else:
            print(f"✓ Отправляем историю ({len(history)} заказов)")
            history_text = "📋 <b>История ваших поездок</b>\n\n"
            for i, order in enumerate(history, 1):
                history_text += f"<b>Поездка #{i}</b>\n"
                history_text += f"🆔 Заказ #{order.id}\n"
                history_text += f"📍 Откуда: {order.pickup_address}\n"
                history_text += f"📍 Куда: {order.dropoff_address}\n"
                history_text += f"💰 Цена: {order.price:.0f} руб.\n"
                if order.rating:
                    history_text += f"⭐ Оценка клиента: {order.rating}/5\n"
                history_text += f"📅 Дата: {order.completed_at.strftime('%d.%m.%Y %H:%M')}\n"
                history_text += "➖➖➖➖➖➖➖➖➖\n\n"
            
            await update.message.reply_text(history_text, parse_mode='HTML')
    except Exception as e:
        print(f"❌ ОШИБКА в driver_orders: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def driver_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику водителя с использованием новых полей модели Driver"""
    db = SessionLocal()

    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)

        if not db_user or db_user.role != UserRole.DRIVER:
            await update.message.reply_text("Вы не зарегистрированы как водитель")
            return

        driver_profile = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver_profile:
            await update.message.reply_text("Профиль водителя не найден")
            return

        # Используем новые поля из модели Driver
        total_completed = driver_profile.completed_trips_count or 0
        avg_rating = driver_profile.rating_avg or 0.0
        rating_count = driver_profile.rating_count or 0

        rating_display = f"{avg_rating:.2f} ⭐" if rating_count > 0 else "Нет оценок"

        stats_text = (
            "📊 <b>Моя статистика</b>\n\n"
            f"🚗 <b>Авто:</b> {driver_profile.car_model} ({driver_profile.car_number})\n"
            f"⭐ <b>Средний рейтинг:</b> {rating_display} ({rating_count} оценок)\n"
            f"🛣️ <b>Завершенных поездок:</b> {total_completed}\n"
        )

        # Последние оценки (используем assigned_driver_id)
        rated_orders = db.query(Order).filter(
            Order.assigned_driver_id == driver_profile.id,
            Order.rating.isnot(None)
        ).order_by(Order.finished_at.desc()).limit(3).all()

        if rated_orders:
            stats_text += "\n📝 <b>Последние оценки:</b>\n"
            for order in rated_orders:
                completed_at = (order.finished_at or order.completed_at).strftime('%d.%m.%Y %H:%M') if (order.finished_at or order.completed_at) else "—"
                stats_text += (
                    f"• Заказ #{order.id}: {order.rating}/5 ⭐ "
                    f"({completed_at})\n"
                )
        else:
            stats_text += "\n📝 Клиенты еще не оставили оценок.\n"

        # Последние поездки (используем новый метод)
        recent_orders = OrderService.get_driver_order_history(db, driver_profile.id, limit=3)
        if recent_orders:
            stats_text += "\n📋 <b>Последние поездки:</b>\n"
            for order in recent_orders:
                completed_at = (order.finished_at or order.completed_at).strftime('%d.%m.%Y %H:%M') if (order.finished_at or order.completed_at) else "—"
                price_str = f"{order.price:.0f} ₽" if order.price and order.price > 0 else "—"
                stats_text += (
                    f"• #{order.id}: {order.pickup_address[:20]}{'...' if len(order.pickup_address) > 20 else ''} → "
                    f"{order.dropoff_address[:20]}{'...' if len(order.dropoff_address) > 20 else ''} "
                    f"({price_str}, {completed_at})\n"
                )

        await update.message.reply_text(stats_text, parse_mode='HTML')
    finally:
        db.close()


async def driver_trip_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды '🧾 Мои поездки' для водителя"""
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.role != UserRole.DRIVER:
            await update.message.reply_text("Вы не зарегистрированы как водитель")
            return
        
        driver_profile = db.query(Driver).filter(Driver.user_id == db_user.id).first()
        if not driver_profile:
            await update.message.reply_text("Профиль водителя не найден")
            return
        
        # Получаем offset из callback data (для пагинации)
        offset = 0
        if update.callback_query:
            try:
                _, offset_str = update.callback_query.data.split(":")
                offset = int(offset_str)
            except:
                offset = 0
        
        # Получаем историю поездок
        limit = 10
        orders = OrderService.get_driver_order_history(db, driver_profile.id, limit=limit, offset=offset)
        
        if not orders and offset == 0:
            await update.message.reply_text(
                "📭 <b>История поездок пуста</b>\n\n"
                "У вас пока нет завершённых или отменённых заказов.",
                parse_mode='HTML'
            )
            return
        
        # Формируем сообщение с историей
        from datetime import datetime
        
        message = "🧾 <b>Мои поездки</b>\n\n"
        
        for order in orders:
            status_emoji = {
                "finished": "✅",
                "cancelled": "❌",
                "completed": "✅"
            }.get(order.status.value if hasattr(order.status, 'value') else order.status, "📋")
            
            date_str = (order.finished_at or order.completed_at).strftime('%d.%m.%Y %H:%M') if (order.finished_at or order.completed_at) else order.created_at.strftime('%d.%m.%Y %H:%M')
            
            # Получаем информацию о клиенте
            client_name = order.customer.full_name if order.customer else "—"
            client_phone = getattr(order.customer, 'phone_number', None) if order.customer else None
            
            # Оценка
            rating_str = ""
            if order.rating:
                rating_str = f"\n⭐ Оценка: {'⭐' * order.rating}"
            
            message += (
                f"{status_emoji} <b>№{order.id}</b> • {date_str}\n"
                f"📍 {order.pickup_address[:30]}{'...' if len(order.pickup_address) > 30 else ''}\n"
                f"🎯 {order.dropoff_address[:30]}{'...' if len(order.dropoff_address) > 30 else ''}\n"
                f"👤 {client_name[:25]}{'...' if len(client_name) > 25 else ''}"
            )
            
            if client_phone:
                message += f"\n📞 {client_phone}"
            
            if order.price and order.price > 0:
                message += f"\n💰 {order.price:.0f} ₽"
            
            message += f"\n📊 Статус: {status_emoji} {order.status.value if hasattr(order.status, 'value') else order.status}"
            
            if rating_str:
                message += rating_str
            
            message += "\n\n"
        
        # Добавляем кнопку "Показать ещё" если есть ещё заказы
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = []
        
        if len(orders) == limit:
            keyboard.append([InlineKeyboardButton("📄 Показать ещё", callback_data=f"driver_history:{offset + limit}")])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории поездок водителя: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при загрузке истории")
    finally:
        db.close()


def register_driver_handlers(application: Application):
    """Регистрация обработчиков для водителей"""
    
    # Импортируем новые хэндлеры системы очередей
    from .driver_queue import (
        driver_go_online,
        driver_go_offline,
        driver_select_zone_handler,
        driver_accept_order,
        driver_decline_order,
        driver_my_status
    )
    
    # Статус водителя (новая система очередей)
    application.add_handler(MessageHandler(filters.Regex('^🟢 Я на линии$'), driver_go_online))
    application.add_handler(MessageHandler(filters.Regex('^🔴 Я оффлайн$'), driver_go_offline))
    
    # Выбор зоны водителем (новая система)
    application.add_handler(MessageHandler(
        filters.Regex('^📍 (Новое Жуково|Старое Жуково|Мысовцево|Авдон|Уптино|Дёма|Сергеевка)$'),
        driver_select_zone_handler
    ))
    application.add_handler(MessageHandler(filters.Regex('^🔙 Назад$'), driver_select_zone_handler))
    
    # Заказы водителя
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои заказы$'), driver_orders))
    application.add_handler(CommandHandler('my_orders', driver_orders))  # Команда для обновления панели
    application.add_handler(MessageHandler(filters.Regex('^📊 Статистика$'), driver_statistics))
    application.add_handler(MessageHandler(filters.Regex('^🧾 Мои поездки$'), driver_trip_history_handler))
    
    # Обработчик пагинации истории водителя
    application.add_handler(CallbackQueryHandler(driver_trip_history_handler, pattern='^driver_history:\d+$'))
    
    # Callback handlers (новая система очередей)
    application.add_handler(CallbackQueryHandler(driver_accept_order, pattern='^order_accept:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_decline_order, pattern='^order_decline:\d+$'))
    
    # Хэндлеры этапов поездки (новый формат trip:action:order_id)
    from .driver_trip import (
        driver_arrived_callback,
        driver_waiting_callback,
        driver_start_callback,
        driver_finish_callback,
        driver_cancel_trip_callback,
        driver_cancel_reason_handler,
        get_active_driver_order
    )
    application.add_handler(CallbackQueryHandler(driver_arrived_callback, pattern='^trip:arrived:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_waiting_callback, pattern='^trip:waiting:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_start_callback, pattern='^trip:start:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_finish_callback, pattern='^trip:finish:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_cancel_trip_callback, pattern='^trip:cancel:\d+$'))
    
    # Старые форматы для обратной совместимости (можно удалить позже)
    application.add_handler(CallbackQueryHandler(driver_arrived_callback, pattern='^driver_arrived:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_waiting_callback, pattern='^driver_waiting:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_start_callback, pattern='^driver_start:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_finish_callback, pattern='^driver_finish:\d+$'))
    application.add_handler(CallbackQueryHandler(driver_cancel_trip_callback, pattern='^driver_cancel:\d+$'))
    
    # Старые callback handlers (для обратной совместимости)
    application.add_handler(CallbackQueryHandler(accept_order_callback, pattern='^(accept_order|decline_order):\d+$'))
    application.add_handler(CallbackQueryHandler(start_order_callback, pattern='^start_order:\d+$'))
    application.add_handler(CallbackQueryHandler(complete_order_callback, pattern='^complete_order:\d+$'))
    application.add_handler(CallbackQueryHandler(rate_driver_callback, pattern='^rate:\d+:\d+$'))

    # Межгород
    application.add_handler(CallbackQueryHandler(intercity_reply_callback, pattern='^intercity_reply:\d+$'))
    application.add_handler(CallbackQueryHandler(intercity_confirm_callback, pattern='^intercity_confirm:\d+$'))
    application.add_handler(CallbackQueryHandler(intercity_cancel_callback, pattern='^intercity_cancel:\d+$'))
    
    # Обработчики межгорода и отмены (общий обработчик текстовых сообщений)
    async def combined_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Комбинированный обработчик для intercity_reply и cancel_reason"""
        # Сначала проверяем отмену (более приоритетно)
        if context.user_data.get('cancel_reason_required'):
            await driver_cancel_reason_handler(update, context)
            return
        
        # Затем проверяем межгород
        if context.user_data.get(REPLY_STATE_KEY):
            await intercity_reply_message(update, context)
            return
    
    text_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        combined_text_handler,
        block=False,
    )
    application.add_handler(text_handler)

