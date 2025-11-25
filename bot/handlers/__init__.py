"""
Обработчики команд бота
"""
from .user import register_user_handlers
from .driver import register_driver_handlers
from .admin import register_admin_handlers
from .auth import register_auth_handlers

__all__ = [
    "register_user_handlers",
    "register_driver_handlers",
    "register_admin_handlers",
    "register_auth_handlers",
]

