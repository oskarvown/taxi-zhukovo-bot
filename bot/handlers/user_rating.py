"""
Обработчики оценки поездки для клиента
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from database.db import SessionLocal
from bot.services.user_service import UserService
from bot.services.order_service import OrderService
from bot.models.user import UserRole
from bot.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)

# Состояния для диалога комментария
WAITING_FOR_COMMENT = 1


async def rate_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка оценки заказа клиентом"""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    
    try:
        # Парсим callback data: rate:{order_id}:{rating}
        _, order_id, rating_str = query.data.split(":")
        order_id = int(order_id)
        rating = int(rating_str)
        
        if rating < 1 or rating > 5:
            await query.answer("Оценка должна быть от 1 до 5", show_alert=True)
            return
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            await query.edit_message_text("❌ Заказ не найден")
            return
        
        # Проверяем что заказ принадлежит этому клиенту
        if order.customer_id != db_user.id:
            await query.edit_message_text("❌ Этот заказ не принадлежит вам")
            return
        
        # Проверяем что заказ завершен
        if order.status not in [OrderStatus.FINISHED, OrderStatus.COMPLETED]:
            await query.edit_message_text("❌ Заказ еще не завершен")
            return
        
        # Сохраняем оценку
        OrderService.set_rating(db, order, rating)
        
        # Отменяем таймер автовозврата в главное меню (если он был запущен)
        job_name = f"main_menu_timer_{order_id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in current_jobs:
            job.schedule_removal()
            logger.info(f"Таймер главного меню {job_name} отменён (клиент поставил оценку)")
        
        # Обновляем сообщение
        await query.edit_message_text(
            f"✅ <b>Спасибо за оценку!</b>\n\n"
            f"Вы оценили поездку на {rating} {'⭐' * rating}\n\n"
            f"Хотите оставить комментарий?",
            parse_mode='HTML',
            reply_markup=None
        )
        
        # Предлагаем оставить комментарий
        from bot.utils.keyboards import Keyboards
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        comment_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Оставить комментарий", callback_data=f"rate_comment:{order_id}")],
            [InlineKeyboardButton("❌ Пропустить", callback_data=f"rate_skip_comment:{order_id}")]
        ])
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Хотите оставить комментарий к поездке?",
            reply_markup=comment_keyboard
        )
        
        logger.info(f"Клиент {db_user.id} оценил заказ {order_id} на {rating} звезд")
        
    except Exception as e:
        logger.error(f"Ошибка при оценке заказа: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка при оценке")
    finally:
        db.close()


async def rate_comment_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало ввода комментария к оценке"""
    query = update.callback_query
    await query.answer()
    
    try:
        _, order_id = query.data.split(":")
        order_id = int(order_id)
        
        context.user_data['rating_order_id'] = order_id
        
        await query.edit_message_text(
            "✍️ <b>Оставьте комментарий к поездке</b>\n\n"
            "Напишите ваш отзыв или нажмите 'Пропустить'",
            parse_mode='HTML'
        )
        
        from bot.utils.keyboards import Keyboards
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Введите ваш комментарий:",
            reply_markup=Keyboards.cancel_action()
        )
        
        return WAITING_FOR_COMMENT
        
    except Exception as e:
        logger.error(f"Ошибка при начале ввода комментария: {e}", exc_info=True)
        return ConversationHandler.END


async def rate_comment_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получен комментарий к оценке"""
    # Проверяем, что это не команда водителя
    if update.message.text in ["🟢 Я на линии", "🔴 Я оффлайн", "📋 Мои заказы", "📊 Статистика"]:
        return ConversationHandler.END
    
    db = SessionLocal()
    
    try:
        order_id = context.user_data.get('rating_order_id')
        if not order_id:
            # Не показываем ошибку, просто завершаем ConversationHandler
            return ConversationHandler.END
        
        comment = update.message.text
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return ConversationHandler.END
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.customer_id != db_user.id:
            await update.message.reply_text("❌ Заказ не найден")
            return ConversationHandler.END
        
        # Обновляем комментарий (оценка уже была сохранена ранее)
        order.rating_comment = comment
        if comment:
            order.feedback = comment
        db.commit()
        
        await update.message.reply_text(
            "✅ <b>Комментарий сохранен!</b>\n\n"
            "Спасибо за ваш отзыв!",
            parse_mode='HTML',
            reply_markup=None
        )
        
        # Отправляем главное меню клиенту
        from bot.utils.keyboards import Keyboards
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Главное меню 👇",
                reply_markup=Keyboards.main_user()
            )
        except Exception as e:
            logger.error(f"Ошибка отправки главного меню клиенту: {e}", exc_info=True)
        
        logger.info(f"Клиент {db_user.id} оставил комментарий к заказу {order_id}")
        
        # Очищаем данные
        context.user_data.pop('rating_order_id', None)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении комментария: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка")
        return ConversationHandler.END
    finally:
        db.close()


async def rate_skip_comment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить комментарий"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "✅ <b>Спасибо за оценку!</b>\n\n"
        "Ваша оценка учтена.",
        parse_mode='HTML'
    )
    
    # Отправляем главное меню клиенту
    from bot.utils.keyboards import Keyboards
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Главное меню 👇",
            reply_markup=Keyboards.main_user()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки главного меню клиенту: {e}", exc_info=True)
    
    # Очищаем данные
    context.user_data.pop('rating_order_id', None)
    
    return ConversationHandler.END


async def client_coming_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Клиент выходит к водителю"""
    query = update.callback_query
    await query.answer("Водитель уведомлен, что вы выходите")
    
    db = SessionLocal()
    
    try:
        _, order_id = query.data.split(":")
        order_id = int(order_id)
        
        user = update.effective_user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            return
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.customer_id != db_user.id:
            return
        
        # Уведомляем водителя
        if order.driver_id:
            try:
                driver_user = db.query(db_user.__class__).filter(db_user.__class__.id == order.driver_id).first()
                if driver_user:
                    await context.bot.send_message(
                        driver_user.telegram_id,
                        "🚶 <b>Клиент выходит</b>\n\n"
                        "Клиент сообщил, что выходит к месту подачи.",
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления водителю: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выхода клиента: {e}", exc_info=True)
    finally:
        db.close()


async def client_cancel_arrived_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Клиент отменяет после подъезда водителя"""
    query = update.callback_query
    await query.answer("Отмена зафиксирована")
    
    # Просто подтверждаем действие, без дополнительной логики
    # (можно добавить статистику ожидания)


def register_rating_handlers(application):
    """Регистрация обработчиков оценки"""
    # Обработчик оценки
    application.add_handler(
        CallbackQueryHandler(rate_order_callback, pattern='^rate:\d+:[1-5]$')
    )
    
    # Обработчик начала комментария
    application.add_handler(
        CallbackQueryHandler(rate_comment_start_callback, pattern='^rate_comment:\d+$')
    )
    
    # Обработчик пропуска комментария
    application.add_handler(
        CallbackQueryHandler(rate_skip_comment_callback, pattern='^rate_skip_comment:\d+$')
    )
    
    # Диалог ввода комментария
    # Исключаем команды водителей и кнопки пользователей из перехвата
    excluded_commands = [
        '🟢 Я на линии', '🔴 Я оффлайн', '📋 Мои заказы', '📊 Статистика',
        '📍 Новое Жуково', '📍 Старое Жуково', '📍 Мысовцево', '📍 Авдон', '📍 Уптино', '📍 Дёма', '🔙 Назад',
        '📍 Мой заказ', '📋 Мои заказы', 'ℹ️ Помощь', '💵 Тарифы', '📞 Связаться',
        '📜 Правила пользования', '🛣 Межгород', '🔙 В главное меню', '🚖 Заказать такси'
    ]
    driver_commands_filter = ~filters.Regex(f'^({"|".join(excluded_commands)})$')
    comment_conv = ConversationHandler(
        entry_points=[],  # Убираем entry_points, чтобы не перехватывать сообщения
        states={
            WAITING_FOR_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & driver_commands_filter, rate_comment_received),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex('^❌ Отмена$'), lambda u, c: ConversationHandler.END),
            # Завершаем разговор при нажатии на кнопки меню
            MessageHandler(filters.Regex('^(📍 Мой заказ|📋 Мои заказы|ℹ️ Помощь|💵 Тарифы|📞 Связаться|📜 Правила пользования|🛣 Межгород|🔙 В главное меню|🚖 Заказать такси)$'), 
                          lambda u, c: ConversationHandler.END)
        ],
    )
    application.add_handler(comment_conv)
    
    # Обработчик "Выхожу"
    application.add_handler(
        CallbackQueryHandler(client_coming_callback, pattern='^client_coming:\d+$')
    )
    
    # Обработчик отмены после подъезда
    application.add_handler(
        CallbackQueryHandler(client_cancel_arrived_callback, pattern='^client_cancel_arrived:\d+$')
    )

