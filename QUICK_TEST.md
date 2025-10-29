# Quick Test Instructions

## The Issue
The API server needs to be restarted to pick up the code changes for the `subscription_status` field.

## To Test Registration

### 1. Restart the API Server
Stop and restart the `tasteos-api` task in VS Code to reload the updated code.

### 2. Register a Test User

**Option A: Use Swagger UI**
1. Go to http://localhost:8000/docs
2. Find POST /api/v1/auth/register
3. Click "Try it out"
4. Use this JSON:
```json
{
  "email": "dev@tasteos.local",
  "password": "dev123",
  "name": "Dev User",
  "is_active": true,
  "plan": "free"
}
```
5. Click "Execute"
6. Should get 200 OK with user details

**Option B: Use Python Script**
```bash
cd apps/api
python scripts/register_user.py
```

### 3. Test Login
1. Go to http://localhost:5173/login
2. Enter:
   - Email: `dev@tasteos.local`
   - Password: `dev123`
3. Click "Sign in"
4. Should redirect to /dashboard with session cookie set

## What Was Fixed
- Added `subscription_status` field to database (was missing)
- Updated auth router to explicitly pass `subscription_status` when creating users
- Database schema is now correct with all required columns

## Files Changed
- `tasteos_api/routers/auth.py` - Explicitly set subscription_status
- `scripts/add_subscription_status.py` - Migration to add missing column
- `scripts/check_users_table.py` - Helper to verify DB schema
- `scripts/test_register.py` - Helper to test registration endpoint
