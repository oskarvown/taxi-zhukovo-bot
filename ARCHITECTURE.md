# 🏗️ Архитектура бота такси Жуково

## Обзор системы

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram Bot API                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    bot/main.py                               │
│                  (Entry Point)                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    ┌────────┐    ┌─────────┐    ┌─────────┐
    │  User  │    │ Driver  │    │  Admin  │
    │Handlers│    │Handlers │    │Handlers │
    └────┬───┘    └────┬────┘    └────┬────┘
         │             │              │
         └─────────────┼──────────────┘
                       ▼
            ┌──────────────────┐
            │    Services      │
            │  (Business Logic)│
            └─────────┬────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    ┌─────────┐  ┌─────────┐  ┌────────┐
    │  User   │  │  Order  │  │Pricing │
    │ Service │  │ Service │  │Service │
    └────┬────┘  └────┬────┘  └────────┘
         │            │
         └────────────┼────────────┐
                      ▼            │
              ┌──────────────┐    │
              │   Models     │    │
              │  (ORM Layer) │    │
              └──────┬───────┘    │
                     │            │
                     ▼            ▼
              ┌─────────────────────┐
              │   Database (SQLite) │
              │   user, order,      │
              │   driver tables     │
              └─────────────────────┘
```

## Компоненты системы

### 1. Точка входа (bot/main.py)

**Ответственность:**
- Инициализация приложения
- Настройка логирования
- Регистрация обработчиков
- Запуск polling

**Основные функции:**
- `main()` - основная функция запуска
- `post_init()` - действия после инициализации
- `post_shutdown()` - действия при остановке

### 2. Handlers (Обработчики)

#### bot/handlers/user.py
**Обрабатывает команды клиентов:**
- `/start` - Приветствие и регистрация
- `/order` - Создание заказа (ConversationHandler)
- `/history` - История заказов
- `/help` - Справка

**Состояния разговора:**
```
START → PICKUP_ADDRESS → DROPOFF_ADDRESS → CONFIRM_ORDER → END
```

#### bot/handlers/driver.py
**Обрабатывает команды водителей:**
- Смена статуса (онлайн/оффлайн)
- Принятие заказов
- Начало/завершение поездки
- Просмотр активных заказов

#### bot/handlers/admin.py
**Обрабатывает команды администраторов:**
- `/admin_stats` - Статистика
- `/verify_driver` - Верификация водителей
- `/list_drivers` - Список водителей
- `/pending_orders` - Ожидающие заказы

### 3. Services (Бизнес-логика)

#### bot/services/user_service.py
- Создание/получение пользователей
- Управление ролями
- Проверка прав администратора

#### bot/services/order_service.py
- Создание заказов
- Управление статусами
- Принятие/отклонение заказов
- Оценка поездок
- История заказов

#### bot/services/pricing_service.py
- Расчет расстояния (формула Haversine)
- Расчет стоимости поездки
- Применение тарифов

### 4. Models (Модели данных)

#### bot/models/user.py
```python
User:
  - id (PK)
  - telegram_id (Unique)
  - username
  - first_name, last_name
  - phone_number
  - role (customer/driver/admin)
  - is_active
  - created_at, updated_at
```

#### bot/models/driver.py
```python
Driver:
  - id (PK)
  - user_id (FK → User)
  - car_model, car_number, car_color
  - license_number
  - rating, total_rides
  - is_online, is_verified
  - created_at, updated_at
```

#### bot/models/order.py
```python
Order:
  - id (PK)
  - customer_id (FK → User)
  - driver_id (FK → User)
  - pickup_address, pickup_lat, pickup_lon
  - dropoff_address, dropoff_lat, dropoff_lon
  - status (pending/accepted/in_progress/completed/cancelled)
  - distance_km, price
  - customer_comment, rating, feedback
  - created_at, accepted_at, started_at, completed_at
```

### 5. Utils (Утилиты)

#### bot/utils/keyboards.py
Генерация клавиатур Telegram:
- Главное меню
- Меню водителя
- Запрос геолокации
- Inline-кнопки для действий

#### bot/utils/validators.py
Валидация данных:
- Номера телефонов
- Номера автомобилей
- Координаты
- Рейтинги

### 6. Database (База данных)

**database/db.py:**
- Настройка SQLAlchemy
- Создание сессий
- Инициализация таблиц

## Потоки данных

### Поток создания заказа (Customer)

```
1. User нажимает "Заказать такси"
   ↓
2. UserHandler.order_start()
   ↓
3. Проверка активных заказов (OrderService)
   ↓
4. Запрос адреса отправления
   ↓
5. Запрос адреса назначения
   ↓
6. PricingService.calculate_order_price()
   ↓
7. OrderService.create_order()
   ↓
8. Показ информации с подтверждением
   ↓
9. User подтверждает → статус PENDING
```

### Поток выполнения заказа (Driver)

```
1. Driver переходит в онлайн
   ↓
2. Получает уведомления о новых заказах
   ↓
3. Нажимает "Принять заказ"
   ↓
4. OrderService.accept_order() → статус ACCEPTED
   ↓
5. Customer получает уведомление с данными водителя
   ↓
6. Driver нажимает "Начать поездку"
   ↓
7. OrderService.start_order() → статус IN_PROGRESS
   ↓
8. Driver нажимает "Завершить поездку"
   ↓
9. OrderService.complete_order() → статус COMPLETED
   ↓
10. Customer получает запрос на оценку
    ↓
11. OrderService.rate_order() + обновление рейтинга Driver
```

## Статусы заказа

```
PENDING → ACCEPTED → IN_PROGRESS → COMPLETED
   ↓                      ↓
CANCELLED ← ← ← ← ← ← CANCELLED
```

**Переходы:**
- `PENDING` → `ACCEPTED` - Водитель принял
- `PENDING` → `CANCELLED` - Отменен клиентом/системой
- `ACCEPTED` → `IN_PROGRESS` - Поездка началась
- `ACCEPTED` → `CANCELLED` - Отменен водителем/клиентом
- `IN_PROGRESS` → `COMPLETED` - Поездка завершена
- `IN_PROGRESS` → `CANCELLED` - Отменен (редко)

## Расчет стоимости

```python
distance = haversine(pickup_coords, dropoff_coords)
price = BASE_PRICE + (distance * PRICE_PER_KM)
price = max(price, MIN_PRICE)
```

**Параметры (настраиваются в .env):**
- `BASE_PRICE` = 100 руб
- `PRICE_PER_KM` = 25 руб/км
- `MIN_PRICE` = 150 руб

## Безопасность

### Валидация входных данных
- Все пользовательские вводы валидируются
- Проверка прав доступа для админ-команд
- Проверка владения заказами

### Управление доступом
- Роли: CUSTOMER, DRIVER, ADMIN
- Проверка `is_admin()` для админ-функций
- Водители требуют верификации (`is_verified`)

### Хранение данных
- Bot Token в `.env` (не коммитится)
- Admin IDs в `.env`
- База данных локально (SQLite)

## Масштабирование

### Текущая архитектура (MVP)
- Single instance
- SQLite
- Long polling
- Синхронные операции

### Для продакшн (рекомендации)

**База данных:**
```
SQLite → PostgreSQL/MySQL
```

**Режим работы:**
```
Polling → Webhook (nginx + gunicorn/uvicorn)
```

**Кэширование:**
```
+ Redis для кэша и очередей
```

**Микросервисы (опционально):**
```
Bot Service
├── Order Service
├── User Service  
├── Notification Service
└── Payment Service
```

## Зависимости

```
python-telegram-bot → Telegram API
SQLAlchemy → ORM
pydantic → Валидация конфигурации
python-dotenv → Переменные окружения
loguru → Логирование
```

## Расширения (будущее)

### Интеграция карт
```python
# Геокодирование адресов
yandex_geocoder / google_maps
```

### Платежи
```python
# Онлайн оплата
YooKassa / Stripe
```

### Push-уведомления
```python
# Для водителей
Firebase Cloud Messaging
```

### Аналитика
```python
# Метрики и дашборды
Prometheus + Grafana
```

## Тестирование

### Юнит-тесты
```bash
pytest tests/
```

### Интеграционные тесты
- Тестирование handlers с mock Telegram API
- Тестирование services с test database

### Нагрузочное тестирование
- Одновременные заказы
- Множество водителей онлайн
- Пиковые нагрузки

## Мониторинг

### Логи
```python
# Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Настройка: .env → LOG_LEVEL
```

### Метрики
- Количество активных пользователей
- Количество заказов в час
- Среднее время ожидания водителя
- Средний рейтинг водителей

### Алерты
- Ошибки в боте
- Отсутствие онлайн водителей
- Долгие ожидающие заказы

---

## 🔧 Для разработчиков

### Добавление новой команды

1. Создайте handler в соответствующем файле
2. Зарегистрируйте в `register_*_handlers()`
3. Добавьте клавиатуру в `keyboards.py` (если нужно)
4. Обновите документацию

### Добавление нового поля в модель

1. Обновите модель в `bot/models/`
2. Создайте миграцию (или удалите БД для dev)
3. Обновите сервисы, использующие модель
4. Обновите отображение в handlers

### Отладка

```python
# В .env установите:
DEBUG=True
LOG_LEVEL=DEBUG

# Запустите:
python run.py

# Логи будут подробные
```

---

Документация актуальна на дату создания проекта.

