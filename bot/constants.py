"""
Константы системы
"""

# Зоны обслуживания (ключи в латинице)
ZONES = [
    "NEW_ZHUKOVO",   # Новое Жуково
    "OLD_ZHUKOVO",   # Старое Жуково
    "MYSOVTSEVO",    # Мысовцево
    "AVDON",         # Авдон
    "UPTINO",        # Уптино
    "DEMA",          # Дёма
    "SERGEEVKA"      # Сергеевка
]

# Публичные названия зон (для UI)
PUBLIC_ZONE_LABELS = {
    "NEW_ZHUKOVO": "Новое Жуково",
    "OLD_ZHUKOVO": "Старое Жуково",
    "MYSOVTSEVO": "Мысовцево",
    "AVDON": "Авдон",
    "UPTINO": "Уптино",
    "DEMA": "Дёма",
    "SERGEEVKA": "Сергеевка",
}

# Обратный маппинг (от публичного названия к ключу)
ZONE_KEY_MAP = {v: k for k, v in PUBLIC_ZONE_LABELS.items()}

# Таймауты системы очередей
DRIVER_RESPONSE_TIMEOUT = 30  # секунд на ответ водителя
ORDER_GLOBAL_TIMEOUT = 180     # секунд до fallback (3 минуты)

