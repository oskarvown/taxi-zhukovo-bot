"""
Интеграция системы очередей для клиентских хэндлеров
"""
import logging
from bot.constants import ZONE_KEY_MAP
from bot.models.order import OrderZone

logger = logging.getLogger(__name__)


def map_district_to_zone(district: str) -> str:
    """
    Преобразовать район (pickup_district) в ключ зоны для системы очередей
    
    Args:
        district: Название района (например, "Новое Жуково", "Старое Жуково" и т.д.)
    
    Returns:
        Ключ зоны (например, "NEW_ZHUKOVO") или None если район не найден
    """
    if not district:
        return None
    
    # Пробуем найти точное совпадение
    zone_key = ZONE_KEY_MAP.get(district)
    
    if zone_key:
        logger.debug(f"Район '{district}' → зона '{zone_key}'")
        return zone_key
    
    # Пробуем частичное совпадение (на случай разных вариантов написания)
    district_lower = district.lower().strip()
    
    mappings = {
        "новое жуково": "NEW_ZHUKOVO",
        "новое": "NEW_ZHUKOVO",
        "старое жуково": "OLD_ZHUKOVO",
        "старое": "OLD_ZHUKOVO",
        "мысовцево": "MYSOVTSEVO",
        "авдон": "AVDON",
        "уптино": "UPTINO",
        "дёма": "DEMA",
        "дема": "DEMA",
        "сергеевка": "SERGEEVKA",
    }
    
    for key, value in mappings.items():
        if key in district_lower:
            logger.debug(f"Район '{district}' → зона '{value}' (частичное совпадение)")
            return value
    
    logger.warning(f"Не удалось сопоставить район '{district}' с зоной")
    return None


async def dispatch_order_to_queue(order_id: int, db):
    """
    Запустить диспетчеризацию заказа через систему очередей
    
    Args:
        order_id: ID заказа
        db: Сессия БД
    """
    from bot.services.order_dispatcher import get_dispatcher
    from bot.models.order import Order
    
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error(f"Заказ {order_id} не найден для диспетчеризации")
            return
        
        # Проверяем что у заказа установлена зона
        if not order.zone:
            logger.error(f"Заказ {order_id} не имеет зоны, невозможно начать диспетчеризацию")
            return
        
        # Запускаем диспетчер
        dispatcher = get_dispatcher()
        await dispatcher.create_and_dispatch_order(order_id, db)
        
        logger.info(f"Заказ {order_id} успешно отправлен в систему очередей (зона: {order.zone})")
        
    except Exception as e:
        logger.error(f"Ошибка при диспетчеризации заказа {order_id}: {e}", exc_info=True)

