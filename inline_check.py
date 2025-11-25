import sqlite3
conn = sqlite3.connect('taxi_zhukovo.db')
cursor = conn.cursor()

print("=== ORDERS TABLE COLUMNS ===")
cursor.execute("PRAGMA table_info(orders)")
for col in cursor.fetchall():
    print(f"{col[1]:25} {col[2]}")

print("\n=== STATISTICS ===")
cursor.execute("SELECT COUNT(*) FROM orders")
print(f"Total orders: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id IS NOT NULL")
print(f"With driver: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
print(f"Completed: {cursor.fetchone()[0]}")

print("\n=== DRIVERS ===")
cursor.execute("""
    SELECT
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
    user_id, name, rides, status, zone, online_since = row
    cursor.execute("SELECT COUNT(*) FROM orders WHERE driver_id=?", (user_id,))
    orders = cursor.fetchone()[0]
    print(f"{name}: profile_rides={rides}, db_orders={orders}, status={status}, zone={zone}, online_since={online_since}")

conn.close()

