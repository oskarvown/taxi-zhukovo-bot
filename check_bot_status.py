#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка статуса бота через Telegram API
Проверяет, не заблокирован ли бот Telegram
"""

import os
import sys
import asyncio

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram import Bot  # pyright: ignore[reportMissingImports]
    from telegram.error import TelegramError  # pyright: ignore[reportMissingImports]
    from bot.config import settings
except ImportError as e:
    print(f"⚠️ Ошибка импорта: {e}")
    print("Убедитесь, что вы запускаете скрипт из корневой директории проекта")
    sys.exit(1)


async def check_bot_status():
    """Проверить статус бота через Telegram API"""
    print("=" * 80)
    print("🔍 ПРОВЕРКА СТАТУСА БОТА В TELEGRAM")
    print("=" * 80)
    print()
    
    token = settings.telegram_bot_token
    if not token:
        print("❌ КРИТИЧНО: Токен бота не найден!")
        return False
    
    print(f"📋 Токен: {token[:10]}...{token[-5:]}")
    print()
    
    try:
        bot = Bot(token=token)
        
        print("🔄 Запрос к Telegram API...")
        bot_info = await bot.get_me()
        
        print()
        print("=" * 80)
        print("✅ БОТ АКТИВЕН И РАБОТАЕТ!")
        print("=" * 80)
        print()
        print(f"📱 Имя бота: {bot_info.first_name}")
        if bot_info.username:
            print(f"👤 Username: @{bot_info.username}")
        print(f"🆔 ID бота: {bot_info.id}")
        print()
        print("✅ Бот не заблокирован Telegram")
        print("✅ API доступен")
        print("✅ Токен валиден")
        print()
        
        return True
        
    except TelegramError as e:
        print()
        print("=" * 80)
        print("❌ ПРОБЛЕМА С БОТОМ!")
        print("=" * 80)
        print()
        
        error_message = str(e).lower()
        
        if "unauthorized" in error_message or "invalid token" in error_message:
            print("❌ ПРОБЛЕМА: Неверный или отозванный токен")
            print()
            print("💡 РЕШЕНИЕ:")
            print("1. Откройте @BotFather в Telegram")
            print("2. Отправьте /mybots")
            print("3. Выберите вашего бота")
            print("4. Проверьте статус бота")
            print("5. Если нужно, получите новый токен: /token")
            print()
            
        elif "forbidden" in error_message:
            print("❌ ПРОБЛЕМА: Бот заблокирован Telegram")
            print()
            print("💡 РЕШЕНИЕ:")
            print("1. Откройте @BotFather в Telegram")
            print("2. Отправьте /mybots")
            print("3. Выберите вашего бота")
            print("4. Проверьте, не было ли жалоб")
            print("5. Обратитесь в поддержку Telegram")
            print()
            
        elif "account frozen" in error_message or "frozen" in error_message:
            print("❌ КРИТИЧНО: Аккаунт заморожен!")
            print()
            print("💡 РЕШЕНИЕ:")
            print("1. Это означает, что Telegram заблокировал бота")
            print("2. Откройте @BotFather в Telegram")
            print("3. Отправьте /mybots")
            print("4. Выберите вашего бота")
            print("5. Проверьте статус - если бот удален, создайте нового")
            print("6. Обратитесь в поддержку Telegram: https://telegram.org/support")
            print()
            
        else:
            print(f"❌ ОШИБКА: {e}")
            print()
            print("💡 Проверьте:")
            print("1. Интернет-соединение")
            print("2. Правильность токена")
            print("3. Статус бота в BotFather")
            print()
        
        return False
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ НЕИЗВЕСТНАЯ ОШИБКА")
        print("=" * 80)
        print()
        print(f"Ошибка: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция"""
    try:
        result = asyncio.run(check_bot_status())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

