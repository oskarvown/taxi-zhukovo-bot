"""
Обработчики команд для администраторов
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.db import SessionLocal
from bot.services import UserService
from bot.services.queue_manager import queue_manager
from bot.models import User, Driver, Order, OrderStatus, UserRole, DriverStatus, DriverZone
from sqlalchemy import func

logger = logging.getLogger(__name__)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика для администратора"""
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    db = SessionLocal()
    try:
        # Подсчет статистики
        total_users = db.query(User).count()
        total_customers = db.query(User).filter(User.role == UserRole.CUSTOMER).count()
        total_drivers = db.query(Driver).count()
        verified_drivers = db.query(Driver).filter(Driver.is_verified == True).count()
        online_drivers = db.query(Driver).filter(Driver.is_online == True).count()
        
        total_orders = db.query(Order).count()
        pending_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING).count()
        completed_orders = db.query(Order).filter(Order.status == OrderStatus.COMPLETED).count()
        
        # Средняя стоимость заказа
        avg_price = db.query(func.avg(Order.price)).filter(Order.status == OrderStatus.COMPLETED).scalar() or 0
        
        stats_text = (
            "📊 <b>Статистика системы</b>\n\n"
            "<b>Пользователи:</b>\n"
            f"👥 Всего: {total_users}\n"
            f"🙋 Клиенты: {total_customers}\n"
            f"🚗 Водители: {total_drivers}\n"
            f"✅ Верифицированные водители: {verified_drivers}\n"
            f"🟢 Онлайн водители: {online_drivers}\n\n"
            "<b>Заказы:</b>\n"
            f"📋 Всего: {total_orders}\n"
            f"⏳ Ожидают: {pending_orders}\n"
            f"✅ Завершено: {completed_orders}\n"
            f"💰 Средний чек: {avg_price:.2f} руб."
        )
        
        await update.message.reply_text(stats_text, parse_mode='HTML')
    finally:
        db.close()


async def admin_verify_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Верификация водителя"""
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Использование: /verify_driver <telegram_id>\n"
            "Пример: /verify_driver 123456789"
        )
        return
    
    try:
        driver_telegram_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Неверный формат Telegram ID")
        return
    
    db = SessionLocal()
    try:
        driver_user = db.query(User).filter(User.telegram_id == driver_telegram_id).first()
        
        if not driver_user:
            await update.message.reply_text("Пользователь не найден")
            return
        
        driver = db.query(Driver).filter(Driver.user_id == driver_user.id).first()
        
        if not driver:
            await update.message.reply_text("Этот пользователь не зарегистрирован как водитель")
            return
        
        driver.is_verified = True
        db.commit()
        
        await update.message.reply_text(
            f"✅ Водитель {driver_user.full_name} верифицирован"
        )
        
        # Уведомляем водителя
        await context.bot.send_message(
            chat_id=driver_telegram_id,
            text="✅ Ваш профиль водителя верифицирован! Теперь вы можете принимать заказы."
        )
    finally:
        db.close()


async def admin_list_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список всех водителей"""
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    db = SessionLocal()
    try:
        drivers = db.query(Driver).all()
        
        if not drivers:
            await update.message.reply_text("Нет зарегистрированных водителей")
            return
        
        drivers_text = "🚗 <b>Список водителей</b>\n\n"
        
        for driver in drivers:
            status = "🟢" if driver.is_online else "🔴"
            verified = "✅" if driver.is_verified else "⏳"
            
            drivers_text += (
                f"{status} {verified} <b>{driver.user.full_name}</b>\n"
                f"ID: {driver.user.telegram_id}\n"
                f"Авто: {driver.car_model} ({driver.car_number})\n"
                f"Рейтинг: {driver.rating:.1f} ({driver.total_rides} поездок)\n\n"
            )
        
        await update.message.reply_text(drivers_text, parse_mode='HTML')
    finally:
        db.close()


async def admin_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список ожидающих заказов"""
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.status == OrderStatus.PENDING).all()
        
        if not orders:
            await update.message.reply_text("Нет ожидающих заказов")
            return
        
        orders_text = "⏳ <b>Ожидающие заказы</b>\n\n"
        
        for order in orders:
            orders_text += f"{order.display_info}\n\n"
        
        await update.message.reply_text(orders_text, parse_mode='HTML')
    finally:
        db.close()


async def admin_check_dema_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Проверить водителей в зоне DEMA
    
    Выводит всех водителей, у которых current_zone = "DEMA"
    """
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    db = SessionLocal()
    try:
        # Находим всех водителей в зоне DEMA
        dema_drivers = db.query(Driver).filter(
            Driver.current_zone == DriverZone.DEMA
        ).all()
        
        if not dema_drivers:
            await update.message.reply_text("✅ В зоне DEMA нет водителей")
            return
        
        from bot.constants import PUBLIC_ZONE_LABELS
        
        message = f"📍 <b>Водители в зоне DEMA (всего: {len(dema_drivers)})</b>\n\n"
        
        online_count = 0
        for driver in dema_drivers:
            status_value = driver.status.value if hasattr(driver.status, 'value') else str(driver.status)
            zone_value = driver.current_zone.value if hasattr(driver.current_zone, 'value') else str(driver.current_zone)
            
            status_emoji = "🟢" if status_value == "online" else "🔴" if status_value == "offline" else "⏳"
            if status_value == "online":
                online_count += 1
            
            driver_name = driver.user.full_name if driver.user else "Неизвестно"
            message += (
                f"{status_emoji} <b>ID {driver.id}</b>: {driver_name}\n"
                f"   Статус: {status_value}\n"
                f"   Зона: {zone_value}\n"
                f"   Online since: {driver.online_since or 'не указано'}\n"
                f"   Авто: {driver.car_model} ({driver.car_number})\n\n"
            )
        
        message += f"🟢 Онлайн водителей: {online_count} из {len(dema_drivers)}"
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(message) > 4000:
            # Отправляем по частям
            parts = message.split("\n\n")
            current_part = ""
            for part in parts:
                if len(current_part + part) > 3500:
                    await update.message.reply_text(current_part, parse_mode='HTML')
                    current_part = part + "\n\n"
                else:
                    current_part += part + "\n\n"
            if current_part:
                await update.message.reply_text(current_part, parse_mode='HTML')
        else:
            await update.message.reply_text(message, parse_mode='HTML')
        
        logger.info(f"Администратор {user.id} проверил водителей в зоне DEMA ({len(dema_drivers)} водителей)")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке водителей в зоне DEMA: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Произошла ошибка:\n{str(e)}")
    finally:
        db.close()


async def admin_reset_drivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Полный сброс состояния всех водителей
    
    Выполняет:
    - Очистку поля online_since
    - Очистку/сброс current_zone на NONE
    - Очистку статуса "на линии" (OFFLINE)
    - Удаление водителей из всех очередей
    
    То есть у всех водителей будет состояние «как будто они ещё не нажимали Я на линии».
    """
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    db = SessionLocal()
    try:
        # Получаем всех водителей
        drivers = db.query(Driver).all()
        
        if not drivers:
            await update.message.reply_text("❌ Нет водителей в системе")
            return
        
        reset_count = 0
        
        # Сначала удаляем всех водителей из очередей
        for driver in drivers:
            # Используем метод полного удаления из всех зон
            queue_manager._remove_driver_from_all_zones(driver.id)
            
            # Сохраняем старую зону для логирования
            old_zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
            old_status = driver.status.value if hasattr(driver.status, 'value') else driver.status
            
            # Сбрасываем состояние водителя
            driver.status = DriverStatus.OFFLINE
            driver.current_zone = DriverZone.NONE
            driver.online_since = None
            driver.pending_order_id = None
            driver.pending_until = None
            
            reset_count += 1
            logger.info(
                f"Сброшен статус водителя {driver.id} (было: status={old_status}, zone={old_zone})"
            )
        
        # Сохраняем изменения в БД
        db.commit()
        
        # Очищаем все очереди в менеджере (используем ZONES вместо keys())
        from bot.constants import ZONES
        queue_manager._queues = {zone: [] for zone in ZONES}
        queue_manager._driver_zones = {}
        
        logger.info(f"Все очереди очищены. Осталось водителей в очередях: {sum(len(q) for q in queue_manager._queues.values())}")
        
        await update.message.reply_text(
            f"✅ <b>Сброс состояния водителей выполнен</b>\n\n"
            f"Обработано водителей: {reset_count}\n\n"
            f"Все водители переведены в статус OFFLINE.\n"
            f"Все очереди очищены.\n\n"
            f"Водители должны заново нажать '🟢 Я на линии', чтобы выйти в очередь.",
            parse_mode='HTML'
        )
        
        logger.info(f"Администратор {user.id} выполнил полный сброс состояния всех водителей ({reset_count} водителей)")
        
    except Exception as e:
        logger.error(f"Ошибка при сбросе состояния водителей: {e}", exc_info=True)
        db.rollback()
        await update.message.reply_text(
            f"❌ Произошла ошибка при сбросе состояния водителей:\n{str(e)}"
        )
    finally:
        db.close()


async def admin_queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показать статус всех очередей по зонам
    
    Показывает для каждой зоны:
    - Количество водителей в очереди
    - Список водителей с позициями, статусами и именами
    """
    user = update.effective_user
    
    if not UserService.is_admin(user.id):
        await update.message.reply_text("У вас нет прав администратора")
        return
    
    db = SessionLocal()
    try:
        from bot.constants import ZONES, PUBLIC_ZONE_LABELS
        
        # Перестраиваем очереди из БД для актуальности
        queue_manager.rebuild_from_db(db)
        
        # Получаем информацию о всех очередях
        queues_info = queue_manager.get_all_queues_info()
        
        # Формируем сообщение
        message_parts = []
        message_parts.append("📊 <b>СТАТУС ОЧЕРЕДЕЙ ПО ЗОНАМ</b>\n")
        message_parts.append("=" * 50 + "\n")
        
        total_online = 0
        zones_with_drivers = 0
        
        # Показываем все зоны, включая пустые
        for zone in ZONES:
            zone_label = PUBLIC_ZONE_LABELS.get(zone, zone)
            queue_info = queues_info[zone]
            driver_ids = queue_info['drivers']
            
            if driver_ids:
                zones_with_drivers += 1
            else:
                # Показываем пустую зону кратко
                message_parts.append(f"\n📍 <b>{zone_label}</b>: ✅ пусто")
                continue
            
            message_parts.append(f"\n📍 <b>{zone_label}</b>")
            message_parts.append(f"👥 В очереди: {len(driver_ids)} водителей\n")
            
            # Получаем информацию о каждом водителе
            for position, driver_id in enumerate(driver_ids, 1):
                driver = db.query(Driver).filter(Driver.id == driver_id).first()
                
                if not driver:
                    message_parts.append(f"  {position}. ⚠️ Водитель {driver_id} (не найден в БД)\n")
                    continue
                
                # Статус водителя
                status_value = driver.status.value if hasattr(driver.status, 'value') else str(driver.status)
                status_emoji = {
                    DriverStatus.ONLINE: "🟢",
                    DriverStatus.OFFLINE: "🔴",
                    DriverStatus.PENDING_ACCEPTANCE: "⏳",
                    DriverStatus.BUSY: "🚗",
                }.get(driver.status, "❓")
                
                driver_name = driver.user.full_name if driver.user else "Неизвестно"
                
                # Время на линии
                online_since_str = ""
                if driver.online_since:
                    from datetime import datetime, timedelta
                    now = datetime.utcnow()
                    diff = now - driver.online_since
                    hours = int(diff.total_seconds() // 3600)
                    minutes = int((diff.total_seconds() % 3600) // 60)
                    if hours > 0:
                        online_since_str = f" ({hours}ч {minutes}м)"
                    else:
                        online_since_str = f" ({minutes}м)"
                
                # Pending заказ
                pending_info = ""
                if driver.pending_order_id:
                    pending_info = " ⏳ (ожидает ответ)"
                
                message_parts.append(
                    f"  {position}. {status_emoji} <b>{driver_name}</b>\n"
                    f"     ID: {driver.id} | Авто: {driver.car_model} {driver.car_number}{pending_info}{online_since_str}\n"
                )
                
                if status_value == "online":
                    total_online += 1
            
            message_parts.append("")  # Пустая строка между зонами
        
        # Итоговая статистика
        message_parts.append("\n" + "=" * 50)
        message_parts.append(f"\n📈 <b>ИТОГО:</b>")
        message_parts.append(f"🟢 Онлайн водителей в очередях: {total_online}")
        message_parts.append(f"📍 Зон с водителями: {zones_with_drivers} из {len(ZONES)}")
        if zones_with_drivers == 0:
            message_parts.append("\n⚠️ Во всех зонах нет водителей в очереди")
        
        full_message = "\n".join(message_parts)
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(full_message) > 4000:
            # Разбиваем по зонам
            parts = []
            current_part = "📊 <b>СТАТУС ОЧЕРЕДЕЙ ПО ЗОНАМ</b>\n" + "=" * 50 + "\n"
            
            for zone in ZONES:
                zone_label = PUBLIC_ZONE_LABELS.get(zone, zone)
                queue_info = queues_info[zone]
                driver_ids = queue_info['drivers']
                
                if not driver_ids:
                    continue
                
                zone_text = f"\n📍 <b>{zone_label}</b>\n👥 В очереди: {len(driver_ids)} водителей\n\n"
                
                for position, driver_id in enumerate(driver_ids, 1):
                    driver = db.query(Driver).filter(Driver.id == driver_id).first()
                    if not driver:
                        continue
                    
                    status_emoji = {
                        DriverStatus.ONLINE: "🟢",
                        DriverStatus.OFFLINE: "🔴",
                        DriverStatus.PENDING_ACCEPTANCE: "⏳",
                        DriverStatus.BUSY: "🚗",
                    }.get(driver.status, "❓")
                    
                    driver_name = driver.user.full_name if driver.user else "Неизвестно"
                    zone_text += f"{position}. {status_emoji} {driver_name} (ID: {driver.id})\n"
                
                # Если текущая часть + зона слишком длинная, отправляем текущую и начинаем новую
                if len(current_part + zone_text) > 3500:
                    parts.append(current_part)
                    current_part = zone_text
                else:
                    current_part += zone_text
                    current_part += "\n"
            
            # Добавляем последнюю часть и итоги
            if current_part:
                parts.append(current_part)
            
            # Отправляем по частям
            for i, part in enumerate(parts, 1):
                if i < len(parts):
                    await update.message.reply_text(
                        part,
                        parse_mode='HTML'
                    )
                else:
                    # В последней части добавляем итоги
                    part += "\n" + "=" * 50
                    part += f"\n📈 <b>ИТОГО:</b> 🟢 Онлайн: {total_online} | Зон: {zones_with_drivers}/{len(ZONES)}"
                    await update.message.reply_text(
                        part,
                        parse_mode='HTML'
                    )
        else:
            await update.message.reply_text(full_message, parse_mode='HTML')
        
        logger.info(f"Администратор {user.id} запросил статус очередей (онлайн: {total_online}, зон: {zones_with_drivers})")
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса очередей: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Произошла ошибка при получении статуса очередей:\n{str(e)}"
        )
    finally:
        db.close()


def register_admin_handlers(application: Application):
    """Регистрация обработчиков для администраторов"""
    
    application.add_handler(CommandHandler('admin_stats', admin_stats))
    application.add_handler(CommandHandler('verify_driver', admin_verify_driver))
    application.add_handler(CommandHandler('list_drivers', admin_list_drivers))
    application.add_handler(CommandHandler('pending_orders', admin_pending_orders))
    application.add_handler(CommandHandler('reset_drivers', admin_reset_drivers))
    application.add_handler(CommandHandler('check_dema', admin_check_dema_drivers))
    application.add_handler(CommandHandler('queue_status', admin_queue_status))

