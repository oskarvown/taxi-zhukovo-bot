"""
Обработчики команд для пользователей
"""
from typing import Optional
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton  # pyright: ignore[reportMissingImports]
from telegram.ext import (  # pyright: ignore[reportMissingImports]
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from telegram.ext import ContextTypes  # pyright: ignore[reportMissingImports]
from database.db import SessionLocal
from bot.services import UserService, OrderService, PricingService, UserPenaltyService
from bot.services.broadcast_service import BroadcastService
from bot.utils import Keyboards
from bot.models import OrderStatus, Driver, UserRole
from bot.config import settings
import asyncio
from datetime import datetime, timedelta
from bot.handlers.auth import ensure_user_authenticated
from bot.handlers.user_intercity import build_intercity_conversation, build_intercity_select_handler

logger = logging.getLogger(__name__)

print("✅ Импорты user.py загружены успешно")

# Состояния разговора
SELECT_DISTRICT, PICKUP_ADDRESS, SELECT_DESTINATION, DROPOFF_ADDRESS, CONFIRM_ORDER = range(5)


async def notify_drivers_by_district(context: ContextTypes.DEFAULT_TYPE, order, district: str):
    """
    Отправить уведомления водителям из конкретного района
    
    Args:
        context: Контекст бота
        order: Объект заказа
        district: Район для поиска водителей
        
    Returns:
        int: Количество успешно уведомленных водителей
    """
    db = SessionLocal()
    notified_count = 0
    
    try:
        # Получаем онлайн водителей из указанного района, отсортированных по времени отметки (FIFO)
        online_drivers = db.query(Driver).filter(
            Driver.is_online == True,
            Driver.is_verified == True,
            Driver.current_district == district
        ).order_by(Driver.district_updated_at.asc()).all()  # FIFO - кто первый отметился
        
        if not online_drivers:
            print(f"⚠️ Нет онлайн водителей в районе '{district}' для заказа #{order.id}")
            return 0
        
        print(f"📢 Отправка уведомлений {len(online_drivers)} водителям из района '{district}' о заказе #{order.id}")
        
        # Отправляем уведомление каждому водителю
        notification_text = (
            "🚖 <b>НОВЫЙ ЗАКАЗ В ВАШЕМ РАЙОНЕ!</b>\n\n"
            f"{order.display_info}\n\n"
            "⏰ Успейте принять заказ первым!"
        )
        
        for driver in online_drivers:
            try:
                await context.bot.send_message(
                    chat_id=driver.user.telegram_id,
                    text=notification_text,
                    parse_mode='HTML',
                    reply_markup=Keyboards.driver_order_action(order.id)
                )
                notified_count += 1
                print(f"✅ Уведомлен водитель ID: {driver.user.telegram_id} ({driver.user.full_name})")
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления водителю {driver.user.telegram_id}: {e}")
        
        print(f"✅ Успешно уведомлено {notified_count} из {len(online_drivers)} водителей в районе '{district}'")
        return notified_count
        
    finally:
        db.close()


async def notify_online_drivers(context: ContextTypes.DEFAULT_TYPE, order):
    """
    Отправить уведомления онлайн водителям о новом заказе с приоритетом по районам
    
    Логика:
    1. Сначала уведомляем водителей из района заказа (FIFO)
    2. Если через 60 секунд заказ не принят, уведомляем водителей из "Новое Жуково" (FIFO)
    
    Args:
        context: Контекст бота
        order: Объект заказа
        
    Returns:
        int: Количество успешно уведомленных водителей
    """
    pickup_district = order.pickup_district
    
    # Сначала уведомляем водителей из района заказа
    if pickup_district:
        print(f"🎯 Приоритетный поиск в районе: {pickup_district}")
        notified_count = await notify_drivers_by_district(context, order, pickup_district)
        
        if notified_count > 0:
            # Ждем 60 секунд и проверяем, принят ли заказ
            await asyncio.sleep(60)
            
            # Проверяем статус заказа
            db = SessionLocal()
            try:
                fresh_order = OrderService.get_order_by_id(db, order.id)
                if fresh_order is not None:
                    order_status = str(fresh_order.status.value if hasattr(fresh_order.status, 'value') else fresh_order.status)
                    if order_status == OrderStatus.PENDING.value:
                        # Заказ все еще ожидает, ищем в Новом Жуково
                        print(f"⏰ Прошла 1 минута, заказ #{order.id} не принят. Поиск в Новом Жуково...")
                        
                        if pickup_district != "Новое Жуково":
                            additional_notified = await notify_drivers_by_district(context, order, "Новое Жуково")
                            notified_count += additional_notified
                    else:
                        print(f"✅ Заказ #{order.id} уже принят водителем")
            finally:
                db.close()
        else:
            # Если в районе заказа нет водителей, сразу ищем в Новом Жуково
            print(f"⚠️ В районе '{pickup_district}' нет водителей, ищем в Новом Жуково...")
            notified_count = await notify_drivers_by_district(context, order, "Новое Жуково")
    else:
        # Если район не указан, уведомляем всех
        print(f"⚠️ Район не указан, уведомляем всех онлайн водителей")
        db = SessionLocal()
        try:
            online_drivers = db.query(Driver).filter(
                Driver.is_online == True,
                Driver.is_verified == True
            ).all()
            
            notification_text = (
                "🚖 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
                f"{order.display_info}\n\n"
                "⏰ Успейте принять заказ первым!"
            )
            
            notified_count = 0
            for driver in online_drivers:
                try:
                    await context.bot.send_message(
                        chat_id=driver.user.telegram_id,
                        text=notification_text,
                        parse_mode='HTML',
                        reply_markup=Keyboards.driver_order_action(order.id)
                    )
                    notified_count += 1
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
        finally:
            db.close()
    
    return notified_count


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        # Создаем или получаем пользователя
        db_user = UserService.get_or_create_user(db, user)
        if not await ensure_user_authenticated(update, context, db_user):
            return
        
        # Проверяем роль пользователя и показываем соответствующее меню
        if db_user.role == UserRole.DRIVER:
            # Меню для водителя
            driver = db.query(Driver).filter(Driver.user_id == db_user.id).first()
            
            if driver and driver.is_verified:
                trips_count = driver.completed_trips_count or driver.total_rides or 0
                rating_display = f"{driver.rating_avg:.1f} ⭐" if driver.rating_count > 0 else "Новый"
                
                welcome_text = (
                    f"👋 Привет, {user.first_name}!\n"
                    "🚗 <b>Меню водителя «Такси Жуково+»</b>\n\n"
                    f"🚕 Ваш автомобиль: {driver.car_model} ({driver.car_number})\n"
                    f"⭐ Рейтинг: {rating_display}\n"
                    f"🛣️ Поездок выполнено: {trips_count}\n\n"
                    "👇 Выберите действие:"
                )
                keyboard = Keyboards.main_driver()
            else:
                welcome_text = (
                    f"👋 Привет, {user.first_name}!\n\n"
                    "⏳ Ваш профиль водителя ожидает верификации администратором.\n\n"
                    "📞 Пожалуйста, свяжитесь с администратором для активации."
                )
                keyboard = Keyboards.main_user()
        elif db_user.role == UserRole.ADMIN:
            # Меню для администратора
            welcome_text = (
                f"👋 Привет, {user.first_name}!\n"
                "👑 <b>Панель администратора «Такси Жуково+»</b>\n\n"
                "Вы можете управлять водителями, просматривать статистику и заказы.\n\n"
                "👇 Используйте команды:\n"
                "/drivers - Список водителей\n"
                "/stats - Статистика системы\n"
                "/orders - Активные заказы"
            )
            keyboard = Keyboards.main_menu()
        else:
            # Меню для обычного пользователя (клиента)
            welcome_text = (
                f"👋 Привет, {user.first_name}!\n"
                "Добро пожаловать в бот 🚖 <b>«Такси Жуково+»</b>\n\n"
                "📋 Актуальные правила:\n"
                "• Регистрация по номеру телефона обязательна.\n"
                "• Заказы оформляются текстовым вводом адресов (геолокация отключена).\n"
                "• Отмены спустя 5 минут после подтверждения водителем ведут к предупреждению.\n\n"
                "🚗 Бот найдёт ближайшего водителя по фиксированным маршрутам.\n"
                "👇 Выберите, что хотите сделать:"
            )
            keyboard = Keyboards.main_user()
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    finally:
        db.close()


async def switch_role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение роли между клиентом и водителем (для администраторов)"""
    message = update.message or update.effective_message

    if not message:
        return

    user = update.effective_user
    admin_ids = set(settings.admin_ids)

    if admin_ids and user.id not in admin_ids:
        await message.reply_text("❌ Эта команда доступна только администраторам.")
        return

    db = SessionLocal()
    show_updated_menu = False
    response_text = None

    try:
        db_user = UserService.get_or_create_user(db, user)
        current_role = db_user.role

        # Определяем желаемую роль
        args = [arg.lower() for arg in context.args] if getattr(context, "args", None) else []
        target_role: Optional[UserRole] = None

        if args:
            arg = args[0]
            if arg in {"driver", "водитель"}:
                target_role = UserRole.DRIVER
            elif arg in {"user", "customer", "клиент"}:
                target_role = UserRole.CUSTOMER
            elif arg in {"toggle", "сменить", "переключить"}:
                target_role = UserRole.DRIVER if current_role != UserRole.DRIVER else UserRole.CUSTOMER
        else:
            # Без аргументов просто переключаем роль
            target_role = UserRole.DRIVER if current_role != UserRole.DRIVER else UserRole.CUSTOMER

        if target_role is None:
            await message.reply_text(
                "ℹ️ Использование: /switch_role <driver|user|toggle>\n"
                "Без аргументов команда просто переключает текущую роль."
            )
            return

        if target_role == current_role:
            response_text = (
                "ℹ️ Роль уже установлена.\n"
                f"Текущий режим: <b>{'Водитель' if current_role == UserRole.DRIVER else 'Клиент'}</b>."
            )
            return

        driver_profile = db.query(Driver).filter(Driver.user_id == db_user.id).first()

        if target_role == UserRole.DRIVER and not driver_profile:
            await message.reply_text(
                "❌ У вас ещё нет профиля водителя.\n"
                "Добавьте данные через скрипт add_driver.py или обратитесь к администратору."
            )
            return

        if target_role == UserRole.CUSTOMER and driver_profile:
            driver_profile.is_online = False  # type: ignore[assignment]

        db_user.role = target_role  # type: ignore[assignment]
        db.commit()

        show_updated_menu = True

        if target_role == UserRole.DRIVER:
            if driver_profile and not driver_profile.is_verified:
                response_text = (
                    "✅ Роль переключена на <b>Водителя</b>.\n"
                    "⏳ Профиль ещё не верифицирован администратором."
                )
            else:
                response_text = "✅ Роль переключена на <b>Водителя</b>."
        else:
            response_text = "✅ Роль переключена на <b>Клиента</b>."
    finally:
        db.close()

    if response_text:
        await message.reply_text(response_text, parse_mode='HTML')

    if show_updated_menu:
        await start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    print(f"ℹ️ help_command вызван! Пользователь: {update.effective_user.id}")
    help_text = (
        "📖 <b>Помощь по боту такси</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/order - Заказать такси\n"
        "/history - История заказов\n"
        "/cancel - Отменить текущее действие\n\n"
        "<b>Как заказать такси:</b>\n"
        "1️⃣ Нажмите 'Заказать такси' или /order\n"
        "2️⃣ Выберите район и введите адрес отправления вручную\n"
        "3️⃣ Выберите район назначения и введите адрес вручную\n"
        "4️⃣ Подтвердите заказ\n"
        "5️⃣ Ожидайте уведомления о принятии заказа водителем\n\n"
        "🚗 <b>Преимущества:</b>\n"
        "• Автоматический поиск ближайшего водителя\n"
        "• Расчет стоимости до начала поездки\n"
        "• Отслеживание статуса заказа\n"
        "• Маршрут в Яндекс.Картах\n\n"
        "<b>📞 Поддержка:</b>\n"
        "По всем вопросам нажмите кнопку \"Связаться\""
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания заказа"""
    print(f"🚖 order_start вызван! Пользователь: {update.effective_user.id}")
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_or_create_user(db, user)
        if not await ensure_user_authenticated(update, context, db_user):
            return ConversationHandler.END
        print(f"✓ Пользователь найден/создан: {db_user.full_name}")

        # Сбрасываем временные данные заказа
        for key in [
            'pickup_district',
            'pickup_zone_id',
            'pickup_address',
            'pickup_lat',
            'pickup_lon',
            'destination_zone_id',
            'destination_zone_name',
            'calculated_price',
            'dropoff_address',
            'dropoff_lat',
            'dropoff_lon',
            'pickup_submenu',
            'pickup_mode'
        ]:
            context.user_data.pop(key, None)
        
        # Проверяем, нет ли активного заказа
        active_order = OrderService.get_active_order_by_customer(db, db_user)
        if active_order:
            print(f"⚠️ У пользователя есть активный заказ #{active_order.id}")
            await update.message.reply_text(
                f"⚠️ <b>У вас уже есть активный заказ</b>\n\n"
                f"{active_order.display_info}\n\n"
                "Пожалуйста, завершите или отмените текущий заказ перед созданием нового.\n\n"
                "👇 Вы можете отменить этот заказ прямо сейчас:",
                parse_mode='HTML',
                reply_markup=Keyboards.customer_cancel_order(active_order.id)
            )
            return ConversationHandler.END
        
        print("✓ Нет активных заказов, показываем выбор района")
        await update.message.reply_text(
            "🏘 <b>Выберите район, где вы находитесь:</b>\n\n"
            "Это поможет быстрее найти ближайшего водителя!",
            parse_mode='HTML',
            reply_markup=Keyboards.select_district()
        )
        
        print("✓ Сообщение отправлено, переход в SELECT_DISTRICT")
        return SELECT_DISTRICT
    except Exception as e:
        print(f"❌ ОШИБКА в order_start: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ Произошла ошибка при создании заказа. Попробуйте ещё раз или обратитесь к администратору."
        )
        return ConversationHandler.END
    finally:
        db.close()


async def district_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района"""
    text = update.message.text or ""

    if text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Заказ отменен.\n\n"
            "Если передумаете — просто нажмите \"Заказать такси\" снова! 🚖",
            reply_markup=Keyboards.main_menu()
        )
        return ConversationHandler.END

    submenu = context.user_data.get('pickup_submenu')

    def reset_to_main_keyboard():
        context.user_data.pop('pickup_submenu', None)
        return Keyboards.select_district()

    if submenu == 'ufa':
        context.user_data['pickup_mode'] = None
        if text == "🔙 Назад":
            await update.message.reply_text(
                "🏘 <b>Выберите район, где вы находитесь:</b>",
                parse_mode='HTML',
                reply_markup=reset_to_main_keyboard()
            )
            return SELECT_DISTRICT

        ufa_options = {
            "Уфа-Центр": "Уфа-Центр",
            "Телецентр": "Телецентр",
            "Сипайлово": "Сипайлово",
            "Черниковка": "Черниковка",
            "Инорс": "Инорс",
            "Зелёная роща": "Зелёная роща",
            "Проспект Октября": "Проспект Октября"
        }

        if text not in ufa_options:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите район Уфы из списка ниже:",
                reply_markup=Keyboards.select_ufa_pickup()
            )
            return SELECT_DISTRICT

        selected_district = ufa_options[text]
        zone_id = PricingService.get_zone_id_by_name(selected_district)
        context.user_data.pop('pickup_submenu', None)
        if not zone_id:
            await update.message.reply_text(
                "❌ Не удалось определить выбранный район. Попробуйте выбрать заново.",
                reply_markup=Keyboards.select_ufa_pickup()
            )
            return SELECT_DISTRICT

        context.user_data['pickup_district'] = selected_district
        context.user_data['pickup_zone_id'] = zone_id
        context.user_data['is_from_other_destination'] = False  # Явно сбрасываем для Уфы
        
        # Запрашиваем адрес
        await update.message.reply_text(
            f"✅ <b>Район: {selected_district}</b>\n\n"
            "📍 Теперь укажите <b>точный адрес отправления</b> текстом.\n\n"
            "Например: «ул. Центральная, 15» или «Жуково, 3-я линия 4».",
            parse_mode='HTML',
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        return PICKUP_ADDRESS
    elif submenu == 'other_destinations':
        context.user_data['pickup_mode'] = 'other'
        if text == "🔙 Назад":
            await update.message.reply_text(
                "🏘 <b>Выберите район, где вы находитесь:</b>",
                parse_mode='HTML',
                reply_markup=reset_to_main_keyboard()
            )
            return SELECT_DISTRICT

        other_options = {
            "Дмитриевка": "Дмитриевка",
            "Михайловка": "Михайловка",
            "Миловский Парк": "Миловский Парк",
            "Миловка": "Миловка",
            "Николаевка": "Николаевка",
            "Юматово": "Юматово",
            "Алкино": "Алкино",
            "Кафе Отдых": "Кафе Отдых",
            "Сергеевка": "Сергеевка",
            "Чесноковка": "Чесноковка",
            "Иглино": "Иглино",
            "Шакша": "Шакша",
            "Акбердино": "Акбердино",
            "Нагаево": "Нагаево",
            "Чишмы": "Чишмы"
        }

        if text not in other_options:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите направление из списка ниже:",
                reply_markup=Keyboards.select_other_destinations()
            )
            return SELECT_DISTRICT

        selected_destination = other_options[text]
        zone_id = PricingService.get_zone_id_by_name(selected_destination)
        context.user_data.pop('pickup_submenu', None)
        if not zone_id:
            print(f"⚠️ Не удалось определить zone_id для направления '{selected_destination}'")
            await update.message.reply_text(
                "❌ Не удалось определить выбранное направление. Попробуйте выбрать заново.",
                reply_markup=Keyboards.select_other_destinations()
            )
            return SELECT_DISTRICT

        context.user_data['pickup_district'] = selected_destination
        context.user_data['pickup_zone_id'] = zone_id
        context.user_data['is_from_other_destination'] = True  # Флаг для ограничения выбора назначения
        
        # Запрашиваем адрес
        await update.message.reply_text(
            f"✅ <b>Район: {selected_destination}</b>\n\n"
            "📍 Теперь укажите <b>точный адрес отправления</b> текстом.\n\n"
            "Например: «ул. Центральная, 15».",
            parse_mode='HTML',
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        return PICKUP_ADDRESS
    elif submenu == 'airport':
        context.user_data['pickup_mode'] = 'airport'
        if text == "🔙 Назад":
            await update.message.reply_text(
                "🏘 <b>Выберите район, где вы находитесь:</b>",
                parse_mode='HTML',
                reply_markup=reset_to_main_keyboard()
            )
            return SELECT_DISTRICT

        airport_options = {
            "Терминал 1": "Аэропорт, Терминал 1",
            "Терминал 2": "Аэропорт, Терминал 2"
        }

        if text not in airport_options:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите терминал из списка ниже:",
                reply_markup=Keyboards.select_airport_terminal()
            )
            return SELECT_DISTRICT

        selected_terminal = airport_options[text]
        zone_id = PricingService.get_zone_id_by_name("Аэропорт")
        context.user_data.pop('pickup_submenu', None)
        if not zone_id:
            print(f"⚠️ Не удалось определить zone_id для аэропорта")
            await update.message.reply_text(
                "❌ Не удалось определить выбранный аэропорт. Попробуйте выбрать заново.",
                reply_markup=Keyboards.select_airport_terminal()
            )
            return SELECT_DISTRICT

        context.user_data['pickup_district'] = "Аэропорт"
        context.user_data['pickup_zone_id'] = zone_id
        context.user_data['pickup_address'] = selected_terminal  # Сохраняем терминал как адрес
        context.user_data['pickup_mode'] = 'airport'
        context.user_data['is_from_other_destination'] = False  # Явно сбрасываем для аэропорта
        
        # Сразу переходим к выбору назначения (без запроса адреса)
        await update.message.reply_text(
            f"✅ <b>Отправление: {selected_terminal}</b>\n\n"
            "🎯 Теперь выберите район назначения.",
            parse_mode='HTML',
            reply_markup=Keyboards.select_destination_zone()
        )
        
        return SELECT_DESTINATION
    elif submenu == 'po_zhukovo':
        context.user_data['pickup_mode'] = 'po_zhukovo'
        if text == "🔙 Назад":
            await update.message.reply_text(
                "🏘 <b>Выберите район, где вы находитесь:</b>",
                parse_mode='HTML',
                reply_markup=reset_to_main_keyboard()
            )
            return SELECT_DISTRICT

        po_zhukovo_options = {
            "Новое Жуково": "Новое Жуково",
            "Старое Жуково": "Старое Жуково"
        }

        if text not in po_zhukovo_options:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите вариант из списка ниже:",
                reply_markup=Keyboards.select_po_zhukovo_pickup()
            )
            return SELECT_DISTRICT

        selected_district = po_zhukovo_options[text]
        zone_id = PricingService.get_zone_id_by_name(selected_district)
        context.user_data.pop('pickup_submenu', None)
        if not zone_id:
            print(f"⚠️ Не удалось определить zone_id для района '{selected_district}'")
            await update.message.reply_text(
                "❌ Не удалось определить выбранный район. Попробуйте выбрать заново.",
                reply_markup=Keyboards.select_po_zhukovo_pickup()
            )
            return SELECT_DISTRICT

        context.user_data['pickup_district'] = selected_district
        context.user_data['pickup_zone_id'] = zone_id
        context.user_data['is_from_other_destination'] = False  # Явно сбрасываем для По Жуково
        
        # Запрашиваем адрес
        await update.message.reply_text(
            f"✅ <b>Район: {selected_district}</b>\n\n"
            "📍 Теперь укажите <b>точный адрес отправления</b> текстом.\n\n"
            "Например: «ул. Центральная, 15» или «Жуково, 3-я линия 4».",
            parse_mode='HTML',
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        return PICKUP_ADDRESS
    else:
        if text == "Уфа":
            context.user_data['pickup_submenu'] = 'ufa'
            context.user_data['pickup_mode'] = None
            await update.message.reply_text(
                "🏙 <b>Выберите район Уфы, где вы находитесь:</b>",
                parse_mode='HTML',
                reply_markup=Keyboards.select_ufa_pickup()
            )
            return SELECT_DISTRICT

        if text == "По Жуково":
            context.user_data['pickup_submenu'] = 'po_zhukovo'
            context.user_data['pickup_mode'] = 'po_zhukovo'
            await update.message.reply_text(
                "🚖 <b>Выберите часть Жуково, где вы находитесь:</b>",
                parse_mode='HTML',
                reply_markup=Keyboards.select_po_zhukovo_pickup()
            )
            return SELECT_DISTRICT

        if text == "По Дёме":
            context.user_data['pickup_mode'] = 'po_dema'
            context.user_data['pickup_district'] = "Дёма"
            zone_id = PricingService.get_zone_id_by_name("Дёма")
            if not zone_id:
                await update.message.reply_text(
                    "❌ Не удалось определить район Дёма. Попробуйте выбрать заново.",
                    reply_markup=Keyboards.select_district()
                )
                return SELECT_DISTRICT
            
            context.user_data['pickup_zone_id'] = zone_id
            context.user_data['is_from_other_destination'] = False
            
            await update.message.reply_text(
                "✅ <b>Район: Дёма (по району)</b>\n\n"
                "📍 Укажите <b>точный адрес отправления</b> текстом.\n\n"
                "Например: «ул. Ленина, 25» или «Дёма, ул. Мира 10».",
                parse_mode='HTML',
                reply_markup=Keyboards.manual_input_with_cancel()
            )
            return PICKUP_ADDRESS

        if text == "По Авдону":
            context.user_data['pickup_mode'] = 'po_avdon'
            context.user_data['pickup_district'] = "Авдон"
            zone_id = PricingService.get_zone_id_by_name("Авдон")
            if not zone_id:
                await update.message.reply_text(
                    "❌ Не удалось определить район Авдон. Попробуйте выбрать заново.",
                    reply_markup=Keyboards.select_district()
                )
                return SELECT_DISTRICT
            
            context.user_data['pickup_zone_id'] = zone_id
            context.user_data['is_from_other_destination'] = False
            
            await update.message.reply_text(
                "✅ <b>Район: Авдон (по району)</b>\n\n"
                "📍 Укажите <b>точный адрес отправления</b> текстом.\n\n"
                "Например: «ул. Центральная, 5» или «Авдон, ул. Школьная 12».",
                parse_mode='HTML',
                reply_markup=Keyboards.manual_input_with_cancel()
            )
            return PICKUP_ADDRESS

        if text == "По Сергеевке":
            context.user_data['pickup_mode'] = 'po_sergeevka'
            context.user_data['pickup_district'] = "Сергеевка"
            zone_id = PricingService.get_zone_id_by_name("Сергеевка")
            if not zone_id:
                await update.message.reply_text(
                    "❌ Не удалось определить район Сергеевка. Попробуйте выбрать заново.",
                    reply_markup=Keyboards.select_district()
                )
                return SELECT_DISTRICT
            
            context.user_data['pickup_zone_id'] = zone_id
            context.user_data['is_from_other_destination'] = False
            
            await update.message.reply_text(
                "✅ <b>Район: Сергеевка (по району)</b>\n\n"
                "📍 Укажите <b>точный адрес отправления</b> текстом.\n\n"
                "Например: «ул. Ленина, 10» или «Сергеевка, ул. Советская 25».",
                parse_mode='HTML',
                reply_markup=Keyboards.manual_input_with_cancel()
            )
            return PICKUP_ADDRESS

        # Обработка кнопки "Аэропорт" -> переход в подменю терминалов
        if text == "Аэропорт":
            context.user_data['pickup_submenu'] = 'airport'
            context.user_data['pickup_mode'] = 'airport'
            await update.message.reply_text(
                "✈️ <b>Выберите терминал аэропорта:</b>",
                parse_mode='HTML',
                reply_markup=Keyboards.select_airport_terminal()
            )
            return SELECT_DISTRICT
        
        # Обработка кнопки "Прочие направления" -> переход в подменю
        if text == "Прочие направления":
            context.user_data['pickup_submenu'] = 'other_destinations'
            context.user_data['pickup_mode'] = 'other'
            await update.message.reply_text(
                "📍 <b>Выберите направление:</b>",
                parse_mode='HTML',
                reply_markup=Keyboards.select_other_destinations()
            )
            return SELECT_DISTRICT
        
        direct_options = {
            "Новое Жуково": "Новое Жуково",
            "Старое Жуково": "Старое Жуково",
            "Мысовцево": "Мысовцево",
            "Авдон": "Авдон",
            "Уптино": "Уптино",
            "Дёма": "Дёма",
            "Сергеевка": "Сергеевка",
            "Ж/Д вокзал": "Ж/Д вокзал"
        }

        if text not in direct_options:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите район из списка кнопок ниже:",
                reply_markup=Keyboards.select_district()
            )
            return SELECT_DISTRICT

        selected_district = direct_options[text]
        zone_id = PricingService.get_zone_id_by_name(selected_district)
        if not zone_id:
            print(f"⚠️ Не удалось определить zone_id для района '{selected_district}'")
            await update.message.reply_text(
                "❌ Не удалось определить выбранный район. Попробуйте выбрать заново.",
                reply_markup=Keyboards.select_district()
            )
            return SELECT_DISTRICT

        context.user_data['pickup_district'] = selected_district
        context.user_data['pickup_zone_id'] = zone_id
        context.user_data['pickup_mode'] = None
        context.user_data['is_from_other_destination'] = False  # Явно сбрасываем флаг для обычных районов
        
        await update.message.reply_text(
            f"✅ <b>Район: {context.user_data['pickup_district']}</b>\n\n"
            "📍 Теперь укажите <b>точный адрес отправления</b> текстом.\n\n"
            "Например: «ул. Центральная, 15» или «Жуково, 3-я линия 4».",
            parse_mode='HTML',
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        
        return PICKUP_ADDRESS


async def pickup_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка адреса отправления"""
    text = (update.message.text or "").strip()

    if text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Заказ отменен.\n\n"
            "Если передумаете — просто нажмите \"Заказать такси\" снова! 🚖",
            reply_markup=Keyboards.main_menu()
        )
        return ConversationHandler.END

    if len(text) < 5:
        await update.message.reply_text(
            "⚠️ Адрес слишком короткий. Введите, пожалуйста, полный адрес отправления.",
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        return PICKUP_ADDRESS

    context.user_data['pickup_address'] = text
    context.user_data['pickup_lat'] = None
    context.user_data['pickup_lon'] = None

    pickup_mode = context.user_data.get('pickup_mode')
    if pickup_mode in ['po_zhukovo', 'po_dema', 'po_avdon', 'po_sergeevka']:
        pickup_zone_id = context.user_data.get('pickup_zone_id')
        if not pickup_zone_id:
            await update.message.reply_text(
                "⚠️ Не удалось определить район отправления. Пожалуйста, выберите район заново.",
                reply_markup=Keyboards.select_district()
            )
            return SELECT_DISTRICT

        # Определяем зону назначения и название района
        if pickup_mode == 'po_zhukovo':
            destination_zone_name = "По Жуково"
            district_label = "Жуково"
        elif pickup_mode == 'po_dema':
            destination_zone_name = "По Дёме"
            district_label = "Дёме"
        elif pickup_mode == 'po_avdon':
            destination_zone_name = "По Авдону"
            district_label = "Авдону"
        else:  # po_sergeevka
            destination_zone_name = "По Сергеевке"
            district_label = "Сергеевке"

        destination_zone_id = PricingService.get_zone_id_by_name(destination_zone_name)
        if not destination_zone_id:
            await update.message.reply_text(
                f"⚠️ Настройки тарифов по {district_label} не найдены. Попробуйте позже или обратитесь к администратору.",
                reply_markup=Keyboards.main_menu()
            )
            return ConversationHandler.END

        price_result = PricingService.get_price(pickup_zone_id, destination_zone_id)

        if price_result.is_intercity:
            rate = price_result.rate_per_km or settings.price_per_km
            await update.message.reply_text(
                "⚠️ Для этого направления пока действует межгородской тариф.\n\n"
                f"💰 Стоимость рассчитывается по километражу: {rate:.0f} ₽/км.\n\n"
                "Попробуйте выбрать другой район или обратитесь к диспетчеру.",
                parse_mode='HTML',
                reply_markup=Keyboards.main_menu()
            )
            return ConversationHandler.END

        if price_result.is_missing or not price_result.price:
            await update.message.reply_text(
                f"⚠️ Тариф для поездок по {district_label} пока не задан. Обратитесь к диспетчеру.",
                parse_mode='HTML',
                reply_markup=Keyboards.main_menu()
            )
            return ConversationHandler.END

        context.user_data['destination_zone_id'] = destination_zone_id
        context.user_data['destination_zone_name'] = destination_zone_name
        context.user_data['calculated_price'] = float(price_result.price)

        await update.message.reply_text(
            f"💰 <b>Стоимость поездки по {district_label}:</b> {price_result.price:.0f} ₽\n\n"
            f"✍️ Укажите точный адрес назначения внутри {district_label[:-1] if district_label.endswith('е') or district_label.endswith('у') else district_label}.",
            parse_mode='HTML',
            reply_markup=Keyboards.manual_input_with_cancel()
        )

        return DROPOFF_ADDRESS

    # Проверяем, если отправление из "Прочих направлений", показываем ограниченный список назначений
    is_from_other = context.user_data.get('is_from_other_destination', False)
    
    if is_from_other:
        await update.message.reply_text(
            f"✅ <b>Адрес отправления сохранен</b>\n"
            f"📍 {context.user_data['pickup_address']}\n\n"
            "🎯 Выберите район назначения из доступных:",
            parse_mode='HTML',
            reply_markup=Keyboards.select_destination_from_other()
        )
    else:
        await update.message.reply_text(
            f"✅ <b>Адрес отправления сохранен</b>\n"
            f"📍 {context.user_data['pickup_address']}\n\n"
            "🎯 Теперь выберите район назначения.",
            parse_mode='HTML',
            reply_markup=Keyboards.select_destination_zone()
        )
    
    return SELECT_DESTINATION


async def destination_zone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора района назначения"""
    message_text = update.message.text or ""
    
    # Отладка
    destination_submenu = context.user_data.get('destination_submenu')
    logger.info(f"🔍 destination_zone_handler: message_text='{message_text}', submenu={destination_submenu}")

    if message_text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Заказ отменен.\n\n"
            "Если передумаете — просто нажмите \"Заказать такси\" снова! 🚖",
            reply_markup=Keyboards.main_menu()
        )
        return ConversationHandler.END

    if message_text == "🔙 Изменить район":
        await update.message.reply_text(
            "🏘 Выберите район, где вы находитесь:",
            reply_markup=Keyboards.select_district()
        )
        return SELECT_DISTRICT
    
    # Валидация: "По Жуково", "По Дёме", "По Авдону", "По Сергеевке" недоступны как назначение
    if message_text in ["По Жуково", "По Дёме", "По Авдону", "По Сергеевке"]:
        is_from_other = context.user_data.get('is_from_other_destination', False)
        keyboard = Keyboards.select_destination_from_other() if is_from_other else Keyboards.select_destination_zone()
        await update.message.reply_text(
            f"⚠️ Кнопка «{message_text}» доступна только как отправление.\n\n"
            "Выберите, пожалуйста, район назначения.",
            reply_markup=keyboard
        )
        return SELECT_DESTINATION
    
    # Обработка кнопки "Уфа" -> переход в подменю районов Уфы
    if message_text == "Уфа":
        context.user_data['destination_submenu'] = 'ufa'
        await update.message.reply_text(
            "🏙 <b>Выберите район Уфы для назначения:</b>",
            parse_mode='HTML',
            reply_markup=Keyboards.select_ufa_destination()
        )
        return SELECT_DESTINATION
    
    # Обработка кнопки "Аэропорт" -> переход в подменю терминалов
    if message_text == "Аэропорт":
        context.user_data['destination_submenu'] = 'airport'
        await update.message.reply_text(
            "✈️ <b>Выберите терминал аэропорта:</b>",
            parse_mode='HTML',
            reply_markup=Keyboards.select_airport_terminal()
        )
        return SELECT_DESTINATION
    
    # Обработка кнопки "Прочие направления" -> переход в подменю
    if message_text == "Прочие направления":
        context.user_data['destination_submenu'] = 'other_destinations'
        await update.message.reply_text(
            "📍 <b>Выберите направление назначения:</b>",
            parse_mode='HTML',
            reply_markup=Keyboards.select_other_destinations()
        )
        return SELECT_DESTINATION
    
    # Проверяем, находимся ли мы в подменю
    destination_submenu = context.user_data.get('destination_submenu')
    
    if destination_submenu == 'ufa':
        if message_text == "🔙 Назад":
            context.user_data.pop('destination_submenu', None)
            logger.info(f"✅ Обработана кнопка 🔙 Назад из submenu 'ufa', возвращаемся к select_destination_zone")
            await update.message.reply_text(
                "🎯 Выберите район назначения:",
                reply_markup=Keyboards.select_destination_zone()
            )
            return SELECT_DESTINATION
        
        # Обработка "Проспект Октября" - переход в подменю
        if message_text == "Проспект Октября":
            context.user_data['destination_submenu'] = 'prospekt_oktyabrya'
            await update.message.reply_text(
                "🏛 <b>Выберите точку на Проспекте Октября:</b>",
                parse_mode='HTML',
                reply_markup=Keyboards.select_prospekt_oktyabrya_submenu()
            )
            return SELECT_DESTINATION
        
        ufa_destinations = [
            "Уфа-Центр",
            "Телецентр",
            "Сипайлово",
            "Черниковка",
            "Инорс",
            "Зелёная роща"
        ]
        
        if message_text not in ufa_destinations:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите район Уфы из списка ниже:",
                reply_markup=Keyboards.select_ufa_destination()
            )
            return SELECT_DESTINATION
        
        # Район Уфы выбран, очищаем submenu и продолжаем обработку
        context.user_data.pop('destination_submenu', None)
        # message_text содержит выбранный район - продолжаем к расчету цены
    elif destination_submenu == 'other_destinations':
        if message_text == "🔙 Назад":
            context.user_data.pop('destination_submenu', None)
            logger.info(f"✅ Обработана кнопка 🔙 Назад из submenu 'other_destinations', возвращаемся к select_destination_zone")
            await update.message.reply_text(
                "🎯 Выберите район назначения:",
                reply_markup=Keyboards.select_destination_zone()
            )
            return SELECT_DESTINATION
        
        other_destinations = [
            "Дмитриевка", "Михайловка", "Миловский Парк", "Миловка",
            "Николаевка", "Юматово", "Алкино", "Кафе Отдых",
            "Чесноковка", "Затон", "Иглино", "Шакша", "Акбердино", "Нагаево", "Чишмы"
        ]
        
        if message_text not in other_destinations:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите направление из списка ниже:",
                reply_markup=Keyboards.select_other_destinations()
            )
            return SELECT_DESTINATION
        
        # Направление выбрано, очищаем submenu и продолжаем обработку
        context.user_data.pop('destination_submenu', None)
        # message_text содержит выбранное направление - продолжаем к расчету цены
    elif destination_submenu == 'airport':
        if message_text == "🔙 Назад":
            context.user_data.pop('destination_submenu', None)
            logger.info(f"✅ Обработана кнопка 🔙 Назад из submenu 'airport', возвращаемся к select_destination_zone")
            await update.message.reply_text(
                "🎯 Выберите район назначения:",
                reply_markup=Keyboards.select_destination_zone()
            )
            return SELECT_DESTINATION
        
        airport_terminals = ["Терминал 1", "Терминал 2"]
        
        if message_text not in airport_terminals:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите терминал из списка ниже:",
                reply_markup=Keyboards.select_airport_terminal()
            )
            return SELECT_DESTINATION
        
        # Терминал выбран
        selected_terminal = f"Аэропорт, {message_text}"
        context.user_data.pop('destination_submenu', None)
        message_text = "Аэропорт"  # Используем для pricing lookup
        context.user_data['dropoff_address'] = selected_terminal  # Сохраняем терминал как адрес
    elif destination_submenu == 'prospekt_oktyabrya':
        if message_text == "⬅️ Назад":
            context.user_data.pop('destination_submenu', None)
            await update.message.reply_text(
                "🏙 <b>Выберите район Уфы для назначения:</b>",
                parse_mode='HTML',
                reply_markup=Keyboards.select_ufa_destination()
            )
            return SELECT_DESTINATION
        
        prospekt_points = ["Галле", "Горсовет", "ГДК"]
        
        if message_text not in prospekt_points:
            await update.message.reply_text(
                "⚠️ Пожалуйста, выберите точку из списка ниже:",
                reply_markup=Keyboards.select_prospekt_oktyabrya_submenu()
            )
            return SELECT_DESTINATION
        
        # Точка выбрана - преобразуем в правильный ID для pricing
        point_mapping = {
            "Галле": "Проспект Октября — Галле",
            "Горсовет": "Проспект Октября — Горсовет",
            "ГДК": "Проспект Октября — ГДК"
        }
        
        selected_point = point_mapping[message_text]
        context.user_data.pop('destination_submenu', None)
        context.user_data['dropoff_address'] = f"Проспект Октября, {message_text}"  # Сохраняем адрес
        message_text = selected_point  # Используем для pricing lookup
    else:
        # Проверяем, если отправление из "Прочих направлений"
        is_from_other = context.user_data.get('is_from_other_destination', False)
        
        if is_from_other:
            # Для "Прочих направлений" доступны только 6 базовых зон
            valid_destinations = ["Старое Жуково", "Новое Жуково", "Мысовцево", "Дёма", "Авдон", "Уптино"]
            
            if message_text not in valid_destinations:
                await update.message.reply_text(
                    "⚠️ Для «Прочих направлений» доступны только направления:\n\n"
                    "Старое/Новое Жуково, Мысовцево, Уптино, Дёма, Авдон.",
                    reply_markup=Keyboards.select_destination_from_other()
                )
                return SELECT_DESTINATION
        else:
            # Не в подменю - проверяем основные направления
            valid_destinations = ["Ж/Д вокзал", "Дёма", "Авдон", "Уптино", "Затон", "ТРЦ МЕГА", "Вьетнамский рынок", "Яркий"]
            
            if message_text not in valid_destinations:
                await update.message.reply_text(
                    "⚠️ Пожалуйста, выберите район назначения с помощью кнопок ниже.",
                    reply_markup=Keyboards.select_destination_zone()
                )
                return SELECT_DESTINATION

    pickup_zone_id = context.user_data.get('pickup_zone_id')
    if not pickup_zone_id:
        await update.message.reply_text(
            "⚠️ Сначала выберите район, где вы находитесь.",
            reply_markup=Keyboards.select_district()
        )
        return SELECT_DISTRICT

    destination_zone_id = PricingService.get_zone_id_by_name(message_text)
    if not destination_zone_id:
        await update.message.reply_text(
            "❌ Не удалось определить выбранный район назначения. Попробуйте еще раз.",
            reply_markup=Keyboards.select_destination_zone()
        )
        return SELECT_DESTINATION

    price_result = PricingService.get_price(pickup_zone_id, destination_zone_id)

    if price_result.is_intercity:
        rate = price_result.rate_per_km or settings.price_per_km
        await update.message.reply_text(
            "⚠️ Для этого направления действует межгородской тариф.\n\n"
            f"💰 Стоимость рассчитывается по километражу: {rate:.0f} ₽/км.\n\n"
            "Пока автоматический расчет недоступен. Пожалуйста, выберите другой район назначения "
            "или воспользуйтесь кнопкой \"🛣 Межгород\" в главном меню.",
            parse_mode='HTML',
            reply_markup=Keyboards.select_destination_zone()
        )
        return SELECT_DESTINATION

    if price_result.is_missing:
        await update.message.reply_text(
            "⚠️ Тариф для выбранного направления пока не задан.\n\n"
            "Выберите другой район назначения или свяжитесь с диспетчером.",
            parse_mode='HTML',
            reply_markup=Keyboards.select_destination_zone()
        )
        return SELECT_DESTINATION

    context.user_data['destination_zone_id'] = destination_zone_id
    context.user_data['destination_zone_name'] = message_text
    context.user_data['calculated_price'] = float(price_result.price)

    # Если назначение — аэропорт, адрес уже сохранён, пропускаем ввод
    if context.user_data.get('dropoff_address'):
        # Создаем заказ сразу
        db = SessionLocal()
        try:
            user = update.effective_user
            db_user = UserService.get_or_create_user(db, user)
            
            # Проверяем, нужен ли broadcast-режим
            pickup_district = context.user_data.get('pickup_district', '')
            is_broadcast = BroadcastService.is_broadcast_zone(pickup_district)
            
            order = OrderService.create_order(
                db=db,
                customer=db_user,
                pickup_district=pickup_district,
                pickup_address=context.user_data['pickup_address'],
                dropoff_address=context.user_data['dropoff_address'],
                price=context.user_data['calculated_price'],
                dropoff_zone=context.user_data.get('destination_zone_name'),
                is_broadcast=is_broadcast
            )
            
            context.user_data['order_id'] = order.id
            
            # Если broadcast-режим, отправляем уведомления водителям
            if is_broadcast:
                broadcast_sent = await BroadcastService.send_broadcast(
                    db, order, update.get_bot(), context
                )
                if broadcast_sent:
                    await update.message.reply_text(
                        "✅ <b>Заказ создан!</b>\n\n"
                        "🔔 Уведомления отправлены водителям.\n"
                        "Ожидайте принятия заказа...",
                        parse_mode='HTML',
                        reply_markup=Keyboards.main_menu()
                    )
                    return ConversationHandler.END
                else:
                    await update.message.reply_text(
                        "⚠️ Свободных водителей не найдено.\n"
                        "Попробуйте создать заказ позже.",
                        parse_mode='HTML',
                        reply_markup=Keyboards.main_menu()
                    )
                    return ConversationHandler.END
            
            destination_zone = context.user_data.get('destination_zone_name', 'не указан')
            order_summary = (
                "📋 <b>Подтвердите заказ</b>\n\n"
                f"{order.display_info}\n"
                f"🎯 Район назначения: {destination_zone}"
            )
            
            await update.message.reply_text(
                order_summary,
                parse_mode='HTML',
                reply_markup=Keyboards.confirm_order(order.id)
            )
            
            return CONFIRM_ORDER
        finally:
            db.close()
    
    # Обычный случай - запрашиваем адрес назначения
    await update.message.reply_text(
        f"💰 <b>Стоимость поездки:</b> {price_result.price:.0f} ₽\n\n"
        "✍️ Теперь укажите точный адрес назначения текстом.",
        parse_mode='HTML',
        reply_markup=Keyboards.manual_input_with_cancel()
    )

    return DROPOFF_ADDRESS


async def dropoff_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка адреса назначения"""
    text = (update.message.text or "").strip()

    if text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Заказ отменен.\n\n"
            "Если передумаете — просто нажмите \"Заказать такси\" снова! 🚖",
            reply_markup=Keyboards.main_menu()
        )
        return ConversationHandler.END
    
    if not context.user_data.get('destination_zone_id'):
        await update.message.reply_text(
            "⚠️ Сначала выберите район назначения.",
            reply_markup=Keyboards.select_destination_zone()
        )
        return SELECT_DESTINATION

    if not context.user_data.get('calculated_price'):
        await update.message.reply_text(
            "⚠️ Не удалось определить стоимость. Попробуйте выбрать район назначения заново.",
            reply_markup=Keyboards.select_destination_zone()
        )
        return SELECT_DESTINATION
    
    if len(text) < 5:
        await update.message.reply_text(
            "⚠️ Адрес слишком короткий. Укажите, пожалуйста, полный адрес назначения.",
            reply_markup=Keyboards.manual_input_with_cancel()
        )
        return DROPOFF_ADDRESS

    context.user_data['dropoff_address'] = text
    context.user_data['dropoff_lat'] = None
    context.user_data['dropoff_lon'] = None
    
    # Создаем заказ
    db = SessionLocal()
    try:
        user = update.effective_user
        db_user = UserService.get_or_create_user(db, user)
        
        print(f"🚖 Создание заказа для пользователя {db_user.full_name}")
        print(f"   Район: {context.user_data.get('pickup_district')}")
        print(f"   Откуда: {context.user_data['pickup_address']}")
        print(f"   Куда: {context.user_data['dropoff_address']}")
        
        # Проверяем, нужен ли broadcast-режим
        pickup_district = context.user_data.get('pickup_district', '')
        is_broadcast = BroadcastService.is_broadcast_zone(pickup_district)
        
        order = OrderService.create_order(
            db=db,
            customer=db_user,
            pickup_district=pickup_district,
            pickup_address=context.user_data['pickup_address'],
            pickup_lat=context.user_data.get('pickup_lat'),
            pickup_lon=context.user_data.get('pickup_lon'),
            dropoff_address=context.user_data['dropoff_address'],
            dropoff_lat=context.user_data.get('dropoff_lat'),
            dropoff_lon=context.user_data.get('dropoff_lon'),
            price=context.user_data['calculated_price'],
            dropoff_zone=context.user_data.get('destination_zone_name'),
            is_broadcast=is_broadcast
        )
        
        print(f"✅ Заказ #{order.id} создан успешно")
        
        context.user_data['order_id'] = order.id
        
        # Если broadcast-режим, отправляем уведомления водителям
        if is_broadcast:
            broadcast_sent = await BroadcastService.send_broadcast(
                db, order, update.get_bot(), context
            )
            if broadcast_sent:
                await update.message.reply_text(
                    "✅ <b>Заказ создан!</b>\n\n"
                    "🔔 Уведомления отправлены водителям.\n"
                    "Ожидайте принятия заказа...",
                    parse_mode='HTML',
                    reply_markup=Keyboards.main_menu()
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "⚠️ Свободных водителей не найдено.\n"
                    "Попробуйте создать заказ позже.",
                    parse_mode='HTML',
                    reply_markup=Keyboards.main_menu()
                )
                return ConversationHandler.END
        
        destination_zone = context.user_data.get('destination_zone_name', 'не указан')
        order_summary = (
            "📋 <b>Подтвердите заказ</b>\n\n"
            f"{order.display_info}\n"
            f"🎯 Район назначения: {destination_zone}"
        )
        
        await update.message.reply_text(
            order_summary,
            parse_mode='HTML',
            reply_markup=Keyboards.confirm_order(order.id)
        )
        
        return CONFIRM_ORDER
    except Exception as e:
        print(f"❌ ОШИБКА при создании заказа: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ Произошла ошибка при создании заказа. Попробуйте ещё раз или обратитесь к администратору.",
            reply_markup=Keyboards.main_menu()
        )
        return ConversationHandler.END
    finally:
        db.close()


async def confirm_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение или отмена заказа"""
    query = update.callback_query
    await query.answer()
    
    action, order_id = query.data.split(':')
    order_id = int(order_id)
    
    db = SessionLocal()
    try:
        order = OrderService.get_order_by_id(db, order_id)
        
        if action == "confirm_order":
            await query.edit_message_text(
                f"✅ <b>Заказ #{order.id} подтвержден!</b>\n\n"
                "🔍 Ищем ближайшего свободного водителя...\n"
                "⏱ Обычно это занимает не более 1-2 минут.\n\n"
                "📱 Вы получите уведомление, как только водитель примет заказ!\n\n"
                "💡 <i>Следите за обновлениями в этом чате</i>\n\n"
                "👇 Если передумали, можете отменить заказ:",
                parse_mode='HTML',
                reply_markup=Keyboards.customer_cancel_order(order.id)
            )
            
            # Запускаем новую систему очередей
            if order.zone:
                from bot.handlers.user_queue import dispatch_order_to_queue
                await dispatch_order_to_queue(order.id, db)
            else:
                # Fallback на старую систему если зона не установлена
                await notify_online_drivers(context, order)
            
        elif action == "cancel_order":
            OrderService.cancel_order(db, order)
            await query.edit_message_text(
                "❌ <b>Заказ отменен</b>\n\n"
                "Не переживайте, вы можете создать новый заказ в любое время! 🚖",
                parse_mode='HTML'
            )
        
        # Возвращаем главное меню
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Что хотите сделать дальше?",
            reply_markup=Keyboards.main_menu()
        )
        
        return ConversationHandler.END
    finally:
        db.close()


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """История заказов"""
    print(f"📋 history_command вызван! Пользователь: {update.effective_user.id}")
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_or_create_user(db, user)
        print(f"✓ Пользователь найден: {db_user.full_name if db_user else 'не найден'}")
        
        if not await ensure_user_authenticated(update, context, db_user):
            return
        
        orders = OrderService.get_customer_history(db, db_user)
        
        if not orders:
            await update.message.reply_text(
                "📋 <b>История заказов</b>\n\n"
                "У вас пока нет завершенных заказов.\n\n"
                "🚖 Нажмите \"Заказать такси\", чтобы сделать первый заказ!",
                parse_mode='HTML'
            )
            return
        
        history_text = "📋 <b>История ваших поездок</b>\n\n"
        for i, order in enumerate(orders, 1):
            history_text += f"<b>Поездка #{i}</b>\n"
            history_text += f"{order.display_info}\n"
            if order.rating:
                history_text += f"⭐ Ваша оценка: {order.rating}/5\n"
            history_text += "➖➖➖➖➖➖➖➖➖\n\n"
        
        await update.message.reply_text(history_text, parse_mode='HTML')
    finally:
        db.close()


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Действие отменено.\n\n"
        "Возвращаю вас в главное меню 👇",
        reply_markup=Keyboards.main_menu()
    )
    return ConversationHandler.END


async def pricing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о фиксированных тарифах"""
    print(f"💵 pricing_command вызван! Пользователь: {update.effective_user.id}")
    origin_names = [
        "Старое Жуково",
        "Новое Жуково",
        "По Жуково",
        "Дёма",
        "Авдон",
        "Уптино",
        "Мысовцево",
        "Аэропорт",
        "Уфа-Центр",
        "Сипайлово",
        "Черниковка",
        "Телецентр",
        "Чесноковка"
    ]
    destination_names = [
        "Уфа-Центр",
        "Телецентр",
        "Сипайлово",
        "Черниковка",
        "Чесноковка",
        "По Жуково",
        "Аэропорт"
    ]

    rows = []
    for origin in origin_names:
        origin_id = PricingService.get_zone_id_by_name(origin)
        if not origin_id:
            continue

        rate_lines = []
        for destination in destination_names:
            destination_id = PricingService.get_zone_id_by_name(destination)
            if not destination_id:
                continue

            price_info = PricingService.get_price(origin_id, destination_id)
            if price_info.is_available:
                rate_lines.append(f"• {destination}: {price_info.price:.0f} ₽")

        if rate_lines:
            rows.append(f"<b>{origin} →</b>\n" + "\n".join(rate_lines))

    if not rows:
        rows.append("Тарифы будут опубликованы позже. Пожалуйста, уточните стоимость у оператора.")

    pricing_text = (
        "💵 <b>Фиксированные тарифы Такси Жуково+</b>\n\n"
        + "\n\n".join(rows)
        + "\n\n"
        "🛣 <b>Межгород:</b>\n"
        "• Стоимость обсуждается напрямую с водителем через раздел «🛣 Межгород».\n\n"
        "💡 Точная стоимость показывается автоматически при создании заказа."
    )

    await update.message.reply_text(pricing_text, parse_mode='HTML')


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контактная информация"""
    print(f"📞 contact_command вызван! Пользователь: {update.effective_user.id}")
    contact_text = (
        "📞 <b>Контакты и поддержка</b>\n\n"
        "🚖 <b>Такси Жуково+</b>\n\n"
        "📱 <b>Связаться с оператором:</b>\n"
        "По всем вопросам обращайтесь к администратору\n\n"
        "⏰ <b>Режим работы:</b>\n"
        "Круглосуточно, без выходных\n\n"
        "🗺 <b>Зона обслуживания:</b>\n"
        "• Жуково\n"
        "• Дёма\n"
        "• Авдон\n"
        "• Прилегающие районы\n\n"
        "💬 <b>Есть вопросы?</b>\n"
        "Просто напишите нам, и мы обязательно поможем!"
    )
    
    await update.message.reply_text(contact_text, parse_mode='HTML')


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Правила пользования"""
    print(f"📜 rules_command вызван! Пользователь: {update.effective_user.id}")
    rules_text = (
        "📜 <b>Правила пользования</b>\n\n"
        "• Регистрация по номеру телефона обязательна.\n"
        "• Если вы отменяете заказ спустя 5 минут после подтверждения водителем, вы получаете предупреждение (срок — 2 месяца).\n"
        "• Повторная отмена в течение 2 месяцев приводит к перманентной блокировке аккаунта.\n"
        "• Межгород: стоимость и детали поездки обсуждаются напрямую с водителем."
    )
    await update.message.reply_text(rules_text, parse_mode='HTML')


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    await update.message.reply_text("👇 Главное меню", reply_markup=Keyboards.main_menu())

async def intercity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о междугороднем тарифе"""
    print(f"🛣 intercity_command вызван! Пользователь: {update.effective_user.id}")
    intercity_text = (
        "🛣 <b>Межгородние поездки</b>\n\n"
        "💬 <b>Как это работает:</b>\n"
        "Вы выбираете точку отправления и вручную указываете пункт назначения.\n"
        "Далее бот рассылает запрос всем доступным водителям — вы можете списаться с ними для уточнения деталей и цены.\n\n"
        "🚗 <b>Примеры популярных направлений:</b>\n"
        "• Дёма → Стерлитамак (~115 км)\n"
        "• Жуково → Октябрьский (~170 км)\n"
        "• Мысовцево → Набережные Челны (~200 км)\n"
        "• Дёма → Казань (~520 км)\n"
        "• Жуково → Ижевск (~340 км)\n\n"
        "🎯 <b>Как заказать:</b>\n"
        "Нажмите «Заказать межгород» и укажите:\n"
        "Откуда: Дёма / Жуково / Мысовцево (кнопкой)\n"
        "Куда: введите населённый пункт/адрес вручную\n\n"
        "ℹ️ Стоимость и детали поездки уточняются напрямую с водителем."
    )
    
    await update.message.reply_text(intercity_text, parse_mode='HTML', reply_markup=Keyboards.intercity_menu())
    return None  # Явно возвращаем None, чтобы не было ошибки с await


async def active_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активный заказ"""
    print(f"📍 active_order_command вызван! Пользователь: {update.effective_user.id}")
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_or_create_user(db, user)
        print(f"✓ Пользователь найден: {db_user.full_name if db_user else 'не найден'}")
        
        if not await ensure_user_authenticated(update, context, db_user):
            return
        
        # Получаем активный заказ
        active_order = OrderService.get_active_order_by_customer(db, db_user)
        
        if not active_order:
            await update.message.reply_text(
                "✅ <b>У вас нет активных заказов</b>\n\n"
                "Вы можете создать новый заказ, нажав кнопку \"Заказать такси\" 🚖",
                parse_mode='HTML'
            )
            return
        
        # Показываем информацию об активном заказе с кнопкой отмены
        status_text = {
            "pending": "⏳ Ожидает водителя",
            "accepted": "✅ Водитель принял заказ",
            "in_progress": "🚗 Поездка в процессе"
        }
        
        message = (
            f"<b>📋 Ваш активный заказ</b>\n\n"
            f"{active_order.display_info}\n\n"
            f"<b>Статус:</b> {status_text.get(active_order.status, active_order.status)}\n\n"
        )
        
        if active_order.driver:
            message += f"<b>👤 Водитель:</b> {active_order.driver.full_name}\n\n"
        
        message += "Если хотите отменить заказ, нажмите кнопку ниже:"
        
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=Keyboards.customer_cancel_order(active_order.id)
        )
    finally:
        db.close()


async def customer_cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заказа клиентом после подтверждения"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        # Игнорируем ошибку устаревшего callback (пользователь нажал старую кнопку)
        if "too old" in str(e).lower() or "expired" in str(e).lower():
            pass
        else:
            raise
    
    action, order_id = query.data.split(':')
    order_id = int(order_id)
    
    db = SessionLocal()
    try:
        order = OrderService.get_order_by_id(db, order_id)
        
        # Проверяем, что заказ принадлежит этому клиенту
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not order or order.customer_id != db_user.id:
            await query.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Проверяем, что заказ не завершен
        if order.status in {OrderStatus.COMPLETED, OrderStatus.CANCELLED}:
            await query.answer("⚠️ Этот заказ уже завершен", show_alert=True)
            return
        
        # Проверяем, нужно ли применять санкции
        penalize = False
        if order.accepted_at:
            elapsed = datetime.utcnow() - order.accepted_at
            if elapsed > timedelta(minutes=5):
                penalize = True

        # Отменяем заказ
        OrderService.cancel_order(db, order)
        
        # Отменяем таймеры для этого заказа (если они есть)
        from bot.services.scheduler import scheduler
        from bot.services.order_dispatcher import get_dispatcher
        try:
            dispatcher = get_dispatcher()
            await scheduler.cancel_order_timeout(order.id)
            # Если заказ был назначен водителю, отменяем и таймер водителя
            if order.assigned_driver_id:
                await scheduler.cancel_driver_timeout(order.assigned_driver_id)
        except Exception as e:
            # Если не удалось отменить таймеры, это не критично
            pass
        
        # Формируем сообщение в зависимости от статуса
        if order.status == OrderStatus.PENDING:
            message = (
                "❌ <b>Заказ отменен</b>\n\n"
                f"Заказ #{order.id} был успешно отменен.\n\n"
                "Не переживайте, вы можете создать новый заказ в любое время! 🚖"
            )
        else:
            message = (
                "❌ <b>Заказ отменен</b>\n\n"
                f"Заказ #{order.id} был отменен.\n\n"
                "⚠️ Если водитель уже был назначен, пожалуйста, извинитесь за отмену.\n\n"
                "🚖 Вы можете создать новый заказ в любое время!"
            )
        
        await query.edit_message_text(message, parse_mode='HTML')

        if penalize:
            penalty_result = UserPenaltyService.warn_or_ban(db, db_user)
            if penalty_result == "warning":
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="⚠️ Вы отменили поездку спустя 5 минут после подтверждения. Предупреждение действует 2 месяца."
                )
            elif penalty_result == "banned":
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="⛔ Аккаунт заблокирован за повторную отмену в течение 2 месяцев. Для разблокировки обратитесь к администратору @mrbrennan"
                )
        
        # Отправляем главное меню
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Что хотите сделать дальше?",
            reply_markup=Keyboards.main_menu()
        )
    finally:
        db.close()


async def user_order_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды '🧾 Мои поездки' для клиента"""
    db = SessionLocal()
    
    try:
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            await update.message.reply_text("❌ Вы не зарегистрированы в системе")
            return
        
        # Получаем offset из callback data (для пагинации)
        offset = 0
        if update.callback_query:
            try:
                _, offset_str = update.callback_query.data.split(":")
                offset = int(offset_str)
            except:
                offset = 0
        
        # Получаем историю заказов
        limit = 10
        orders = OrderService.get_user_order_history(db, db_user.id, limit=limit, offset=offset)
        
        if not orders and offset == 0:
            await update.message.reply_text(
                "📭 <b>История поездок пуста</b>\n\n"
                "У вас пока нет завершённых или отменённых заказов.",
                parse_mode='HTML'
            )
            return
        
        # Формируем сообщение с историей
        from datetime import datetime, timedelta
        
        message = "🧾 <b>Ваши поездки</b>\n\n"
        
        for order in orders:
            status_emoji = {
                "finished": "✅",
                "cancelled": "❌",
                "expired": "⏱",
                "completed": "✅"
            }.get(order.status.value if hasattr(order.status, 'value') else order.status, "📋")
            
            date_str = order.finished_at.strftime('%d.%m.%Y %H:%M') if order.finished_at else order.created_at.strftime('%d.%m.%Y %H:%M')
            
            # Получаем информацию о водителе
            driver_info = "—"
            if order.assigned_driver_id:
                from bot.models.driver import Driver
                driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
                if driver:
                    driver_info = f"{driver.user.full_name} ({driver.car_model} {driver.car_number})"
            
            # Оценка
            rating_str = ""
            if order.rating:
                rating_str = f"\n⭐ Оценка: {'⭐' * order.rating}"
            
            # Проверяем, можно ли изменить оценку (в течение 24ч)
            can_rate = False
            if order.finished_at:
                time_since_finish = datetime.utcnow() - order.finished_at
                can_rate = time_since_finish <= timedelta(hours=24)
            
            message += (
                f"{status_emoji} <b>№{order.id}</b> • {date_str}\n"
                f"📍 {order.pickup_address[:30]}{'...' if len(order.pickup_address) > 30 else ''}\n"
                f"🎯 {order.dropoff_address[:30]}{'...' if len(order.dropoff_address) > 30 else ''}\n"
            )
            
            if driver_info != "—":
                message += f"🚗 {driver_info}\n"
            
            if order.price and order.price > 0:
                message += f"💰 {order.price:.0f} ₽\n"
            
            message += f"📊 Статус: {status_emoji} {order.status.value if hasattr(order.status, 'value') else order.status}"
            
            if rating_str:
                message += rating_str
            elif can_rate and order.status.value == "finished":
                message += "\n⚠️ <i>Можно оценить (до 24ч)</i>"
            
            message += "\n\n"
        
        # Добавляем кнопку "Показать ещё" если есть ещё заказы
        keyboard = []
        
        if len(orders) == limit:
            keyboard.append([InlineKeyboardButton("📄 Показать ещё", callback_data=f"user_history:{offset + limit}")])
        
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
        print(f"❌ Ошибка при получении истории заказов клиента: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text("❌ Произошла ошибка при загрузке истории")
    finally:
        db.close()


def register_user_handlers(application: Application):
    """Регистрация обработчиков для пользователей"""
    
    print("📝 Регистрация обработчиков пользователей...")
    
    # Обработчик создания заказа
    # Исключаем команды водителей и кнопки пользователей из перехвата
    excluded_commands = [
        '🟢 Я на линии', '🔴 Я оффлайн', '📋 Мои заказы', '📊 Статистика',
        '📍 Новое Жуково', '📍 Старое Жуково', '📍 Мысовцево', '📍 Авдон', '📍 Уптино', '📍 Дёма', '🔙 Назад',
        '📍 Мой заказ', 'ℹ️ Помощь', '💵 Тарифы', '📞 Связаться',
        '📜 Правила пользования', '🛣 Межгород', '🔙 В главное меню'
    ]
    driver_commands_filter = ~filters.Regex(f'^({"|".join(excluded_commands)})$')
    order_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('order', order_start),
            MessageHandler(filters.Regex('^🚖 Заказать такси$'), order_start)
        ],
        states={
            SELECT_DISTRICT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & driver_commands_filter, district_handler)
            ],
            PICKUP_ADDRESS: [
                MessageHandler(filters.LOCATION | (filters.TEXT & ~filters.COMMAND & driver_commands_filter), pickup_address_handler)
            ],
            SELECT_DESTINATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & driver_commands_filter, destination_zone_handler)
            ],
            DROPOFF_ADDRESS: [
                MessageHandler(filters.LOCATION | (filters.TEXT & ~filters.COMMAND & driver_commands_filter), dropoff_address_handler)
            ],
            CONFIRM_ORDER: [
                CallbackQueryHandler(confirm_order_callback, pattern='^(confirm_order|cancel_order):\d+$')
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command),
            # Завершаем разговор при нажатии на кнопки меню
            MessageHandler(filters.Regex('^(📍 Мой заказ|📋 Мои заказы|ℹ️ Помощь|💵 Тарифы|📞 Связаться|📜 Правила пользования|🛣 Межгород|🔙 В главное меню)$'), 
                          lambda u, c: ConversationHandler.END)
        ],
        per_message=False,  # Важно: не перехватывать каждое сообщение
        allow_reentry=True  # Разрешить повторный вход в разговор
    )
    intercity_conv_handler = build_intercity_conversation()
    
    # ВАЖНО: Регистрируем обработчики кнопок меню с группой -1 (МАКСИМАЛЬНЫЙ приоритет)
    # Это гарантирует, что они обработаются РАНЬШЕ ConversationHandler
    
    # Команды (группа -1 для максимального приоритета)
    application.add_handler(CommandHandler('start', start_command), group=-1)
    application.add_handler(CommandHandler('menu', start_command), group=-1)  # /menu - синоним /start
    application.add_handler(CommandHandler('switch_role', switch_role_command), group=-1)
    application.add_handler(CommandHandler('help', help_command), group=-1)
    application.add_handler(CommandHandler('history', history_command), group=-1)
    application.add_handler(CommandHandler('active', active_order_command), group=-1)
    
    # Обработка текстовых кнопок главного меню (группа -1 - МАКСИМАЛЬНЫЙ ПРИОРИТЕТ!)
    application.add_handler(MessageHandler(filters.Regex('^📍 Мой заказ$'), active_order_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои заказы$'), history_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^🧾 Мои поездки$'), user_order_history_handler), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^ℹ️ Помощь$'), help_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^💵 Тарифы$'), pricing_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^📞 Связаться$'), contact_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^📜 Правила пользования$'), rules_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^🛣 Межгород|🧭 Межгород$'), intercity_command), group=-1)
    application.add_handler(MessageHandler(filters.Regex('^🔙 В главное меню$'), back_to_main_menu), group=-1)
    
    # Обработчик пагинации истории
    application.add_handler(CallbackQueryHandler(user_order_history_handler, pattern='^user_history:\d+$'), group=-1)
    
    # ConversationHandler регистрируем в группе 1 (НИЗКИЙ ПРИОРИТЕТ)
    # block=False позволяет другим обработчикам обрабатывать сообщения
    application.add_handler(order_conv_handler, group=1)
    application.add_handler(intercity_conv_handler, group=1)
    
    # Обработчик отмены заказа клиентом (группа -1 для приоритета)
    application.add_handler(CallbackQueryHandler(customer_cancel_order_callback, pattern='^customer_cancel:\d+$'), group=-1)
    application.add_handler(build_intercity_select_handler(), group=-1)
    
    # Хэндлеры оценки и комментариев
    from .user_rating import register_rating_handlers
    register_rating_handlers(application)
    
    print("✅ Обработчики пользователей зарегистрированы!")
    print(f"   - ConversationHandler для заказа (кнопка '🚖 Заказать такси')")
    print(f"   - Команды: /start, /help, /history, /active")
    print(f"   - Кнопки меню: Мой заказ, Мои заказы, Помощь, Тарифы, Связаться, Межгород")

