"""
Сервис расчета фиксированной стоимости поездок.

Работает на основе JSON-конфигурации с тарифами между зонами.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from bot.config import settings


@dataclass
class PriceResult:
    """Результат поиска тарифа."""

    price: Optional[float]
    mode: str  # fixed | intercity | missing
    used_reverse: bool = False
    rate_per_km: Optional[float] = None
    source_pair: Optional[Tuple[str, str]] = None

    @property
    def is_available(self) -> bool:
        return self.mode == "fixed" and self.price is not None

    @property
    def is_intercity(self) -> bool:
        return self.mode == "intercity"

    @property
    def is_missing(self) -> bool:
        return self.mode == "missing"


class PricingService:
    """Сервис для работы с фиксированными тарифами."""

    _config_data: Optional[Dict[str, Any]] = None
    _zones_by_id: Dict[str, Dict[str, str]] = {}
    _zones_by_name: Dict[str, str] = {}
    _price_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

    @classmethod
    def refresh(cls) -> None:
        """Сбросить кэшированные данные (например, после обновления файла)."""
        cls._config_data = None
        cls._zones_by_id = {}
        cls._zones_by_name = {}
        cls._price_map = {}

    @classmethod
    def _resolve_config_path(cls) -> Path:
        """Получить абсолютный путь до файла конфигурации тарифов."""
        configured_path = Path(settings.pricing_config_path)
        if configured_path.is_absolute():
            return configured_path

        # По умолчанию считаем путь относительно корня проекта
        project_root = Path(__file__).resolve().parents[2]
        return (project_root / configured_path).resolve()

    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        """Загрузить JSON с тарифами и подготовить структуры для быстрого доступа."""
        if cls._config_data is not None:
            return cls._config_data

        path = cls._resolve_config_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Файл конфигурации тарифов не найден: {path}"
            )

        with path.open("r", encoding="utf-8") as fp:
            cls._config_data = json.load(fp)

        zones = cls._config_data.get("zones", [])
        cls._zones_by_id = {zone["id"]: zone for zone in zones}
        cls._zones_by_name = {zone["name"]: zone["id"] for zone in zones}

        prices = cls._config_data.get("prices", [])
        cls._price_map = {}
        for entry in prices:
            from_zone = entry.get("from")
            to_zone = entry.get("to")
            if not from_zone or not to_zone:
                continue
            cls._price_map[(from_zone, to_zone)] = entry

        return cls._config_data

    @classmethod
    def get_zone_id_by_name(cls, name: str) -> Optional[str]:
        """Получить ID зоны по отображаемому названию."""
        if not name:
            return None
        cls._load_config()
        return cls._zones_by_name.get(name.strip())

    @classmethod
    def get_zone_name_by_id(cls, zone_id: str) -> Optional[str]:
        """Получить отображаемое название зоны по её ID."""
        if not zone_id:
            return None
        cls._load_config()
        zone = cls._zones_by_id.get(zone_id)
        return zone.get("name") if zone else None

    @classmethod
    def list_zone_names(cls) -> list[str]:
        """Список всех отображаемых названий зон."""
        cls._load_config()
        return list(cls._zones_by_name.keys())

    @classmethod
    def _find_price_entry(cls, from_zone_id: str, to_zone_id: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Найти тариф между зонами с учётом симметрии."""
        cls._load_config()
        direct = cls._price_map.get((from_zone_id, to_zone_id))
        if direct:
            return direct, False

        rules = cls._config_data.get("pricing_rules", {})
        if rules.get("fallback_symmetry"):
            reverse = cls._price_map.get((to_zone_id, from_zone_id))
            if reverse:
                return reverse, True

        return None, False

    @classmethod
    def get_price(cls, from_zone_id: str, to_zone_id: str) -> PriceResult:
        """
        Получить фиксированный тариф между двумя зонами.

        Возвращает PriceResult, в котором содержится режим расчёта:
        - fixed: найдена фиксированная цена;
        - intercity: тариф рассчитывается по межгороду (по километражу);
        - missing: тариф не задан.
        """
        entry, used_reverse = cls._find_price_entry(from_zone_id, to_zone_id)
        if not entry:
            return PriceResult(
                price=None,
                mode="missing",
                used_reverse=False,
                source_pair=(from_zone_id, to_zone_id),
            )

        mode = entry.get("mode") or "fixed"
        rules = cls._config_data.get("pricing_rules", {})

        if mode == "intercity":
            return PriceResult(
                price=None,
                mode="intercity",
                used_reverse=used_reverse,
                rate_per_km=rules.get("intercity_rate_per_km"),
                source_pair=(entry.get("from"), entry.get("to")),
            )

        price = entry.get("price")
        if price is None:
            return PriceResult(
                price=None,
                mode="missing",
                used_reverse=used_reverse,
                source_pair=(entry.get("from"), entry.get("to")),
            )

        return PriceResult(
            price=price,
            mode="fixed",
            used_reverse=used_reverse,
            rate_per_km=None,
            source_pair=(entry.get("from"), entry.get("to")),
        )

    @classmethod
    def ensure_price_available(cls, from_zone_id: str, to_zone_id: str) -> PriceResult:
        """
        Проверить, что тариф существует и является фиксированным.

        Raises:
            ValueError: если тариф отсутствует или требует ручного расчёта.
        """
        result = cls.get_price(from_zone_id, to_zone_id)

        if result.is_missing:
            from_name = cls.get_zone_name_by_id(from_zone_id) or from_zone_id
            to_name = cls.get_zone_name_by_id(to_zone_id) or to_zone_id
            raise ValueError(f"Тариф между '{from_name}' и '{to_name}' не задан.")

        if result.is_intercity:
            rate = result.rate_per_km or settings.price_per_km
            raise ValueError(
                f"Тариф между зонами рассчитывается по межгороду ({rate:.0f} ₽/км) и требует ручного подтверждения."
            )

        return result
