#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Комплексный анализ блокировки бота Telegram
Проверяет все возможные причины блокировки и предоставляет детальный отчет
"""

import os
import sys
import re
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database.db import SessionLocal
    from bot.models import User, Driver, Order
    from bot.config import settings
    from sqlalchemy import text
except ImportError as e:
    print(f"⚠️ Ошибка импорта: {e}")
    print("Убедитесь, что вы запускаете скрипт из корневой директории проекта")
    sys.exit(1)


class BotBlockAnalyzer:
    """Анализатор блокировки бота"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        self.errors_found = []
        
    def analyze_all(self):
        """Выполнить полный анализ"""
        print("=" * 80)
        print("🔍 КОМПЛЕКСНЫЙ АНАЛИЗ БЛОКИРОВКИ БОТА")
        print("=" * 80)
        print()
        
        # 1. Проверка конфигурации
        self.check_configuration()
        
        # 2. Проверка статуса бота через Telegram API
        self.check_telegram_status()
        
        # 3. Проверка базы данных
        self.check_database()
        
        # 4. Проверка логов (если доступны)
        self.check_logs()
        
        # 5. Анализ паттернов ошибок
        self.analyze_error_patterns()
        
        # 6. Проверка активности бота
        self.check_bot_activity()
        
        # Вывод результатов
        self.print_report()
        
    def check_configuration(self):
        """Проверка конфигурации бота"""
        print("📋 Проверка конфигурации...")
        
        # Проверка токена
        token = settings.telegram_bot_token
        if not token:
            self.issues.append("❌ КРИТИЧНО: Токен бота не найден в конфигурации!")
        elif len(token) < 20:
            self.issues.append("⚠️ Токен бота выглядит некорректно (слишком короткий)")
        else:
            self.info.append(f"✅ Токен бота найден: {token[:10]}...{token[-5:]}")
        
        # Проверка .env файла
        env_file = Path(".env")
        if env_file.exists():
            self.info.append("✅ Файл .env найден")
            # Проверяем наличие критических переменных
            with open(env_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
                if "TELEGRAM_BOT_TOKEN" not in env_content:
                    self.warnings.append("⚠️ TELEGRAM_BOT_TOKEN не найден в .env")
        else:
            self.warnings.append("⚠️ Файл .env не найден")
        
        print("   ✓ Конфигурация проверена\n")
    
    def check_telegram_status(self):
        """Проверка статуса бота через Telegram API"""
        print("🔍 Проверка статуса бота в Telegram...")
        
        try:
            import asyncio
            from telegram import Bot  # pyright: ignore[reportMissingImports]
            from telegram.error import TelegramError  # pyright: ignore[reportMissingImports]
            
            token = settings.telegram_bot_token
            if not token:
                self.warnings.append("⚠️ Токен не найден, пропуск проверки Telegram API")
                print("   ⚠️ Токен не найден, пропуск проверки\n")
                return
            
            async def check():
                try:
                    bot = Bot(token=token)
                    bot_info = await bot.get_me()
                    self.info.append(f"✅ Бот активен в Telegram: @{bot_info.username or 'без username'}")
                    self.info.append(f"✅ Имя бота: {bot_info.first_name}")
                    return True
                except TelegramError as e:
                    error_msg = str(e).lower()
                    if "unauthorized" in error_msg or "invalid token" in error_msg:
                        self.issues.append("❌ КРИТИЧНО: Токен неверный или отозван!")
                        self.issues.append("   Решение: Проверьте токен в BotFather, получите новый если нужно")
                    elif "forbidden" in error_msg:
                        self.issues.append("❌ КРИТИЧНО: Бот заблокирован Telegram!")
                        self.issues.append("   Решение: Проверьте статус в BotFather, обратитесь в поддержку")
                    elif "frozen" in error_msg or "account frozen" in error_msg:
                        self.issues.append("❌ КРИТИЧНО: Аккаунт заморожен Telegram!")
                        self.issues.append("   Решение: Обратитесь в поддержку Telegram или создайте нового бота")
                    else:
                        self.warnings.append(f"⚠️ Ошибка при проверке Telegram API: {e}")
                    return False
            
            result = asyncio.run(check())
            if result:
                print("   ✅ Бот активен в Telegram\n")
            else:
                print("   ❌ Проблема с ботом в Telegram\n")
                
        except ImportError:
            self.warnings.append("⚠️ Не удалось импортировать telegram библиотеку для проверки API")
            print("   ⚠️ Пропуск проверки Telegram API (библиотека не найдена)\n")
        except Exception as e:
            self.warnings.append(f"⚠️ Ошибка при проверке Telegram API: {e}")
            print(f"   ⚠️ Ошибка: {e}\n")
        
    def check_database(self):
        """Проверка базы данных на проблемы"""
        print("💾 Проверка базы данных...")
        
        db = SessionLocal()
        try:
            # Проверка подключения
            db.execute(text("SELECT 1"))
            self.info.append("✅ Подключение к БД успешно")
            
            # Статистика пользователей
            total_users = db.query(User).count()
            users_without_phone = db.query(User).filter(User.phone_number == None).count()
            banned_users = db.query(User).filter(User.is_banned == True).count()
            
            self.info.append(f"📊 Всего пользователей: {total_users}")
            self.info.append(f"📊 Пользователей без телефона: {users_without_phone}")
            self.info.append(f"📊 Забаненных пользователей: {banned_users}")
            
            if users_without_phone > total_users * 0.5:
                self.warnings.append(
                    f"⚠️ Большой процент пользователей без телефона ({users_without_phone}/{total_users})"
                )
            
            # Статистика водителей
            total_drivers = db.query(Driver).count()
            online_drivers = db.query(Driver).filter(Driver.is_online == True).count()
            verified_drivers = db.query(Driver).filter(Driver.is_verified == True).count()
            
            self.info.append(f"🚗 Всего водителей: {total_drivers}")
            self.info.append(f"🚗 Онлайн водителей: {online_drivers}")
            self.info.append(f"🚗 Верифицированных водителей: {verified_drivers}")
            
            # Проверка водителей без телефона
            drivers_without_phone = 0
            for driver in db.query(Driver).all():
                user = db.query(User).filter(User.id == driver.user_id).first()
                if user and not user.phone_number:
                    drivers_without_phone += 1
            
            if drivers_without_phone > 0:
                self.warnings.append(
                    f"⚠️ Найдено {drivers_without_phone} водителей без телефона"
                )
            
            # Статистика заказов
            total_orders = db.query(Order).count()
            recent_orders = db.query(Order).filter(
                Order.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            self.info.append(f"📦 Всего заказов: {total_orders}")
            self.info.append(f"📦 Заказов за последние 24 часа: {recent_orders}")
            
            if recent_orders == 0 and total_orders > 0:
                self.warnings.append("⚠️ Нет активности заказов за последние 24 часа")
            
        except Exception as e:
            self.issues.append(f"❌ Ошибка при проверке БД: {e}")
        finally:
            db.close()
        
        print("   ✓ База данных проверена\n")
        
    def check_logs(self):
        """Проверка логов на наличие ошибок"""
        print("📝 Проверка логов...")
        
        log_paths = [
            "logs/bot.log",
            "logs/bot_error.log",
            "/opt/taxi-zhukovo/logs/bot.log",
            "/opt/taxi-zhukovo/logs/bot_error.log",
        ]
        
        log_found = False
        for log_path in log_paths:
            log_file = Path(log_path)
            if log_file.exists():
                log_found = True
                self.info.append(f"✅ Найден лог файл: {log_path}")
                self.analyze_log_file(log_file)
                break
        
        if not log_found:
            self.warnings.append("⚠️ Файлы логов не найдены (возможно, бот запущен на сервере)")
            self.warnings.append("   Для проверки логов на сервере используйте: ssh и journalctl")
        
        print("   ✓ Логи проверены\n")
        
    def analyze_log_file(self, log_file: Path):
        """Анализ файла логов"""
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            if not lines:
                self.warnings.append(f"⚠️ Лог файл {log_file} пуст")
                return
            
            # Анализ последних 1000 строк
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
            
            # Поиск критических ошибок
            error_patterns = [
                (r'Forbidden', 'Запрещен доступ к API'),
                (r'Unauthorized', 'Неавторизованный доступ (проблема с токеном)'),
                (r'Conflict', 'Конфликт - несколько экземпляров бота'),
                (r'Rate limit', 'Превышен лимит запросов'),
                (r'Too Many Requests', 'Слишком много запросов'),
                (r'Blocked', 'Пользователь заблокировал бота'),
                (r'Chat not found', 'Чат не найден'),
                (r'Bad Request', 'Некорректный запрос к API'),
                (r'Network error', 'Ошибка сети'),
                (r'Connection error', 'Ошибка подключения'),
            ]
            
            error_counts = Counter()
            for line in recent_lines:
                for pattern, description in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        error_counts[description] += 1
                        self.errors_found.append({
                            'type': description,
                            'line': line.strip()[:200]
                        })
            
            if error_counts:
                self.issues.append("❌ Найдены ошибки в логах:")
                for error_type, count in error_counts.most_common():
                    self.issues.append(f"   - {error_type}: {count} раз(а)")
            else:
                self.info.append("✅ Критических ошибок в логах не найдено")
            
            # Проверка последней активности
            last_line = lines[-1] if lines else ""
            if "start" in last_line.lower() or "error" in last_line.lower():
                self.info.append(f"📄 Последняя строка лога: {last_line.strip()[:100]}")
            
        except Exception as e:
            self.warnings.append(f"⚠️ Ошибка при чтении лога {log_file}: {e}")
    
    def analyze_error_patterns(self):
        """Анализ паттернов ошибок"""
        print("🔬 Анализ паттернов ошибок...")
        
        if not self.errors_found:
            self.info.append("✅ Паттерны ошибок не обнаружены")
            print("   ✓ Паттерны проанализированы\n")
            return
        
        # Группировка ошибок по типам
        error_types = Counter([e['type'] for e in self.errors_found])
        
        # Анализ наиболее частых ошибок
        most_common = error_types.most_common(3)
        if most_common:
            self.issues.append("🔍 Наиболее частые ошибки:")
            for error_type, count in most_common:
                self.issues.append(f"   - {error_type}: {count} раз(а)")
        
        print("   ✓ Паттерны проанализированы\n")
        
    def check_bot_activity(self):
        """Проверка активности бота"""
        print("📊 Проверка активности бота...")
        
        db = SessionLocal()
        try:
            # Проверка последних заказов
            recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()
            
            if recent_orders:
                last_order = recent_orders[0]
                time_since_last = datetime.utcnow() - last_order.created_at
                
                if time_since_last < timedelta(hours=1):
                    self.info.append(f"✅ Последний заказ был {time_since_last.seconds // 60} минут назад")
                elif time_since_last < timedelta(hours=24):
                    self.warnings.append(f"⚠️ Последний заказ был {time_since_last.seconds // 3600} часов назад")
                else:
                    self.warnings.append(f"⚠️ Нет активности более 24 часов")
            else:
                self.warnings.append("⚠️ В базе нет заказов")
            
            # Проверка онлайн водителей
            online_drivers = db.query(Driver).filter(Driver.is_online == True).count()
            if online_drivers == 0:
                self.warnings.append("⚠️ Нет онлайн водителей")
            else:
                self.info.append(f"✅ Онлайн водителей: {online_drivers}")
                
        except Exception as e:
            self.warnings.append(f"⚠️ Ошибка при проверке активности: {e}")
        finally:
            db.close()
        
        print("   ✓ Активность проверена\n")
        
    def print_report(self):
        """Вывод итогового отчета"""
        print("=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ")
        print("=" * 80)
        print()
        
        # Критические проблемы
        if self.issues:
            print("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
            print("-" * 80)
            for issue in self.issues:
                print(f"  {issue}")
            print()
        
        # Предупреждения
        if self.warnings:
            print("⚠️ ПРЕДУПРЕЖДЕНИЯ:")
            print("-" * 80)
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        # Информация
        if self.info:
            print("ℹ️ ИНФОРМАЦИЯ:")
            print("-" * 80)
            for info in self.info:
                print(f"  {info}")
            print()
        
        # Рекомендации
        print("=" * 80)
        print("💡 РЕКОМЕНДАЦИИ ПО УСТРАНЕНИЮ")
        print("=" * 80)
        print()
        
        if any("Unauthorized" in str(e) for e in self.errors_found):
            print("1. ПРОБЛЕМА С ТОКЕНОМ:")
            print("   - Проверьте токен бота в BotFather (@BotFather)")
            print("   - Убедитесь, что токен правильный в .env файле")
            print("   - Проверьте, не был ли бот удален или заблокирован")
            print()
        
        if any("Conflict" in str(e) for e in self.errors_found):
            print("2. КОНФЛИКТ ЭКЗЕМПЛЯРОВ:")
            print("   - Остановите все запущенные экземпляры бота")
            print("   - Проверьте: ps aux | grep run.py")
            print("   - Убедитесь, что systemd служба не запущена дважды")
            print()
        
        if any("Rate limit" in str(e) or "Too Many" in str(e) for e in self.errors_found):
            print("3. ПРЕВЫШЕН ЛИМИТ ЗАПРОСОВ:")
            print("   - Уменьшите частоту отправки сообщений")
            print("   - Добавьте задержки между запросами")
            print("   - Проверьте, нет ли зацикленных запросов")
            print()
        
        if any("Forbidden" in str(e) for e in self.errors_found):
            print("4. ЗАПРЕЩЕН ДОСТУП:")
            print("   - Бот может быть заблокирован Telegram")
            print("   - Проверьте статус в BotFather")
            print("   - Обратитесь в поддержку Telegram")
            print()
        
        if any("Blocked" in str(e) for e in self.errors_found):
            print("5. ПОЛЬЗОВАТЕЛИ ЗАБЛОКИРОВАЛИ БОТА:")
            print("   - Это нормально, если пользователь сам заблокировал бота")
            print("   - Добавьте обработку этой ошибки в код")
            print()
        
        print("=" * 80)
        print("📋 ДОПОЛНИТЕЛЬНЫЕ ШАГИ ДИАГНОСТИКИ")
        print("=" * 80)
        print()
        print("1. Проверьте логи на сервере:")
        print("   ssh root@195.133.73.49")
        print("   journalctl -u taxi-bot -n 200 | grep -i error")
        print()
        print("2. Проверьте статус бота:")
        print("   systemctl status taxi-bot")
        print()
        print("3. Проверьте BotFather:")
        print("   Откройте @BotFather в Telegram")
        print("   Отправьте /mybots")
        print("   Выберите вашего бота и проверьте статус")
        print()
        print("4. Проверьте токен:")
        print("   grep TELEGRAM_BOT_TOKEN .env")
        print()
        print("=" * 80)


def main():
    """Главная функция"""
    try:
        analyzer = BotBlockAnalyzer()
        analyzer.analyze_all()
    except KeyboardInterrupt:
        print("\n\n⚠️ Анализ прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

