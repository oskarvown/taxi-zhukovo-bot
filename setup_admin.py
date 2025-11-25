"""
Скрипт для настройки администратора бота
Добавляет ID пользователя в файл .env
"""
import os
from pathlib import Path


def setup_admin(admin_id: int):
    """
    Добавить администратора в .env файл
    
    Args:
        admin_id: Telegram ID администратора
    """
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    # Если .env не существует, создаем из .env.example
    if not env_file.exists():
        if env_example.exists():
            print("📄 Создаю файл .env из .env.example...")
            with open(env_example, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Файл .env создан")
        else:
            print("❌ Файл .env.example не найден")
            return
    
    # Читаем текущий .env
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Обновляем ADMIN_TELEGRAM_IDS
    updated = False
    new_lines = []
    
    for line in lines:
        if line.startswith('ADMIN_TELEGRAM_IDS='):
            # Получаем текущие ID
            current_value = line.split('=', 1)[1].strip()
            
            if current_value and current_value != 'your_admin_id_here':
                # Добавляем новый ID к существующим
                existing_ids = [id.strip() for id in current_value.split(',') if id.strip()]
                if str(admin_id) not in existing_ids:
                    existing_ids.append(str(admin_id))
                    new_value = ','.join(existing_ids)
                    new_lines.append(f'ADMIN_TELEGRAM_IDS={new_value}\n')
                    print(f"✅ ID {admin_id} добавлен к существующим админам: {new_value}")
                else:
                    new_lines.append(line)
                    print(f"ℹ️  ID {admin_id} уже есть в списке админов")
            else:
                # Устанавливаем первого админа
                new_lines.append(f'ADMIN_TELEGRAM_IDS={admin_id}\n')
                print(f"✅ ID {admin_id} установлен как администратор")
            
            updated = True
        else:
            new_lines.append(line)
    
    # Записываем обратно
    if updated:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"\n🎉 Пользователь с ID {admin_id} теперь администратор!")
        print("\n📝 Не забудьте:")
        print("   1. Добавить TELEGRAM_BOT_TOKEN в файл .env")
        print("   2. Запустить бота: python run.py")
    else:
        print("❌ Не удалось обновить ADMIN_TELEGRAM_IDS в .env")


def show_env_status():
    """Показать текущий статус .env файла"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ Файл .env не найден")
        print("   Создайте его, скопировав .env.example:")
        print("   cp .env.example .env")
        return False
    
    print("✅ Файл .env существует")
    
    # Проверяем настройки
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'TELEGRAM_BOT_TOKEN=your_bot_token_here' in content or 'TELEGRAM_BOT_TOKEN=' not in content:
        print("⚠️  Токен бота не настроен (TELEGRAM_BOT_TOKEN)")
    else:
        print("✅ Токен бота настроен")
    
    if 'ADMIN_TELEGRAM_IDS=' in content:
        for line in content.split('\n'):
            if line.startswith('ADMIN_TELEGRAM_IDS='):
                admin_ids = line.split('=', 1)[1].strip()
                if admin_ids and admin_ids != 'your_admin_id_here':
                    print(f"✅ Администраторы: {admin_ids}")
                else:
                    print("⚠️  Администраторы не настроены")
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Настройка администратора для бота «Такси Жуково+»")
    print("=" * 60)
    print()
    
    # Показываем текущий статус
    print("📊 Проверка текущей конфигурации:")
    print("-" * 60)
    show_env_status()
    print()
    
    # Добавляем администратора
    admin_id = 6840100810
    print("-" * 60)
    print(f"👤 Добавление администратора с ID: {admin_id}")
    print("-" * 60)
    setup_admin(admin_id)
    
    print()
    print("=" * 60)
    print("🚀 Готово! Теперь вы можете запустить бота:")
    print("   python run.py")
    print("=" * 60)

