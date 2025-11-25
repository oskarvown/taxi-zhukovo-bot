"""
Диспетчер заказов
Управляет распределением заказов по водителям через систему очередей
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from telegram import Bot
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest

from bot.models.order import Order, OrderStatus, OrderZone
from bot.models.driver import Driver, DriverStatus, DriverZone
from bot.services.queue_manager import queue_manager
from bot.services.scheduler import scheduler
from bot.constants import DRIVER_RESPONSE_TIMEOUT, ORDER_GLOBAL_TIMEOUT, PUBLIC_ZONE_LABELS

logger = logging.getLogger(__name__)


class OrderDispatcher:
    """Диспетчер распределения заказов"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def create_and_dispatch_order(self, order_id: int, db: Session):
        """
        Создать заказ и начать процесс распределения
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Заказ {order_id} не найден")
            return
        
        # Устанавливаем статус NEW
        order.status = OrderStatus.NEW
        db.commit()
        
        logger.info(f"Начато распределение заказа {order_id} в зоне {order.zone}")
        
        # Запускаем глобальный таймер 180 секунд
        await scheduler.schedule_order_timeout(
            order_id,
            ORDER_GLOBAL_TIMEOUT,
            lambda oid: self._on_order_global_timeout(oid, db)
        )
        
        # Начинаем первичное распределение
        await self._assign_to_next_driver_in_zone(order_id, db)
    
    async def _assign_to_next_driver_in_zone(self, order_id: int, db: Session):
        """Назначить заказ следующему водителю в зоне заказа"""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        
        # Проверяем что заказ всё ещё в нужном статусе
        if order.status not in [OrderStatus.NEW, OrderStatus.ASSIGNED]:
            logger.info(f"Заказ {order_id} уже не в статусе NEW/ASSIGNED, пропускаем назначение")
            return
        
        # Получаем зону заказа
        zone = order.zone.value if hasattr(order.zone, 'value') else order.zone
        
        # Получаем следующего водителя из очереди
        driver_id = queue_manager.get_next_driver(zone, db)
        
        if not driver_id:
            logger.warning(f"Нет доступных водителей в зоне {zone} для заказа {order_id}")
            # Ждём глобального таймаута
            return
        
        # Назначаем водителю
        await self._assign_to_driver(order_id, driver_id, db)
    
    async def _assign_to_driver(self, order_id: int, driver_id: int, db: Session):
        """Назначить заказ конкретному водителю"""
        order = db.query(Order).filter(Order.id == order_id).first()
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not order or not driver:
            logger.error(f"Заказ {order_id} или водитель {driver_id} не найдены")
            return
        
        # Переводим водителя в pending_acceptance
        driver.status = DriverStatus.PENDING_ACCEPTANCE
        driver.pending_order_id = order_id
        driver.pending_until = datetime.utcnow() + timedelta(seconds=DRIVER_RESPONSE_TIMEOUT)
        
        # Обновляем заказ
        order.status = OrderStatus.ASSIGNED
        order.assigned_driver_id = driver_id
        
        db.commit()
        
        # Удаляем водителя из очереди (временно)
        queue_manager.remove_driver(driver_id)
        
        logger.info(f"Заказ {order_id} назначен водителю {driver_id} ({driver.user.full_name})")
        
        # Отправляем уведомление водителю
        await self._send_order_notification(order, driver)
        
        # Запускаем таймер 30 секунд
        await scheduler.schedule_driver_timeout(
            driver_id,
            order_id,
            DRIVER_RESPONSE_TIMEOUT,
            lambda did, oid: self._on_driver_timeout(did, oid, db)
        )
    
    async def _send_order_notification(self, order: Order, driver: Driver):
        """Отправить уведомление водителю о новом заказе"""
        try:
            zone_label = PUBLIC_ZONE_LABELS.get(order.zone.value if hasattr(order.zone, 'value') else order.zone, order.zone)
            
            message = (
                f"🚖 <b>НОВЫЙ ЗАКАЗ #{order.id}</b>\n\n"
                f"🏘 <b>Район:</b> {zone_label}\n"
                f"📍 <b>Откуда:</b> {order.pickup_address}\n"
                f"📍 <b>Куда:</b> {order.dropoff_address}\n"
                f"💰 <b>Цена:</b> {order.price:.0f} руб.\n\n"
                f"⏱ <b>У вас {DRIVER_RESPONSE_TIMEOUT} секунд для ответа</b>"
            )
            
            if order.customer_comment:
                message += f"\n💬 <b>Комментарий:</b> {order.customer_comment}"
            
            # Кнопки принять/отклонить
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Принять", callback_data=f"order_accept:{order.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"order_decline:{order.id}")
                ]
            ])
            
            await self.bot.send_message(
                driver.user.telegram_id,
                message,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            logger.info(f"Уведомление о заказе {order.id} отправлено водителю {driver.id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления водителю {driver.id}: {e}", exc_info=True)
    
    async def _on_driver_timeout(self, driver_id: int, order_id: int, db: Session):
        """Обработка таймаута водителя (30 секунд истекли без ответа)"""
        logger.info(f"Таймаут водителя {driver_id} для заказа {order_id}")
        
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not driver or not order:
            return
        
        # Проверяем что заказ всё ещё назначен этому водителю
        if order.assigned_driver_id != driver_id:
            logger.debug(f"Заказ {order_id} уже не назначен водителю {driver_id}")
            return
        
        # Возвращаем водителя онлайн и в хвост очереди
        driver.status = DriverStatus.ONLINE
        driver.pending_order_id = None
        driver.pending_until = None
        driver.online_since = datetime.utcnow()  # Обновляем время (идёт в хвост)
        db.commit()
        
        # Добавляем обратно в очередь
        zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
        queue_manager.add_driver(driver_id, zone, db)
        
        logger.info(f"Водитель {driver_id} возвращён в очередь {zone}")
        
        # Уведомляем водителя
        try:
            await self.bot.send_message(
                driver.user.telegram_id,
                "⏱ <b>Время на ответ истекло.</b>\n\nВы вернулись в конец очереди.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления водителю {driver_id}: {e}")
        
        # Назначаем следующему водителю
        await self._assign_to_next_driver_in_zone(order_id, db)
    
    async def _on_order_global_timeout(self, order_id: int, db: Session):
        """Обработка глобального таймаута заказа (180 секунд) → fallback"""
        logger.info(f"Глобальный таймаут заказа {order_id} → переход в fallback")
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        
        # Проверяем что заказ не принят
        if order.status == OrderStatus.ACCEPTED:
            logger.info(f"Заказ {order_id} уже принят, fallback не требуется")
            return
        
        # Переводим в fallback
        order.status = OrderStatus.FALLBACK
        db.commit()
        
        logger.info(f"Заказ {order_id} переведён в режим fallback (поиск по всем зонам)")
        
        # Начинаем поиск по всем зонам
        await self._fallback_search(order_id, db)
    
    async def _fallback_search(self, order_id: int, db: Session):
        """Поиск водителя по всем зонам (fallback режим)"""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        
        # Получаем всех онлайн водителей из всех зон
        driver_ids = queue_manager.get_all_online_drivers(db)
        
        if not driver_ids:
            logger.warning(f"Нет доступных водителей для fallback заказа {order_id}")
            order.status = OrderStatus.EXPIRED
            db.commit()
            
            # Уведомляем клиента
            try:
                await self.bot.send_message(
                    order.customer.telegram_id,
                    "😔 <b>К сожалению, сейчас нет доступных водителей.</b>\n\n"
                    "Попробуйте создать заказ позже.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления клиенту: {e}")
            
            return
        
        # Назначаем первому доступному водителю
        await self._assign_to_driver(order_id, driver_ids[0], db)
    
    async def handle_driver_accept(self, driver_id: int, order_id: int, db: Session):
        """Обработка принятия заказа водителем"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not driver or not order:
            logger.error(f"Водитель {driver_id} или заказ {order_id} не найдены")
            return False
        
        # Проверяем что заказ назначен этому водителю
        if order.assigned_driver_id != driver_id:
            logger.warning(f"Заказ {order_id} не назначен водителю {driver_id}")
            return False
        
        # Отменяем таймеры (безопасно - если таймеров нет, это не ошибка)
        try:
            await scheduler.cancel_driver_timeout(driver_id)
        except Exception as e:
            logger.warning(f"Ошибка при отмене таймера водителя {driver_id}: {e}")
        
        try:
            await scheduler.cancel_order_timeout(order_id)
        except Exception as e:
            logger.warning(f"Ошибка при отмене таймера заказа {order_id}: {e}")
        
        # Обновляем статусы
        driver.status = DriverStatus.BUSY
        driver.pending_order_id = None
        driver.pending_until = None
        
        order.status = OrderStatus.ACCEPTED
        order.driver_id = driver.user_id
        order.accepted_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ handle_accept saved order={order_id} assigned_driver={driver_id} status={order.status.value}")
        
        # Уведомляем клиента с контактами водителя (единый формат для всех типов заказов)
        try:
            from bot.utils.keyboards import Keyboards
            from bot.models.user import User
            
            # Получаем клиента из БД (избегаем lazy loading)
            customer = db.query(User).filter(User.id == order.customer_id).first()
            if not customer:
                logger.error(f"❌ Клиент для заказа {order_id} не найден в БД!")
                return True
            
            logger.info(f"📤 notify_assigned start order={order_id} user={customer.telegram_id}")
            
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
            
            logger.info(f"Контакты водителя: username={username}, telegram_id={telegram_id}, phone={phone}")
            
            # Формируем сообщение согласно ТЗ (с телефоном в тексте)
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
                await self.bot.send_message(
                    customer.telegram_id,
                    message,
                    parse_mode="HTML",
                    reply_markup=contact_keyboard
                )
                logger.info(f"✅ notify_assigned ok order={order_id} user={customer.telegram_id}")
            except BadRequest as e:
                # Обработка ошибки приватности водителя
                if "Button_user_privacy_restricted" in str(e):
                    logger.warning(f"⚠️ Button_user_privacy_restricted для заказа {order_id}, отправляем без кнопки")
                    # Пробуем отправить только через username, если он есть
                    if username:
                        fallback_keyboard = Keyboards.contact_driver(
                            username=username,
                            telegram_id=None  # Не используем tg://user?id= если есть username
                        )
                        try:
                            await self.bot.send_message(
                                customer.telegram_id,
                                message,
                                parse_mode="HTML",
                                reply_markup=fallback_keyboard
                            )
                            logger.info(f"✅ notify_assigned ok (fallback username) order={order_id} user={customer.telegram_id}")
                        except Exception as e2:
                            # Если и с username не получилось, отправляем без кнопки
                            logger.warning(f"⚠️ Не удалось отправить с username, отправляем без кнопки: {e2}")
                            await self.bot.send_message(
                                customer.telegram_id,
                                message,
                                parse_mode="HTML"
                            )
                            logger.info(f"✅ notify_assigned ok (без кнопки) order={order_id} user={customer.telegram_id}")
                    else:
                        # Если username нет, отправляем без кнопки
                        await self.bot.send_message(
                            customer.telegram_id,
                            message,
                            parse_mode="HTML"
                        )
                        logger.info(f"✅ notify_assigned ok (без кнопки) order={order_id} user={customer.telegram_id}")
                else:
                    # Другие BadRequest ошибки - пробрасываем дальше
                    raise
            
        except Exception as e:
            logger.error(f"❌ notify_assigned FAILED order={order_id}: {e}", exc_info=True)
        
        return True
    
    async def handle_driver_decline(self, driver_id: int, order_id: int, db: Session):
        """Обработка отклонения заказа водителем"""
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not driver or not order:
            logger.error(f"Водитель {driver_id} или заказ {order_id} не найдены")
            return False
        
        # Проверяем что заказ назначен этому водителю
        if order.assigned_driver_id != driver_id:
            logger.warning(f"Заказ {order_id} не назначен водителю {driver_id}")
            return False
        
        # Отменяем таймер водителя
        await scheduler.cancel_driver_timeout(driver_id)
        
        # Возвращаем водителя онлайн в хвост очереди
        driver.status = DriverStatus.ONLINE
        driver.pending_order_id = None
        driver.pending_until = None
        driver.online_since = datetime.utcnow()
        
        db.commit()
        
        # Добавляем обратно в очередь
        zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
        queue_manager.add_driver(driver_id, zone, db)
        
        logger.info(f"Водитель {driver_id} отклонил заказ {order_id}, возвращён в очередь {zone}")
        
        # Назначаем следующему водителю
        if order.status == OrderStatus.FALLBACK:
            await self._fallback_search(order_id, db)
        else:
            await self._assign_to_next_driver_in_zone(order_id, db)
        
        return True


# Функция для получения экземпляра диспетчера (будет инициализирован в main.py)
_dispatcher: Optional[OrderDispatcher] = None

def init_dispatcher(bot: Bot):
    """Инициализировать диспетчер"""
    global _dispatcher
    _dispatcher = OrderDispatcher(bot)
    logger.info("Order Dispatcher инициализирован")

def get_dispatcher() -> OrderDispatcher:
    """Получить экземпляр диспетчера"""
    if _dispatcher is None:
        raise RuntimeError("Order Dispatcher не инициализирован. Вызовите init_dispatcher() сначала.")
    return _dispatcher

