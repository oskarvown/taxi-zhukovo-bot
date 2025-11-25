"""
Менеджер очередей водителей
Управляет ZoneQueue для каждой зоны
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict
from collections import defaultdict

from sqlalchemy.orm import Session
from bot.models.driver import Driver, DriverStatus, DriverZone
from bot.constants import ZONES

logger = logging.getLogger(__name__)


class QueueManager:
    """Менеджер очередей водителей по зонам"""
    
    def __init__(self):
        # Очереди для каждой зоны: {zone: [driver_id, ...]} (упорядочены по online_since)
        self._queues: Dict[str, List[int]] = {zone: [] for zone in ZONES}
        # Кеш: {driver_id: zone} для быстрого поиска
        self._driver_zones: Dict[int, str] = {}
    
    def rebuild_from_db(self, db: Session):
        """Перестроить очереди из БД (при старте бота)"""
        logger.info("Перестройка очередей из БД...")
        
        # Очищаем текущие очереди
        self._queues = {zone: [] for zone in ZONES}
        self._driver_zones = {}
        
        # Получаем всех онлайн водителей
        drivers = db.query(Driver).filter(
            Driver.status == DriverStatus.ONLINE,
            Driver.current_zone.in_(ZONES)
        ).order_by(Driver.online_since).all()
        
        logger.info(f"Найдено {len(drivers)} онлайн водителей в БД")
        
        # Добавляем в очереди
        for driver in drivers:
            zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
            if zone in ZONES:
                # Пропускаем водителей с pending_order_id
                if driver.pending_order_id is None:
                    self._queues[zone].append(driver.id)
                    self._driver_zones[driver.id] = zone
                    logger.debug(f"Водитель {driver.id} ({driver.user.full_name if driver.user else 'unknown'}) добавлен в очередь {zone}")
                else:
                    logger.debug(f"Водитель {driver.id} пропущен (pending_order_id={driver.pending_order_id})")
            else:
                logger.warning(f"Водитель {driver.id} имеет недопустимую зону: {zone}")
        
        logger.info(f"Очереди перестроены. Активных водителей: {len(self._driver_zones)}")
        for zone, queue in self._queues.items():
            if queue:
                logger.info(f"  {zone}: {len(queue)} водителей {queue}")
    
    def _rebuild_zone_from_db(self, zone: str, db: Session):
        """Перестроить очередь для одной зоны из БД"""
        if zone not in ZONES:
            return
        
        logger.info(f"Перестройка очереди зоны {zone} из БД...")
        
        # Очищаем очередь для этой зоны
        old_drivers = self._queues[zone][:]
        for driver_id in old_drivers:
            if self._driver_zones.get(driver_id) == zone:
                del self._driver_zones[driver_id]
        self._queues[zone] = []
        
        # Получаем всех онлайн водителей в этой зоне
        drivers = db.query(Driver).filter(
            Driver.status == DriverStatus.ONLINE,
            Driver.current_zone == zone,
            Driver.pending_order_id.is_(None)
        ).order_by(Driver.online_since).all()
        
        logger.info(f"Найдено {len(drivers)} водителей в зоне {zone} в БД")
        
        # Добавляем в очередь
        for driver in drivers:
            self._queues[zone].append(driver.id)
            self._driver_zones[driver.id] = zone
            logger.info(f"Водитель {driver.id} ({driver.user.full_name if driver.user else 'unknown'}) добавлен в очередь {zone}")
    
    def add_driver(self, driver_id: int, zone: str, db: Session):
        """Добавить водителя в очередь зоны"""
        if zone not in ZONES:
            logger.warning(f"Попытка добавить водителя {driver_id} в неизвестную зону {zone}")
            return
        
        # Удаляем из старой зоны если есть
        self.remove_driver(driver_id)
        
        # Добавляем в хвост новой очереди
        self._queues[zone].append(driver_id)
        self._driver_zones[driver_id] = zone
        
        logger.info(f"Водитель {driver_id} добавлен в очередь {zone} (позиция {len(self._queues[zone])})")
    
    def remove_driver(self, driver_id: int):
        """Удалить водителя из очереди"""
        if driver_id not in self._driver_zones:
            return
        
        zone = self._driver_zones[driver_id]
        if driver_id in self._queues[zone]:
            self._queues[zone].remove(driver_id)
            logger.info(f"Водитель {driver_id} удалён из очереди {zone}")
        
        del self._driver_zones[driver_id]
    
    def get_next_driver(self, zone: str, db: Session) -> Optional[int]:
        """
        Получить следующего водителя из очереди зоны
        Возвращает driver_id или None
        """
        if zone not in ZONES:
            logger.warning(f"Попытка получить водителя из неизвестной зоны {zone}")
            return None
        
        queue = self._queues[zone]
        logger.info(f"Поиск водителя в зоне {zone}, в очереди {len(queue)} водителей: {queue}")
        
        if not queue:
            logger.warning(f"Очередь зоны {zone} пуста! Перестраиваем очередь из БД...")
            # Пытаемся перестроить очередь для этой зоны
            self._rebuild_zone_from_db(zone, db)
            queue = self._queues[zone]
            logger.info(f"После перестройки в очереди {len(queue)} водителей: {queue}")
            
            # Если все еще пусто, проверяем все зоны - может водитель в другой зоне
            if not queue:
                logger.warning(f"В зоне {zone} все еще нет водителей. Проверяем все зоны...")
                all_drivers = db.query(Driver).filter(
                    Driver.status == DriverStatus.ONLINE,
                    Driver.current_zone.in_(ZONES),
                    Driver.pending_order_id.is_(None)
                ).all()
                
                logger.info(f"Всего онлайн водителей во всех зонах: {len(all_drivers)}")
                for driver in all_drivers:
                    driver_zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
                    logger.info(f"  Водитель {driver.id}: зона={driver_zone}, status={driver.status}, pending={driver.pending_order_id}")
        
        # Проходим по очереди и ищем первого доступного
        for driver_id in queue[:]:  # копия списка для безопасной итерации
            driver = db.query(Driver).filter(Driver.id == driver_id).first()
            
            if not driver:
                # Водитель удалён из БД
                logger.warning(f"Водитель {driver_id} не найден в БД, удаляем из очереди")
                self.remove_driver(driver_id)
                continue
            
            # Проверяем что водитель всё ещё онлайн и в этой зоне
            driver_zone = driver.current_zone.value if hasattr(driver.current_zone, 'value') else driver.current_zone
            
            logger.debug(f"Проверка водителя {driver_id}: status={driver.status}, zone={driver_zone}, pending_order_id={driver.pending_order_id}")
            
            if (driver.status == DriverStatus.ONLINE and 
                driver_zone == zone and
                driver.pending_order_id is None):
                logger.info(f"Следующий водитель для зоны {zone}: {driver_id}")
                return driver_id
            else:
                # Водитель больше не подходит, удаляем из очереди
                reason = []
                if driver.status != DriverStatus.ONLINE:
                    reason.append(f"status={driver.status}")
                if driver_zone != zone:
                    reason.append(f"zone={driver_zone} (ожидалось {zone})")
                if driver.pending_order_id is not None:
                    reason.append(f"pending_order_id={driver.pending_order_id}")
                
                logger.warning(f"Водитель {driver_id} ({driver.user.full_name if driver.user else 'unknown'}) больше не подходит: {', '.join(reason)}")
                self.remove_driver(driver_id)
        
        logger.warning(f"Нет доступных водителей в зоне {zone} после проверки всей очереди")
        return None
    
    def get_all_online_drivers(self, db: Session) -> List[int]:
        """
        Получить всех онлайн водителей из всех зон
        Отсортированы по online_since (для fallback)
        """
        drivers = db.query(Driver).filter(
            Driver.status == DriverStatus.ONLINE,
            Driver.current_zone.in_(ZONES),
            Driver.pending_order_id.is_(None)
        ).order_by(Driver.online_since).all()
        
        driver_ids = [d.id for d in drivers]
        logger.info(f"Всего онлайн водителей во всех зонах: {len(driver_ids)}")
        return driver_ids
    
    def switch_zone(self, driver_id: int, new_zone: str, db: Session):
        """Переместить водителя в другую зону"""
        if new_zone not in ZONES:
            logger.warning(f"Попытка переместить водителя {driver_id} в неизвестную зону {new_zone}")
            return
        
        old_zone = self._driver_zones.get(driver_id)
        if old_zone == new_zone:
            logger.debug(f"Водитель {driver_id} уже в зоне {new_zone}")
            return
        
        # Удаляем из старой зоны
        self.remove_driver(driver_id)
        
        # Добавляем в новую зону
        self.add_driver(driver_id, new_zone, db)
        
        logger.info(f"Водитель {driver_id} переведён из зоны {old_zone} в {new_zone}")
    
    def get_queue_position(self, driver_id: int) -> Optional[int]:
        """Получить позицию водителя в очереди (1-based)"""
        if driver_id not in self._driver_zones:
            return None
        
        zone = self._driver_zones[driver_id]
        try:
            position = self._queues[zone].index(driver_id) + 1
            return position
        except ValueError:
            return None
    
    def get_queue_info(self, zone: str) -> Dict:
        """Получить информацию об очереди зоны"""
        if zone not in ZONES:
            return {"zone": zone, "count": 0, "drivers": []}
        
        return {
            "zone": zone,
            "count": len(self._queues[zone]),
            "drivers": self._queues[zone].copy()
        }
    
    def get_all_queues_info(self) -> Dict[str, Dict]:
        """Получить информацию о всех очередях"""
        return {zone: self.get_queue_info(zone) for zone in ZONES}


# Глобальный экземпляр менеджера очередей
queue_manager = QueueManager()

