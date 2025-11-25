#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Вывод всех пользователей из БД"""
import sqlite3

conn = sqlite3.connect('taxi_zhukovo.db')
conn.row_factory = sqlite3.Row
cur = conn.execute(
    "SELECT id, telegram_id, first_name, last_name, phone_number, role, is_active "
    "FROM users ORDER BY id"
)

print("=" * 80)
print("СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ")
print("=" * 80)

for row in cur:
    print(f"\nUser #{row['id']}:")
    print(f"  Telegram ID: {row['telegram_id']}")
    print(f"  Имя: {row['first_name']} {row['last_name']}")
    print(f"  Телефон: {row['phone_number'] or 'не указан'}")
    print(f"  Роль: {row['role']}")
    print(f"  Активен: {'Да' if row['is_active'] else 'Нет'}")

conn.close()
print("\n" + "=" * 80)

