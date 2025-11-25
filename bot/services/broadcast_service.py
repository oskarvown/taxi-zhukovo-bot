"""
Сервис для broadcast-уведомлений специальных зон
Обрабатывает заказы из Уфы, Прочих направлений, ЖД-вокзала, Аэропорта
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from bot.models.driver import Driver, DriverStatus
from bot.models.order import Order, OrderStatus
from bot.models.user import User
from bot.services.scheduler import scheduler


# Зоны, которые используют broadcast-режим
BROADCAST_ZONES = [
    "Уфа-Центр", "Телецентр", "Сипайлово", "Черниковка", "Чесноковка",
    "Инорс", "Зелёная роща",  # Уфа
    "Ж/Д вокзал",  # ЖД
    "Аэропорт",  # Аэропорт с терминалами
    "Дмитриевка", "Михайловка", "Миловский Парк", "Миловка",
    "Николаевка", "Юматово", "Алкино", "Кафе Отдых",
    "Иглино", "Шакша", "Акбердино", "Нагаево", "Чишмы"  # Прочие направления
]

# Настройки таймингов
BROADCAST_WINDOW_SECONDS = 30  # Окно для откликов
MAX_ETA_FOR_RESERVE_MINUTES = 15  # Макс ETA для резервации занятым
RESERVE_TTL_MINUTES = 15  # Срок действия резерва


class BroadcastService:
    """Сервис широковещательных уведомлений"""
    
    @staticmethod
    def is_broadcast_zone(pickup_district: str) -> bool:
        """Проверяет, является ли зона broadcast-зоной"""
        # Проверяем по списку или если начинается с "Аэропорт, Терминал"
        return (
            pickup_district in BROADCAST_ZONES or
            pickup_district.startswith("Аэропорт")
        )
    
    @staticmethod
    def get_eligible_drivers(
        db: Session,
        order: Order
    ) -> Tuple[List[Driver], List[Driver]]:
        """
        Получить водителей, которым можно отправить broadcast
        
        Returns:
            (свободные_водители, занятые_по_пути)
        """
        # Свободные водители (status=online)
        free_drivers = db.query(Driver).join(User).filter(
            Driver.status == DriverStatus.ONLINE,
            Driver.pending_order_id.is_(None)
        ).all()
        
        # Занятые водители "по пути" к зоне отправления
        # Условие: status=busy AND next_finish_zone == pickup_zone AND eta <= MAX_ETA
        busy_drivers = []
        if order.pickup_district:
            busy_drivers = db.query(Driver).join(User).filter(
                Driver.status == DriverStatus.BUSY,
                Driver.next_finish_zone == order.pickup_district,
                Driver.eta_to_finish.isnot(None),
                Driver.eta_to_finish <= MAX_ETA_FOR_RESERVE_MINUTES
            ).all()
        
        return free_drivers, busy_drivers
    
    @staticmethod
    async def send_broadcast(
        db: Session,
        order: Order,
        bot,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Отправить broadcast-уведомление всем подходящим водителям
        
        Returns:
            True если хотя бы одному водителю отправлено
        """
        free_drivers, busy_drivers = BroadcastService.get_eligible_drivers(db, order)
        
        if not free_drivers and not busy_drivers:
            print(f"⚠️  Нет доступных водителей для broadcast заказа #{order.id}")
            return False
        
        sent_count = 0
        
        # Формируем сообщение для водителей
        order_info = BroadcastService._format_order_info(order)
        
        # Отправляем свободным водителям
        for driver in free_drivers:
            try:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "✅ Принять",
                        callback_data=f"broadcast_accept:{order.id}"
                    )
                ]])
                
                await bot.send_message(
                    chat_id=driver.user.telegram_id,
                    text=f"🔔 <b>Новый заказ (broadcast)</b>\n\n{order_info}",
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                sent_count += 1
                print(f"✅ Broadcast отправлен свободному водителю #{driver.id}")
            except Exception as e:
                print(f"❌ Ошибка отправки broadcast водителю #{driver.id}: {e}")
        
        # Отправляем занятым "по пути"
        for driver in busy_drivers:
            try:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "📌 Взять после текущей",
                        callback_data=f"broadcast_reserve:{order.id}"
                    )
                ]])
                
                eta_text = f"(≈ {driver.eta_to_finish} мин)" if driver.eta_to_finish else ""
                await bot.send_message(
                    chat_id=driver.user.telegram_id,
                    text=(
                        f"🔔 <b>Новый заказ (резерв)</b>\n\n"
                        f"{order_info}\n\n"
                        f"💡 Вы можете зарезервировать этот заказ после завершения текущей поездки {eta_text}"
                    ),
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                sent_count += 1
                print(f"✅ Broadcast резерв отправлен занятому водителю #{driver.id}")
            except Exception as e:
                print(f"❌ Ошибка отправки broadcast резерва водителю #{driver.id}: {e}")
        
        # Устанавливаем таймер на истечение broadcast-окна
        if sent_count > 0:
            async def on_broadcast_timeout(order_id: int):
                """Callback при истечении broadcast-окна"""
                from database.db import SessionLocal
                timeout_db = SessionLocal()
                try:
                    timeout_order = timeout_db.query(Order).filter(Order.id == order_id).first()
                    if timeout_order and timeout_order.status == OrderStatus.NEW:
                        # Переводим в EXPIRED
                        timeout_order.status = OrderStatus.EXPIRED
                        timeout_db.commit()
                        
                        # Уведомляем клиента
                        try:
                            customer = timeout_db.query(User).filter(User.id == timeout_order.customer_id).first()
                            if customer:
                                await bot.send_message(
                                    customer.telegram_id,
                                    "⚠️ К сожалению, ни один водитель не принял ваш заказ.\n\n"
                                    "Попробуйте создать новый заказ или свяжитесь с диспетчером."
                                )
                        except Exception as e:
                            print(f"❌ Ошибка уведомления клиента о истечении заказа #{order_id}: {e}")
                        
                        print(f"⏰ Broadcast-окно истекло для заказа #{order_id}, статус → EXPIRED")
                finally:
                    timeout_db.close()
            
            await scheduler.schedule_order_timeout(
                order.id,
                BROADCAST_WINDOW_SECONDS,
                on_broadcast_timeout
            )
        
        return sent_count > 0
    
    @staticmethod
    def _format_order_info(order: Order) -> str:
        """Форматирует информацию о заказе для водителя"""
        dropoff_zone = order.dropoff_zone if hasattr(order, 'dropoff_zone') else "не указан"
        
        return (
            f"📍 <b>Откуда:</b> {order.pickup_district or 'не указан'}\n"
            f"   {order.pickup_address}\n\n"
            f"🎯 <b>Куда:</b> {dropoff_zone}\n"
            f"   {order.dropoff_address}\n\n"
            f"💰 <b>Стоимость:</b> {order.price:.0f} ₽"
        )
    
    # Примечание: таймаут broadcast-заказов обрабатывается через scheduler.schedule_order_timeout
    
    @staticmethod
    async def accept_broadcast_order(
        db: Session,
        order_id: int,
        driver: Driver,
        bot,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Tuple[bool, str]:
        """
        Водитель принимает broadcast-заказ
        
        Returns:
            (успех, сообщение)
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            return False, "Заказ не найден"
        
        if order.status != OrderStatus.NEW:
            return False, "Заказ уже принят другим водителем"
        
        if driver.pending_order_id is not None:
            return False, "У вас уже есть активный заказ"
        
        # Назначаем заказ водителю
        order.status = OrderStatus.ACCEPTED
        order.driver_id = driver.user_id
        order.assigned_driver_id = driver.id
        order.accepted_at = datetime.utcnow()
        
        driver.status = DriverStatus.BUSY
        driver.pending_order_id = order.id
        
        db.commit()
        
        print(f"✅ handle_accept saved order={order_id} assigned_driver={driver.id} status={order.status.value}")
        
        # Отменяем таймер broadcast-окна
        try:
            await scheduler.cancel_order_timeout(order_id)
        except Exception as e:
            pass  # Если таймера нет - не критично
        
        # Уведомляем водителя новым сообщением с актуальными кнопками
        try:
            from bot.utils.keyboards import Keyboards
            await bot.send_message(
                chat_id=driver.user.telegram_id,
                text=(
                    f"📋 <b>Заказ #{order.id}</b>\n\n"
                    f"📍 Откуда: {order.pickup_address}\n"
                    f"📍 Куда: {order.dropoff_address}\n"
                    f"💰 Цена: {order.price:.0f} руб.\n\n"
                    "Едьте к клиенту. Когда подъедете, нажмите 'Подъехал'."
                ),
                parse_mode='HTML',
                reply_markup=Keyboards.driver_after_accept(order.id)
            )
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения водителю: {e}")
        
        # Уведомляем клиента с контактами водителя (единый формат - как в очередях)
        try:
            from bot.utils.keyboards import Keyboards
            customer = db.query(User).filter(User.id == order.customer_id).first()
            if customer:
                print(f"📤 notify_assigned start order={order_id} user={customer.telegram_id}")
                
                # Формируем информацию о машине
                car_info = f"{driver.car_model or 'машина'}"
                if driver.car_color:
                    car_info += f" • {driver.car_color}"
                if driver.car_number:
                    car_info += f" • {driver.car_number}"
                
                # Получаем контактные данные водителя
                username = getattr(driver.user, 'username', None)
                telegram_id = getattr(driver.user, 'telegram_id', None)
                phone = getattr(driver.user, 'phone_number', None)
                
                print(f"Контакты водителя: username={username}, telegram_id={telegram_id}, phone={phone}")
                
                # Формируем сообщение согласно ТЗ (единый формат, с телефоном в тексте)
                message = (
                    "✅ <b>Заказ принят</b>\n\n"
                    f"🚘 <b>Водитель:</b> {driver.user.full_name}\n"
                    f"<b>Авто:</b> {car_info}\n"
                    f"⭐ <b>Рейтинг:</b> {driver.rating:.1f}\n"
                    f"⏱ <b>Подача:</b> ~5-10 мин\n\n"
                    "<b>Связь:</b>\n"
                )
                
                # Добавляем телефон в текст (если есть)
                if phone:
                    message += f"📞 Телефон: <code>{phone}</code>\n"
                
                # Создаем клавиатуру с кнопкой "Написать" (без tel: ссылки)
                contact_keyboard = Keyboards.contact_driver(
                    username=username,
                    telegram_id=telegram_id
                )
                
                try:
                    await bot.send_message(
                        chat_id=customer.telegram_id,
                        text=message,
                        parse_mode='HTML',
                        reply_markup=contact_keyboard
                    )
                    print(f"✅ notify_assigned ok order={order_id} user={customer.telegram_id}")
                except BadRequest as e:
                    # Обработка ошибки приватности водителя
                    if "Button_user_privacy_restricted" in str(e):
                        print(f"⚠️ Button_user_privacy_restricted для заказа {order_id}, отправляем без кнопки")
                        # Пробуем отправить только через username, если он есть
                        if username:
                            fallback_keyboard = Keyboards.contact_driver(
                                username=username,
                                telegram_id=None  # Не используем tg://user?id= если есть username
                            )
                            try:
                                await bot.send_message(
                                    chat_id=customer.telegram_id,
                                    text=message,
                                    parse_mode='HTML',
                                    reply_markup=fallback_keyboard
                                )
                                print(f"✅ notify_assigned ok (fallback username) order={order_id} user={customer.telegram_id}")
                            except Exception as e2:
                                # Если и с username не получилось, отправляем без кнопки
                                print(f"⚠️ Не удалось отправить с username, отправляем без кнопки: {e2}")
                                await bot.send_message(
                                    chat_id=customer.telegram_id,
                                    text=message,
                                    parse_mode='HTML'
                                )
                                print(f"✅ notify_assigned ok (без кнопки) order={order_id} user={customer.telegram_id}")
                        else:
                            # Если username нет, отправляем без кнопки
                            await bot.send_message(
                                chat_id=customer.telegram_id,
                                text=message,
                                parse_mode='HTML'
                            )
                            print(f"✅ notify_assigned ok (без кнопки) order={order_id} user={customer.telegram_id}")
                    else:
                        # Другие BadRequest ошибки - пробрасываем дальше
                        raise
            else:
                print(f"❌ Клиент для заказа {order_id} не найден в БД!")
        except Exception as e:
            print(f"❌ notify_assigned FAILED order={order_id}: {e}")
        
        print(f"✅ Водитель #{driver.id} принял broadcast-заказ #{order_id}")
        return True, "Заказ успешно принят!"
    
    @staticmethod
    async def reserve_broadcast_order(
        db: Session,
        order_id: int,
        driver: Driver,
        bot,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Tuple[bool, str]:
        """
        Занятый водитель резервирует broadcast-заказ
        
        Returns:
            (успех, сообщение)
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            return False, "Заказ не найден"
        
        if order.status != OrderStatus.NEW:
            return False, "Заказ уже принят другим водителем"
        
        if order.reserved_driver_id is not None:
            return False, "Заказ уже зарезервирован другим водителем"
        
        if driver.status != DriverStatus.BUSY:
            return False, "Резервация доступна только для занятых водителей"
        
        # Резервируем заказ
        order.reserved_driver_id = driver.id
        order.reserve_expires_at = datetime.utcnow() + timedelta(minutes=RESERVE_TTL_MINUTES)
        
        db.commit()
        
        # Уведомляем клиента о резервации
        try:
            customer = db.query(User).filter(User.id == order.customer_id).first()
            if customer:
                eta_text = f"≈ {driver.eta_to_finish} мин" if driver.eta_to_finish else "несколько минут"
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "✅ Подтвердить ожидание",
                            callback_data=f"confirm_reserve:{order_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Отменить",
                            callback_data=f"decline_reserve:{order_id}"
                        )
                    ]
                ])
                
                await bot.send_message(
                    chat_id=customer.telegram_id,
                    text=(
                        f"🚗 <b>Водитель готов взять ваш заказ!</b>\n\n"
                        f"Водитель завершит текущую поездку через {eta_text} и сразу заберет вас.\n\n"
                        f"Подтверждаете ожидание?"
                    ),
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
        except Exception as e:
            print(f"❌ Ошибка уведомления клиента о резервации #{order_id}: {e}")
        
        # Примечание: истечение резерва контролируется через поле reserve_expires_at
        # При необходимости можно добавить периодическую проверку истекших резервов
        
        print(f"📌 Водитель #{driver.id} зарезервировал заказ #{order_id}")
        return True, f"Заказ зарезервирован! Завершите текущую поездку ({driver.eta_to_finish} мин)."
    
    # Примечание: таймаут резервов обрабатывается через поле reserve_expires_at в БД
    
    @staticmethod
    async def confirm_reserve(
        db: Session,
        order_id: int,
        bot,
        context: ContextTypes.DEFAULT_TYPE
    ) -> Tuple[bool, str]:
        """
        Клиент подтверждает ожидание зарезервированного водителя
        
        Returns:
            (успех, сообщение)
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order or not order.reserved_driver_id:
            return False, "Резервация не найдена"
        
        driver = db.query(Driver).filter(Driver.id == order.reserved_driver_id).first()
        
        if not driver:
            return False, "Водитель не найден"
        
        # Закрепляем заказ за водителем (но статус остается NEW до завершения текущей поездки)
        order.driver_id = driver.user_id
        order.assigned_driver_id = driver.id
        # Снимаем резерв, но помечаем что клиент подтвердил
        order.reserved_driver_id = None
        order.reserve_expires_at = None
        
        db.commit()
        
        # Примечание: таймеры резервов больше не используются (контроль через reserve_expires_at)
        
        # Уведомляем водителя новым сообщением с актуальными кнопками
        try:
            from bot.utils.keyboards import Keyboards
            await bot.send_message(
                chat_id=driver.user.telegram_id,
                text=(
                    f"✅ <b>Клиент подтвердил ожидание!</b>\n\n"
                    f"📋 <b>Заказ #{order_id}</b>\n\n"
                    f"📍 Откуда: {order.pickup_address}\n"
                    f"📍 Куда: {order.dropoff_address}\n"
                    f"💰 Цена: {order.price:.0f} руб.\n\n"
                    f"⚠️ После завершения текущей поездки нажмите \"Готов к новому заказу\"."
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"❌ Ошибка уведомления водителя о подтверждении резерва #{order_id}: {e}")
        
        print(f"✅ Клиент подтвердил резерв для заказа #{order_id}")
        return True, "Спасибо! Водитель заберет вас после текущей поездки."
    
    @staticmethod
    async def decline_reserve(
        db: Session,
        order_id: int
    ) -> Tuple[bool, str]:
        """
        Клиент отклоняет резервацию
        
        Returns:
            (успех, сообщение)
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            return False, "Заказ не найден"
        
        # Снимаем резерв, возвращаем в общий пул
        order.reserved_driver_id = None
        order.reserve_expires_at = None
        db.commit()
        
        print(f"❌ Клиент отклонил резерв для заказа #{order_id}")
        return True, "Резервация отменена. Продолжаем поиск свободного водителя..."

