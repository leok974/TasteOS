#!/usr/bin/env python3
"""
Initialize database tables for TasteOS API.

Creates all tables defined in SQLModel models.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import tasteos_api
sys.path.insert(0, str(Path(__file__).parent.parent))

from tasteos_api.core.database import init_db


async def main():
    """Run database initialization."""
    print("Initializing database tables...")
    try:
        await init_db()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
