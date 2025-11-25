"""
Конфигурация бота
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str = Field(default="", env="TELEGRAM_WEBHOOK_URL")
    
    # Database
    database_url: str = Field(default="sqlite:///./taxi_zhukovo.db", env="DATABASE_URL")
    
    # Application
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Admin
    admin_telegram_ids: str = Field(default="", env="ADMIN_TELEGRAM_IDS")
    
    # Pricing
    base_price: float = Field(default=100.0, env="BASE_PRICE")
    price_per_km: float = Field(default=25.0, env="PRICE_PER_KM")
    min_price: float = Field(default=150.0, env="MIN_PRICE")
    
    # Service Area
    service_area_lat: float = Field(default=55.5833, env="SERVICE_AREA_LAT")
    service_area_lon: float = Field(default=36.7500, env="SERVICE_AREA_LON")
    service_radius_km: float = Field(default=50.0, env="SERVICE_RADIUS_KM")
    
    # Fixed pricing
    pricing_config_path: str = Field(default="bot/config/pricing.json", env="PRICING_CONFIG_PATH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def admin_ids(self) -> List[int]:
        """Получить список ID администраторов"""
        if not self.admin_telegram_ids:
            return []
        return [int(id.strip()) for id in self.admin_telegram_ids.split(",") if id.strip()]


# Глобальный экземпляр настроек
settings = Settings()

