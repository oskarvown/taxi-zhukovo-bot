# 💾 Восстановление базы данных на сервере

## Проблема
На сервере создалась новая пустая база данных, и водители не перенеслись.

## ✅ Решение: Перенос базы данных

### Вариант 1: Копирование базы данных (рекомендуется)

#### Шаг 1: Скопируйте базу данных на сервер

**На вашем компьютере (Mac):**

```bash
# Копирование базы данных на сервер
scp /Volumes/PortableSSD/TAXI_ЖУКОВО/taxi_zhukovo.db root@195.133.73.49:/opt/taxi-zhukovo/taxi_zhukovo.db.backup
```

**Или через Web SSH в панели Timeweb:**
1. Загрузите файл `taxi_zhukovo.db` на сервер через панель управления
2. Или используйте команду выше

#### Шаг 2: На сервере - замена базы данных

**На сервере (через Web SSH):**

```bash
cd /opt/taxi-zhukovo

# 1. Остановка бота
systemctl stop taxi-bot

# 2. Создание резервной копии текущей базы (на всякий случай)
cp taxi_zhukovo.db taxi_zhukovo.db.new_backup

# 3. Замена базы данных
mv taxi_zhukovo.db.backup taxi_zhukovo.db

# 4. Установка правильных прав
chown taxi:taxi taxi_zhukovo.db
chmod 644 taxi_zhukovo.db

# 5. Запуск бота
systemctl start taxi-bot

# 6. Проверка
systemctl status taxi-bot
journalctl -u taxi-bot -f
```

---

### Вариант 2: Выборочное восстановление водителей

Если хотите сохранить данные, которые уже есть на сервере, можно восстановить только водителей.

#### Шаг 1: Экспорт водителей из локальной базы

**На вашем компьютере:**

```bash
cd /Volumes/PortableSSD/TAXI_ЖУКОВО
python3 -c "
from database.db import SessionLocal, engine
from bot.models.driver import Driver
from bot.models.user import User, UserRole
import json

db = SessionLocal()
drivers = db.query(Driver).join(User).all()

data = []
for driver in drivers:
    user = driver.user
    data.append({
        'telegram_id': user.telegram_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'car_model': driver.car_model,
        'car_number': driver.car_number,
        'car_color': driver.car_color,
        'license_number': driver.license_number,
        'rating': driver.rating,
        'rating_avg': driver.rating_avg,
        'rating_count': driver.rating_count,
        'completed_trips_count': driver.completed_trips_count,
        'is_verified': driver.is_verified
    })

with open('drivers_backup.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'✅ Экспортировано {len(data)} водителей в drivers_backup.json')
db.close()
"
```

#### Шаг 2: Скопируйте файл на сервер

```bash
scp /Volumes/PortableSSD/TAXI_ЖУКОВО/drivers_backup.json root@195.133.73.49:/opt/taxi-zhukovo/
```

#### Шаг 3: Восстановление на сервере

**На сервере:**

```bash
cd /opt/taxi-zhukovo

# Остановка бота
systemctl stop taxi-bot

# Создание скрипта восстановления
cat > restore_drivers.py << 'EOF'
import json
from database.db import SessionLocal
from bot.models.driver import Driver
from bot.models.user import User, UserRole

db = SessionLocal()

try:
    with open('drivers_backup.json', 'r', encoding='utf-8') as f:
        drivers_data = json.load(f)
    
    restored = 0
    for data in drivers_data:
        # Проверяем, существует ли пользователь
        user = db.query(User).filter(User.telegram_id == data['telegram_id']).first()
        
        if not user:
            # Создаем пользователя
            user = User(
                telegram_id=data['telegram_id'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                username=data.get('username'),
                role=UserRole.DRIVER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Проверяем, существует ли водитель
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        
        if not driver:
            # Создаем водителя
            user.role = UserRole.DRIVER
            driver = Driver(
                user_id=user.id,
                car_model=data['car_model'],
                car_number=data['car_number'],
                car_color=data.get('car_color'),
                license_number=data['license_number'],
                rating=data.get('rating', 5.0),
                rating_avg=data.get('rating_avg', 0.0),
                rating_count=data.get('rating_count', 0),
                completed_trips_count=data.get('completed_trips_count', 0),
                is_verified=data.get('is_verified', True)
            )
            db.add(driver)
            restored += 1
        else:
            # Обновляем данные
            driver.car_model = data['car_model']
            driver.car_number = data['car_number']
            driver.car_color = data.get('car_color')
            driver.license_number = data['license_number']
            driver.rating = data.get('rating', driver.rating)
            driver.rating_avg = data.get('rating_avg', driver.rating_avg)
            driver.rating_count = data.get('rating_count', driver.rating_count)
            driver.completed_trips_count = data.get('completed_trips_count', driver.completed_trips_count)
            driver.is_verified = data.get('is_verified', True)
            user.role = UserRole.DRIVER
    
    db.commit()
    print(f'✅ Восстановлено {restored} водителей')
    
except Exception as e:
    db.rollback()
    print(f'❌ Ошибка: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
EOF

# Запуск восстановления
source venv/bin/activate
python restore_drivers.py

# Запуск бота
systemctl start taxi-bot
systemctl status taxi-bot
```

---

## 🚀 Быстрый вариант (рекомендую)

**Самый простой способ - скопировать всю базу:**

```bash
# На вашем Mac (в терминале Cursor):
scp /Volumes/PortableSSD/TAXI_ЖУКОВО/taxi_zhukovo.db root@195.133.73.49:/tmp/taxi_zhukovo.db

# На сервере (через Web SSH):
cd /opt/taxi-zhukovo
systemctl stop taxi-bot
mv /tmp/taxi_zhukovo.db taxi_zhukovo.db
chown taxi:taxi taxi_zhukovo.db
systemctl start taxi-bot
systemctl status taxi-bot
```

---

## ⚠️ Важно

- **Остановите бота** перед заменой базы данных
- Создайте резервную копию текущей базы на сервере
- После замены проверьте, что бот запустился

---

**После восстановления все водители должны появиться в системе!**













