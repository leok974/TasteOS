import sqlite3

conn = sqlite3.connect('tasteos.db')
cursor = conn.cursor()

# Check if stripe_customer_id column exists
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

if 'stripe_customer_id' not in columns:
    print("Adding stripe_customer_id column...")
    cursor.execute("ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR")
    conn.commit()
    print("✓ Column added successfully!")
else:
    print("✓ stripe_customer_id column already exists")

conn.close()
