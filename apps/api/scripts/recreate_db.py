"""
Recreate production database with Alembic migrations.

This script:
1. Backs up the existing database (if it exists)
2. Deletes the old database
3. Runs Alembic migrations to create fresh schema

Run this to switch from SQLModel.metadata.create_all() to Alembic-managed schema.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Get the database path
DB_PATH = Path(__file__).parent / "tasteos.db"
BACKUP_PATH = Path(__file__).parent / f"tasteos.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def main():
    print("🔄 TasteOS Database Recreation Script")
    print("=" * 50)

    # Check if database exists
    if DB_PATH.exists():
        print(f"✓ Found existing database: {DB_PATH}")

        # Backup
        print(f"📦 Creating backup: {BACKUP_PATH}")
        try:
            import shutil
            shutil.copy2(DB_PATH, BACKUP_PATH)
            print(f"✓ Backup created successfully")
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            print("⚠️  Continuing without backup...")

        # Delete old database
        print(f"🗑️  Deleting old database...")
        try:
            DB_PATH.unlink()
            print(f"✓ Old database deleted")
        except PermissionError:
            print(f"❌ Cannot delete database - it's locked by another process")
            print(f"⚠️  Please stop any running API servers and try again")
            print(f"\nTo stop Python processes manually:")
            print(f"  Windows: Get-Process python | Stop-Process -Force")
            print(f"  Linux/Mac: killall python")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Failed to delete database: {e}")
            sys.exit(1)
    else:
        print(f"ℹ️  No existing database found at {DB_PATH}")

    # Run Alembic upgrade
    print(f"\n🔨 Running Alembic migrations...")
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print(f"✓ Migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

    # Verify database was created
    if DB_PATH.exists():
        print(f"\n✅ SUCCESS: Database recreated with Alembic migrations")
        print(f"📊 Database location: {DB_PATH}")
        if BACKUP_PATH.exists():
            print(f"💾 Backup location: {BACKUP_PATH}")
        print(f"\n🎯 Next steps:")
        print(f"   1. Remove SQLModel.metadata.create_all() calls from startup")
        print(f"   2. Use 'alembic upgrade head' for all future schema changes")
        print(f"   3. Run API and verify everything works")
    else:
        print(f"\n❌ FAILED: Database was not created")
        sys.exit(1)

if __name__ == "__main__":
    main()
