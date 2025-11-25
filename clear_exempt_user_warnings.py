"""
Скрипт для очистки предупреждений и бана для исключенного пользователя
"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from database.db import SessionLocal
from bot.services import UserService
from bot.services.user_penalty_service import EXEMPT_USER_TELEGRAM_ID

def clear_exempt_user_warnings():
    """Очистить предупреждения и бан для исключенного пользователя"""
    db = SessionLocal()
    try:
        user = UserService.get_user_by_telegram_id(db, EXEMPT_USER_TELEGRAM_ID)
        
        if not user:
            print(f"❌ Пользователь с Telegram ID {EXEMPT_USER_TELEGRAM_ID} не найден в базе данных.")
            print("   Убедитесь, что пользователь зарегистрирован в боте (отправил /start).")
            return
        
        print(f"✅ Найден пользователь: {user.full_name} (ID: {user.id}, Telegram ID: {user.telegram_id})")
        
        # Очищаем предупреждения и бан
        old_warning_count = user.warning_count
        old_is_banned = user.is_banned
        
        user.warning_count = 0
        user.is_banned = False
        user.last_warning_at = None
        
        db.commit()
        
        print(f"✅ Предупреждения и бан очищены:")
        print(f"   - Предупреждений было: {old_warning_count}, стало: 0")
        print(f"   - Бан был: {old_is_banned}, стал: False")
        print(f"   - Дата последнего предупреждения: очищена")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке предупреждений: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🧹 Очистка предупреждений для исключенного пользователя...")
    print(f"   Telegram ID: {EXEMPT_USER_TELEGRAM_ID}")
    print()
    clear_exempt_user_warnings()
    print()
    print("✅ Готово!")

