#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-fix script for taxi database
Double-click to run
"""
import sqlite3
import sys
from pathlib import Path
from tkinter import messagebox
import tkinter as tk

def fix_database():
    """Apply database migration"""
    db_path = Path(__file__).parent / "taxi_zhukovo.db"
    
    if not db_path.exists():
        return False, f"Database not found: {db_path}"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        changes = []
        
        # Check and add pickup_district to orders
        cursor.execute("PRAGMA table_info(orders)")
        orders_cols = [col[1] for col in cursor.fetchall()]
        
        if 'pickup_district' not in orders_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN pickup_district TEXT")
            conn.commit()
            changes.append("Added pickup_district to orders table")
        
        # Check and add fields to drivers
        cursor.execute("PRAGMA table_info(drivers)")
        drivers_cols = [col[1] for col in cursor.fetchall()]
        
        if 'current_district' not in drivers_cols:
            cursor.execute("ALTER TABLE drivers ADD COLUMN current_district TEXT")
            conn.commit()
            changes.append("Added current_district to drivers table")
        
        if 'district_updated_at' not in drivers_cols:
            cursor.execute("ALTER TABLE drivers ADD COLUMN district_updated_at TIMESTAMP")
            conn.commit()
            changes.append("Added district_updated_at to drivers table")
        
        conn.close()
        
        if changes:
            return True, "Database updated successfully!\n\n" + "\n".join(f"✓ {c}" for c in changes)
        else:
            return True, "Database is already up to date.\nAll required fields exist."
        
    except Exception as e:
        return False, f"Error updating database:\n{str(e)}"

def main():
    """Main function"""
    root = tk.Tk()
    root.withdraw()
    
    success, message = fix_database()
    
    title = "Database Fix - SUCCESS" if success else "Database Fix - ERROR"
    msg_type = messagebox.showinfo if success else messagebox.showerror
    
    msg_type(title, message + "\n\nYou can now start the bot.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

