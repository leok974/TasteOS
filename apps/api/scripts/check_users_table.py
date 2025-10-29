import sqlite3

conn = sqlite3.connect('tasteos.db')
cursor = conn.cursor()

# Check if users table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
table_exists = cursor.fetchone()

if table_exists:
    print("✓ Users table exists")
    
    # Get table schema
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    
    print("\nColumns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
else:
    print("✗ Users table does not exist!")

conn.close()
