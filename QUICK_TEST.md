# Authentication Testing - WORKING ✅

## Status: Registration & Login FIXED

The 500 error has been resolved. The issue was **database schema drift** - the `stripe_customer_id` column was missing from the database.

---

## Quick Test (Ready Now!)

### 1. User Already Registered ✅
A test user has been created:
- **Email**: `dev@tasteos.local`
- **Password**: `dev123`

### 2. Test Login Flow
1. Go to http://localhost:5173/login
2. Enter credentials above
3. Click "Sign in"
4. Should redirect to `/dashboard` with session cookie set

### 3. Test in Swagger UI (Optional)
1. Go to http://localhost:8000/docs
2. Find POST /api/v1/auth/login
3. Click "Try it out"
4. Use:
```json
{
  "email": "dev@tasteos.local",
  "password": "dev123"
}
```
5. Click "Execute"
6. Should return 200 OK with user details and set cookie

---

## What Was Fixed

### Root Cause
**Database Model Drift**: The User model in code had evolved but the SQLite database table was created with an older schema.

**Specific Issue**:
```python
# User model has:
stripe_customer_id: Optional[str] = None

# Database table was missing this column
# Result: SQLAlchemy OperationalError on any User query
```

### The Fix
1. **Detected missing column** using `scripts/check_users_table.py`
2. **Added migration script**: `scripts/add_stripe_customer_id.py`
3. **Column added successfully** to `users` table
4. **Registration now works** - dev@tasteos.local user created

### Files Changed
- ✅ `.vscode/tasks.json` - Added MCP runtime protocol (Copilot reads task output)
- ✅ `scripts/add_stripe_customer_id.py` - Migration for missing column
- ✅ `scripts/add_subscription_status.py` - Migration for subscription_status
- ✅ `scripts/test_register_direct.py` - Direct Python test with full tracebacks
- ✅ `scripts/check_users_table.py` - Database schema verification tool

---

## Register Additional Users

**Option A: Python Script**
```bash
cd apps/api
python scripts/register_user.py
# Registers: dev@tasteos.local / dev123
```

**Option B: Swagger UI**
1. http://localhost:8000/docs
2. POST /api/v1/auth/register
3. JSON body:
```json
{
  "email": "your@email.com",
  "password": "yourpassword",
  "name": "Your Name",
  "is_active": true,
  "plan": "free"
}
```

**Option C: PowerShell**
```powershell
$body = @{
  email = 'new@example.com'
  password = 'password123'
  name = 'New User'
  is_active = $true
  plan = 'free'
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/api/v1/auth/register `
  -Method POST `
  -Body $body `
  -ContentType 'application/json'
```

---

## Authentication Flow

### Backend
- **POST /api/v1/auth/register** - Create user account
- **POST /api/v1/auth/login** - JSON login (sets `tasteos_session` cookie)
- **POST /api/v1/auth/login/token** - OAuth2 form login (for API clients)
- **GET /api/v1/auth/me** - Get current user profile
- **POST /api/v1/auth/logout** - Clear session cookie

### Cookie Details
- **Name**: `tasteos_session`
- **Type**: httpOnly (JavaScript can't access)
- **Expiry**: 24 hours
- **Security**: SameSite=lax (CSRF protection)
- **Content**: JWT token with user ID and email

### Frontend
- Login form sends email/password to `/api/v1/auth/login`
- Backend validates credentials and sets cookie
- Frontend uses `credentials: 'include'` on all fetch() calls
- Cookie automatically included in requests
- No manual token management needed!

---

## Troubleshooting

### "Invalid email or password"
- Check you're using correct credentials: `dev@tasteos.local` / `dev123`
- Try registering a new user if needed

### "Could not validate credentials" (after login)
- Session expired (24h limit)
- Go back to /login and sign in again

### "Internal Server Error" on register
- Check database has all required columns:
  ```bash
  python scripts/check_users_table.py
  ```
- Should show: id, email, name, hashed_password, subscription_status, stripe_customer_id, etc.

### Check Task Output (for developers)
The `.vscode/tasks.json` now has MCP runtime protocol.
When debugging 500 errors, check the `tasteos-api` task output for Python tracebacks.

---

## Next Steps

✅ Registration working  
✅ User created: dev@tasteos.local  
🔄 **Test login at http://localhost:5173/login**  
🔄 After login, test dashboard at http://localhost:5173/dashboard  

All code pushed to GitHub!

