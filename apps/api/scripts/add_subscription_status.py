import sqlite3

conn = sqlite3.connect('tasteos.db')
cursor = conn.cursor()

# Check if subscription_status column exists
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

if 'subscription_status' not in columns:
    print("Adding subscription_status column...")
    cursor.execute("ALTER TABLE users ADD COLUMN subscription_status VARCHAR DEFAULT 'active'")
    conn.commit()
    print("✓ Column added successfully!")
else:
    print("✓ subscription_status column already exists")

conn.close()
