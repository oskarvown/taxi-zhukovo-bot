#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Пакетное добавление водителей в систему.

Скрипт проходит по заранее подготовленному списку и:
  * создаёт пользователя, если он ещё не существует;
  * обновляет ФИО и телефон, если они изменились;
  * выставляет роль DRIVER;
  * создаёт/обновляет карточку водителя в таблице drivers.
"""

from typing import Optional
from database.db import SessionLocal
from bot.models import User, UserRole, Driver


DRIVERS = [
    {
        "telegram_id": 607454650,
        "first_name": "Алексей",
        "last_name": "Романов",
        "car_model": "Toyota Raize",
        "car_number": "Н364ТА702",
        "car_color": "белая",
        "phone_number": "+79876066226",
    },
    {
        "telegram_id": 5101540378,
        "first_name": "Сергей",
        "last_name": "Романов",
        "car_model": "Toyota Corolla Fielder",
        "car_number": "Х245ЕС102",
        "car_color": "серебристая",
        "phone_number": "+79173417406",
    },
    {
        "telegram_id": 6528784715,
        "first_name": "Рустам",
        "last_name": "Бекчанов",
        "car_model": "Skoda Octavia",
        "car_number": "М572ХВ702",
        "car_color": "бежевый",
        "phone_number": "+79603877711",
    },
    {
        "telegram_id": 6197116910,
        "first_name": "Альберт",
        "last_name": "Арсланов",
        "car_model": "Honda Elysion",
        "car_number": "Н532СТ702",
        "car_color": "белый",
        "phone_number": "+79279259777",
    },
    {
        "telegram_id": 7344314105,
        "first_name": "Марсель",
        "last_name": "Гайсин",
        "car_model": "Renault Logan",
        "car_number": "Н544ХТ702",
        "car_color": "бежевый",
        "phone_number": "+79177933819",
    },
    {
        "telegram_id": 5165965562,
        "first_name": "Дмитрий",
        "last_name": "Зотов",
        "car_model": "LADA Largus",
        "car_number": "О231НМ102",
        "car_color": "серый базальт",
        "phone_number": "+79378346076",
    },
    {
        "telegram_id": 2081837977,
        "first_name": "Азамат",
        "last_name": "Уразметов",
        "car_model": "LADA Granta лифтбек",
        "car_number": "У189МА102",
        "car_color": "коричневый",
        "phone_number": "+79374874052",
    },
    {
        "telegram_id": 6743690171,
        "first_name": "Андрей",
        "last_name": "Пешкин",
        "car_model": "Chery Tiggo",
        "car_number": "В714НУ702",
        "car_color": "серый",
        "phone_number": "+79033501854",
    },
    {
        "telegram_id": 1734061742,
        "first_name": "Халяф",
        "last_name": "Кутлубаев",
        "car_model": "LADA Largus",
        "car_number": "Х954НА102",
        "car_color": "чёрный",
        "phone_number": "+79279655502",
    },
    {
        "telegram_id": 7003530057,
        "first_name": "Big",
        "last_name": "Boss",
        "car_model": "LIFAN",
        "car_number": "Р633ВА102",
        "car_color": "белый",
        "phone_number": None,
    },
    {
        "telegram_id": 7565514586,
        "first_name": "Николай",
        "last_name": "Вышеславцев",
        "car_model": "Nissan Qashqai",
        "car_number": "В925ХУ102",
        "car_color": "чёрный",
        "phone_number": "+79174591133",
    },
    {
        "telegram_id": 6951240964,
        "first_name": "Анатолий",
        "last_name": "Карявка",
        "car_model": "ВАЗ 21101",
        "car_number": "К155НВ702",
        "car_color": "серо-зеленый",
        "phone_number": "+79996232394",
    },
    {
        "telegram_id": 5132562123,
        "first_name": "Айдар",
        "last_name": "Давлетов",
        "car_model": "LADA Granta",
        "car_number": "Х209СА102",
        "car_color": "синий",
        "phone_number": "+79870330649",
    },
    {
        "telegram_id": 1605116199,
        "first_name": "Дмитрий",
        "last_name": "Азинов",
        "car_model": "KIA CERATO",
        "car_number": "У903СХ102",
        "car_color": "черный",
        "phone_number": "+79196008708",
    },
    {
        "telegram_id": 7361775496,
        "first_name": "Марат",
        "last_name": "Валеев",
        "car_model": "Nissan Almera Classic",
        "car_number": "В040КС102",
        "car_color": "серебристый",
        "phone_number": "+79656627573",
    },
    {
        "telegram_id": 5573448051,
        "first_name": "Улугбек",
        "last_name": "Мустафакулов",
        "car_model": "KIA RIO",
        "car_number": "Е363ЕВ702",
        "car_color": "светло серебристый",
        "phone_number": "+79870579787",
    },
]


def normalize(value: Optional[str]) -> Optional[str]:
    """Стандартизует строку: убирает лишние пробелы и точки."""
    if not value:
        return None
    return value.strip().strip(".")


def add_or_update_driver(db, data: dict) -> None:
    """Создать или обновить водителя по данным из списка."""
    telegram_id = int(data["telegram_id"])

    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=normalize(data.get("first_name")),
            last_name=normalize(data.get("last_name")),
            username=None,
            phone_number=normalize(data.get("phone_number")),
            role=UserRole.DRIVER,
        )
        db.add(user)
        db.flush()  # получаем user.id без коммита
        print(f"✓ Создан новый пользователь: {user.full_name}")
    else:
        updated = False
        first_name = normalize(data.get("first_name"))
        last_name = normalize(data.get("last_name"))
        phone_number = normalize(data.get("phone_number"))

        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if phone_number and user.phone_number != phone_number:
            user.phone_number = phone_number
            updated = True
        if user.role != UserRole.DRIVER:
            user.role = UserRole.DRIVER
            updated = True

        if updated:
            print(f"✓ Обновлена информация пользователя: {user.full_name}")
        else:
            print(f"✓ Пользователь уже актуален: {user.full_name}")

    driver = db.query(Driver).filter(Driver.user_id == user.id).first()

    license_number = normalize(data.get("phone_number")) or "нет данных"

    if driver is None:
        driver = Driver(
            user_id=user.id,
            car_model=normalize(data.get("car_model")) or "—",
            car_number=normalize(data.get("car_number")) or "—",
            car_color=normalize(data.get("car_color")),
            license_number=license_number,
            is_verified=True,
        )
        db.add(driver)
        print(f"  ▸ Добавлена карточка водителя для {user.full_name}")
    else:
        driver.car_model = normalize(data.get("car_model")) or driver.car_model
        driver.car_number = normalize(data.get("car_number")) or driver.car_number
        driver.car_color = normalize(data.get("car_color"))
        driver.license_number = license_number
        driver.is_verified = True
        print(f"  ▸ Обновлена карточка водителя для {user.full_name}")


def main() -> None:
    db = SessionLocal()
    try:
        for item in DRIVERS:
            add_or_update_driver(db, item)
        db.commit()
        print("\nВсе водители успешно обработаны и сохранены.")
    except Exception as exc:
        db.rollback()
        print(f"\n❌ Ошибка при добавлении водителей: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()


