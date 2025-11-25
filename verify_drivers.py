#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Проверка наличия водителей в базе по списку из add_bulk_drivers.py
"""

from database.db import SessionLocal
from bot.models import User, Driver, UserRole

from add_bulk_drivers import DRIVERS, normalize


def main() -> None:
    db = SessionLocal()
    try:
        missing_users = []
        missing_drivers = []

        for data in DRIVERS:
            telegram_id = int(data["telegram_id"])
            user = db.query(User).filter(User.telegram_id == telegram_id).first()

            if user is None:
                missing_users.append(telegram_id)
                continue

            driver = db.query(Driver).filter(Driver.user_id == user.id).first()
            if driver is None:
                missing_drivers.append(telegram_id)
                continue

            issues = []
            if user.role != UserRole.DRIVER:
                issues.append(f"роль {user.role.value}")

            expected_car_model = normalize(data.get("car_model")) or ""
            if expected_car_model and normalize(driver.car_model) != expected_car_model:
                issues.append(f"модель авто: '{driver.car_model}' вместо '{expected_car_model}'")

            expected_car_number = normalize(data.get("car_number")) or ""
            if expected_car_number and normalize(driver.car_number) != expected_car_number:
                issues.append(f"номер авто: '{driver.car_number}' вместо '{expected_car_number}'")

            expected_car_color = normalize(data.get("car_color"))
            if expected_car_color and normalize(driver.car_color) != expected_car_color:
                issues.append(f"цвет авто: '{driver.car_color}' вместо '{expected_car_color}'")

            phone = normalize(data.get("phone_number"))
            expected_license = phone or "нет данных"
            if normalize(driver.license_number) != expected_license:
                issues.append(
                    f"контакт: '{driver.license_number}' вместо '{expected_license}'"
                )

            if issues:
                print(f"⚠️ Telegram ID {telegram_id}: {', '.join(issues)}")
            else:
                print(f"✅ Telegram ID {telegram_id}: всё совпадает")

        if not missing_users and not missing_drivers:
            print("\nИтог: все водители найдены в базе.")
        else:
            print("\nИтог:")
            if missing_users:
                print(f"  ❌ Нет пользователя для Telegram ID: {', '.join(map(str, missing_users))}")
            if missing_drivers:
                print(f"  ❌ Нет карточки водителя для Telegram ID: {', '.join(map(str, missing_drivers))}")
    finally:
        db.close()


if __name__ == "__main__":
    main()


