import sqlite3
import os

db_path = 'instance/database.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Try to add the is_active column
        cursor.execute("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1")
        conn.commit()
        print("Successfully added 'is_active' column to the database.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'is_active' already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database not found at {db_path}. It will be created when you run the app.")
