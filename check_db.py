#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Простая проверка БД"""
import sqlite3
import sys

try:
    print("Connecting to database...")
    conn = sqlite3.connect('taxi_zhukovo.db')
    cursor = conn.cursor()
    
    print("\n=== ORDERS TABLE STRUCTURE ===")
    cursor.execute("PRAGMA table_info(orders)")
    for col in cursor.fetchall():
        print(f"{col[1]:25} {col[2]}")
    
    print("\n=== ORDERS STATISTICS ===")
    cursor.execute("SELECT COUNT(*) FROM orders")
    print(f"Total orders: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NOT NULL")
    print(f"Orders with driver: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    print(f"Completed orders: {cursor.fetchone()[0]}")
    
    print("\n=== LAST 5 ORDERS ===")
    cursor.execute("""
        SELECT id, customer_id, driver_id, status, price, created_at
        FROM orders ORDER BY id DESC LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"Order #{row[0]}: customer={row[1]}, driver={row[2]}, status={row[3]}, price={row[4]}")
    
    print("\n=== DRIVERS ===")
    cursor.execute("""
        SELECT
            d.id,
            d.user_id,
            TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
            d.total_rides,
            d.status,
            d.current_zone,
            d.online_since
        FROM drivers d
        JOIN users u ON d.user_id = u.id
    """)
    for row in cursor.fetchall():
        driver_id, user_id, name, rides, status, zone, online_since = row
        cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id = ?", (user_id,))
        orders_count = cursor.fetchone()[0]
        print(f"Driver: {name} (user_id={user_id}, driver_id={driver_id})")
        print(f"  Status: {status}, zone: {zone}, online_since: {online_since}")
        print(f"  Total rides in profile: {rides}")
        print(f"  Orders in DB: {orders_count}")
    
    conn.close()
    print("\n=== CHECK COMPLETE ===")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

