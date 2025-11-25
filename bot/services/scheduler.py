"""
Планировщик таймеров для системы очередей
Управляет 30-секундными таймерами водителей и 180-секундным таймером заказов
"""
import asyncio
import logging
from typing import Dict, Optional, Callable, Awaitable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Scheduler:
    """Планировщик задач с поддержкой отмены"""
    
    def __init__(self):
        # Таймеры водителей: {driver_id: task}
        self._driver_tasks: Dict[int, asyncio.Task] = {}
        # Таймеры заказов: {order_id: task}
        self._order_tasks: Dict[int, asyncio.Task] = {}
        self._warning_cleanup_task: Optional[asyncio.Task] = None
    
    async def schedule_driver_timeout(
        self,
        driver_id: int,
        order_id: int,
        timeout_seconds: int,
        callback: Callable[[int, int], Awaitable[None]]
    ):
        """
        Запланировать таймаут для водителя (30 секунд)
        callback(driver_id, order_id) будет вызван при истечении времени
        """
        # Отменяем предыдущий таймер если есть
        await self.cancel_driver_timeout(driver_id)
        
        async def timeout_task():
            try:
                logger.info(f"Запущен таймер для водителя {driver_id} (заказ {order_id}): {timeout_seconds}s")
                await asyncio.sleep(timeout_seconds)
                logger.info(f"Таймаут водителя {driver_id} истёк для заказа {order_id}")
                await callback(driver_id, order_id)
            except asyncio.CancelledError:
                logger.debug(f"Таймер водителя {driver_id} отменён")
            except Exception as e:
                logger.error(f"Ошибка в таймере водителя {driver_id}: {e}", exc_info=True)
            finally:
                # Удаляем из списка задач
                if driver_id in self._driver_tasks:
                    del self._driver_tasks[driver_id]
        
        task = asyncio.create_task(timeout_task())
        self._driver_tasks[driver_id] = task
        logger.debug(f"Таймер водителя {driver_id} создан")
    
    async def cancel_driver_timeout(self, driver_id: int) -> bool:
        """Отменить таймер водителя"""
        if driver_id not in self._driver_tasks:
            logger.debug(f"Таймер водителя {driver_id} не найден (уже отменён или не был создан)")
            return False
        
        task = self._driver_tasks[driver_id]
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Безопасное удаление - проверяем что ключ все еще есть
        if driver_id in self._driver_tasks:
            del self._driver_tasks[driver_id]
            logger.debug(f"Таймер водителя {driver_id} отменён")
        return True
    
    async def schedule_order_timeout(
        self,
        order_id: int,
        timeout_seconds: int,
        callback: Callable[[int], Awaitable[None]]
    ):
        """
        Запланировать глобальный таймаут заказа (180 секунд)
        callback(order_id) будет вызван при истечении времени
        """
        # Отменяем предыдущий таймер если есть
        await self.cancel_order_timeout(order_id)
        
        async def timeout_task():
            try:
                logger.info(f"Запущен глобальный таймер для заказа {order_id}: {timeout_seconds}s")
                await asyncio.sleep(timeout_seconds)
                logger.info(f"Глобальный таймаут заказа {order_id} истёк → переход в fallback")
                await callback(order_id)
            except asyncio.CancelledError:
                logger.debug(f"Глобальный таймер заказа {order_id} отменён")
            except Exception as e:
                logger.error(f"Ошибка в глобальном таймере заказа {order_id}: {e}", exc_info=True)
            finally:
                # Удаляем из списка задач
                if order_id in self._order_tasks:
                    del self._order_tasks[order_id]
        
        task = asyncio.create_task(timeout_task())
        self._order_tasks[order_id] = task
        logger.debug(f"Глобальный таймер заказа {order_id} создан")
    
    async def cancel_order_timeout(self, order_id: int) -> bool:
        """Отменить глобальный таймер заказа"""
        if order_id not in self._order_tasks:
            logger.debug(f"Таймер заказа {order_id} не найден (уже отменён или не был создан)")
            return False
        
        task = self._order_tasks[order_id]
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Безопасное удаление - проверяем что ключ все еще есть
        if order_id in self._order_tasks:
            del self._order_tasks[order_id]
            logger.debug(f"Глобальный таймер заказа {order_id} отменён")
        return True
    
    def has_driver_timeout(self, driver_id: int) -> bool:
        """Проверить есть ли активный таймер у водителя"""
        return driver_id in self._driver_tasks and not self._driver_tasks[driver_id].done()
    
    def has_order_timeout(self, order_id: int) -> bool:
        """Проверить есть ли активный глобальный таймер у заказа"""
        return order_id in self._order_tasks and not self._order_tasks[order_id].done()
    
    async def cancel_all(self):
        """Отменить все таймеры (при остановке бота)"""
        logger.info("Отмена всех таймеров...")
        
        # Отменяем таймеры водителей
        for driver_id in list(self._driver_tasks.keys()):
            await self.cancel_driver_timeout(driver_id)
        
        # Отменяем таймеры заказов
        for order_id in list(self._order_tasks.keys()):
            await self.cancel_order_timeout(order_id)

        # Останавливаем ночной джоб
        if self._warning_cleanup_task and not self._warning_cleanup_task.done():
            self._warning_cleanup_task.cancel()
            try:
                await self._warning_cleanup_task
            except asyncio.CancelledError:
                pass
            self._warning_cleanup_task = None

        logger.info("Все таймеры отменены")
    
    def get_stats(self) -> Dict:
        """Получить статистику активных таймеров"""
        return {
            "active_driver_timeouts": len([t for t in self._driver_tasks.values() if not t.done()]),
            "active_order_timeouts": len([t for t in self._order_tasks.values() if not t.done()]),
            "total_driver_tasks": len(self._driver_tasks),
            "total_order_tasks": len(self._order_tasks),
        }

    async def start_warning_cleanup_loop(self):
        """Запустить ночную очистку предупреждений"""
        if self._warning_cleanup_task and not self._warning_cleanup_task.done():
            return
        self._warning_cleanup_task = asyncio.create_task(self._warning_cleanup_worker())
        logger.info("Ночная очистка предупреждений запущена")

    async def _warning_cleanup_worker(self):
        """Фоновая задача очистки предупреждений"""
        while True:
            try:
                seconds = self._seconds_until_hour(3)
                await asyncio.sleep(seconds)
                await self.run_warning_cleanup_once()
            except asyncio.CancelledError:
                logger.info("Задача очистки предупреждений остановлена")
                break
            except Exception as exc:
                logger.error("Ошибка nightly cleanup: %s", exc, exc_info=True)
                await asyncio.sleep(60)

    async def run_warning_cleanup_once(self) -> int:
        """Очистить просроченные предупреждения вручную"""
        from database.db import SessionLocal  # локальный импорт чтобы избежать циклов
        from bot.services.user_penalty_service import UserPenaltyService

        loop = asyncio.get_running_loop()

        def _cleanup():
            db = SessionLocal()
            try:
                return UserPenaltyService.clear_expired_warnings(db)
            finally:
                db.close()

        cleared = await loop.run_in_executor(None, _cleanup)
        logger.info("[scheduler] cleared %s expired warnings", cleared)
        return cleared

    @staticmethod
    def _seconds_until_hour(hour: int) -> float:
        """Количество секунд до следующего указанного часа (UTC)"""
        now = datetime.utcnow()
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()


# Глобальный экземпляр планировщика
scheduler = Scheduler()

