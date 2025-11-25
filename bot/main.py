"""
Главный файл бота такси Жуково
"""
import logging
import sys
from telegram.ext import Application  # pyright: ignore[reportMissingImports]
from telegram.error import Conflict  # pyright: ignore[reportMissingImports]
from bot.config import settings
from bot.handlers import (
    register_user_handlers,
    register_driver_handlers,
    register_admin_handlers,
    register_auth_handlers,
)
from bot.handlers.broadcast_handlers import register_broadcast_handlers
from bot.middlewares.ban_guard import install_ban_guard
from database.db import init_db, SessionLocal

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level.upper())
)

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Действия после инициализации бота"""
    logger.info("Инициализация системы очередей...")
    
    # Инициализируем диспетчер заказов
    from bot.services.order_dispatcher import init_dispatcher
    init_dispatcher(application.bot)
    logger.info("Order Dispatcher инициализирован")
    
    # Перестраиваем очереди из БД
    from bot.services.queue_manager import queue_manager
    from bot.services.scheduler import scheduler
    db = SessionLocal()
    try:
        queue_manager.rebuild_from_db(db)
        logger.info("Очереди водителей восстановлены из БД")
    finally:
        db.close()
    
    await scheduler.start_warning_cleanup_loop()
    logger.info("Ночная очистка предупреждений активирована")
    
    logger.info("Бот инициализирован и готов к работе")


async def post_shutdown(application: Application) -> None:
    """Действия после остановки бота"""
    logger.info("Остановка системы очередей...")
    
    # Отменяем все активные таймеры
    from bot.services.scheduler import scheduler
    await scheduler.cancel_all()
    
    logger.info("Бот остановлен")


async def error_handler(update, context):
    """Обработчик ошибок"""
    import traceback
    
    # Специальная обработка конфликта (несколько экземпляров бота)
    if isinstance(context.error, Conflict):
        logger.error(
            "⚠️ CONFLICT: Другой экземпляр бота уже запущен!\n"
            "Остановите другой запущенный экземпляр или подождите 1-2 минуты.\n"
            "Эта ошибка будет повторяться, пока не будет остановлен другой экземпляр."
        )
        # Не логируем traceback для Conflict, так как это ожидаемая ошибка
        return
    
    # Логируем остальные ошибки
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    if update:
        logger.error(f"Update: {update}")
    logger.error(
        f"Traceback: {''.join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))}"
    )


def main():
    """Запуск бота"""
    logger.info("Запуск бота такси Жуково...")
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    init_db()
    
    # Создание приложения с правильной регистрацией callbacks
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Регистрация обработчиков
    # ВАЖНО: Сначала регистрируем обработчики водителей, чтобы они имели приоритет
    # над ConversationHandler для пользователей
    logger.info("Регистрация обработчиков...")
    register_auth_handlers(application)
    register_driver_handlers(application)  # Водители ПЕРВЫМИ
    register_user_handlers(application)      # Потом пользователи
    register_admin_handlers(application)
    register_broadcast_handlers(application)
    install_ban_guard(application)
    
    # Регистрация обработчика ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("✅ Бот запущен и работает!")
    try:
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True  # Пропускаем старые обновления при запуске
        )
    except Conflict as e:
        logger.error(
            "❌ CONFLICT: Другой экземпляр бота уже запущен!\n"
            f"Ошибка: {e}\n"
            "Решение:\n"
            "1. Найдите и остановите другой запущенный процесс бота\n"
            "2. Или подождите 1-2 минуты и попробуйте снова\n"
            "3. Проверьте запущенные процессы: ps aux | grep run.py"
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)

