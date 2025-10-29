# TasteOS API Scripts

Utility scripts for database management and development workflows.

## Database Scripts

### `recreate_db.py`

Recreates the production database using Alembic migrations.

**When to use:**
- Switching from `SQLModel.metadata.create_all()` to Alembic-managed schema
- Starting fresh with a clean database
- After modifying models and generating new migrations

**What it does:**
1. Backs up existing `tasteos.db` with timestamp
2. Deletes old database
3. Runs `alembic upgrade head` to create fresh schema
4. Verifies database was created successfully

**Usage:**
```bash
cd apps/api
python scripts/recreate_db.py
```

**Prerequisites:**
- Stop all running API processes (database must not be locked)
- Ensure Alembic is configured and migrations exist

**Output:**
- New `tasteos.db` with migration-tracked schema
- Backup file: `tasteos.db.backup.YYYYMMDD_HHMMSS`

## Migration Workflow

### Creating New Migrations

When you modify models:

```bash
# Auto-generate migration from model changes
python -m alembic revision --autogenerate -m "Description of changes"

# Review generated migration in alembic/versions/
# Edit if needed (Alembic isn't perfect with auto-generation)

# Apply migration
python -m alembic upgrade head
```

### Checking Migration Status

```bash
# Show current migration version
python -m alembic current

# Show migration history
python -m alembic history

# Show pending migrations
python -m alembic show head
```

### Rolling Back Migrations

```bash
# Rollback one migration
python -m alembic downgrade -1

# Rollback to specific revision
python -m alembic downgrade <revision_id>

# Rollback all migrations
python -m alembic downgrade base
```

## Development Workflow

### Local Development with Auto-Reload

```bash
# Use SQLModel.metadata.create_all() for quick iteration
# Database schema auto-updates on model changes
pnpm dev:api
```

### Pre-Production Testing

```bash
# Recreate database with migrations
python scripts/recreate_db.py

# Start API (should NOT call metadata.create_all())
pnpm dev:api

# Verify all endpoints work
# Check that schema matches models
```

### Production Deployment

```bash
# On production server
python -m alembic upgrade head

# Start API
# Database schema is managed by migrations only
```

## Best Practices

### ✅ DO:
- Generate migrations for all schema changes
- Review auto-generated migrations before applying
- Test migrations on development database first
- Keep migration messages clear and descriptive
- Commit migration files to version control
- Run `alembic upgrade head` on production deploys

### ❌ DON'T:
- Call `SQLModel.metadata.create_all()` in production
- Edit applied migrations (create new ones instead)
- Skip migration generation for model changes
- Delete migration files from version control
- Run migrations without backups (especially in production)

## Troubleshooting

### Database is Locked

```bash
# Windows
Get-Process python | Where-Object {$_.Path -like "*TasteOS*"} | Stop-Process -Force

# Linux/Mac
killall python
# or
lsof tasteos.db  # Find process ID
kill <PID>
```

### Migration Out of Sync

```bash
# Database has changes not in migrations
# Option 1: Stamp current state
python -m alembic stamp head

# Option 2: Recreate from scratch
python scripts/recreate_db.py
```

### Merge Conflicts in Migrations

```bash
# When multiple branches create migrations
# Alembic can create a merge migration
python -m alembic merge -m "Merge migrations" <rev1> <rev2>
python -m alembic upgrade head
```

## CI/CD Integration

GitHub Actions automatically runs tests with in-memory database:

```yaml
- name: Run pytest
  run: pytest tasteos_api/tests -q -m "phase3 or phase4"
  env:
    DATABASE_URL: "sqlite+aiosqlite:///:memory:"
```

Tests don't need migrations - schema is created from models in memory.

## Additional Scripts (Coming Soon)

- `seed_dev_data.py` - Populate database with test data
- `export_db.py` - Export database to SQL/JSON
- `import_db.py` - Import data from SQL/JSON
- `check_migrations.py` - Verify migrations match model state
