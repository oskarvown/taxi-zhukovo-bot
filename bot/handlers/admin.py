"""
Обработчики команд для администраторов
"""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.db import SessionLocal
from bot.services import UserService
from bot.models import User, Driver, Order, OrderStatus, UserRole
from sqlalchemy import func


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


def register_admin_handlers(application: Application):
    """Регистрация обработчиков для администраторов"""
    
    application.add_handler(CommandHandler('admin_stats', admin_stats))
    application.add_handler(CommandHandler('verify_driver', admin_verify_driver))
    application.add_handler(CommandHandler('list_drivers', admin_list_drivers))
    application.add_handler(CommandHandler('pending_orders', admin_pending_orders))

