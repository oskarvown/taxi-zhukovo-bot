#!/usr/bin/env python
import sqlite3
import sys
from pathlib import Path

def main():
    db_path = Path("taxi_zhukovo.db")
    
    if not db_path.exists():
        print("ERROR: Database not found")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    success = True
    
    try:
        # Check orders table
        cursor.execute("PRAGMA table_info(orders)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'pickup_district' not in columns:
            print("Adding pickup_district...")
            cursor.execute("ALTER TABLE orders ADD COLUMN pickup_district TEXT")
            conn.commit()
            print("SUCCESS")
        else:
            print("pickup_district already exists")
        
        # Check drivers table
        cursor.execute("PRAGMA table_info(drivers)")
        driver_cols = [col[1] for col in cursor.fetchall()]
        
        if 'current_district' not in driver_cols:
            print("Adding current_district...")
            cursor.execute("ALTER TABLE drivers ADD COLUMN current_district TEXT")
            conn.commit()
            print("SUCCESS")
        else:
            print("current_district already exists")
        
        if 'district_updated_at' not in driver_cols:
            print("Adding district_updated_at...")
            cursor.execute("ALTER TABLE drivers ADD COLUMN district_updated_at TIMESTAMP")
            conn.commit()
            print("SUCCESS")
        else:
            print("district_updated_at already exists")
        
        print("\nDONE! Database updated successfully")
        
    except Exception as e:
        print(f"ERROR: {e}")
        success = False
    finally:
        conn.close()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

