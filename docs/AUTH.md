# Authentication Setup

## Overview

TasteOS now uses cookie-based authentication with email/password login. This provides a better developer experience than JWT token pasting.

## Quick Start

### 1. Start the servers

Run the `tasteos-api` and `tasteos-web` tasks in VS Code.

### 2. Register a test user

```powershell
cd apps/api
python scripts/register_user.py
```

This creates a user with:
- **Email**: `dev@tasteos.local`
- **Password**: `dev123`
- **Name**: Dev User

### 3. Login

1. Go to http://localhost:5173/login
2. Enter the email and password
3. Click "Sign in"
4. You'll be redirected to the dashboard

## How it works

### Backend

- **POST /api/v1/auth/register**: Create a new user account
- **POST /api/v1/auth/login**: Login with JSON `{email, password}` → sets `tasteos_session` cookie
- **POST /api/v1/auth/login/token**: OAuth2-compatible form login (for API clients)
- **POST /api/v1/auth/logout**: Clear session cookie
- **GET /api/v1/auth/me**: Get current user profile

### Authentication Flow

1. User submits email/password to `/api/v1/auth/login`
2. Backend validates credentials
3. Backend creates JWT token
4. Backend sets `tasteos_session` httpOnly cookie (24h expiry)
5. Frontend redirects to dashboard
6. All subsequent API calls include the cookie automatically

### Dual Auth Support

The `get_current_user` dependency accepts both:
- **Cookie**: `tasteos_session` (for browsers)
- **Header**: `Authorization: Bearer <token>` (for API clients)

This means:
- Frontend uses cookies (seamless, no token management)
- API clients can still use Bearer tokens
- Both methods work with all protected endpoints

### Security

- Passwords are hashed with bcrypt (72-byte truncation)
- Cookies are httpOnly (JavaScript can't access them)
- Cookies use SameSite=lax (CSRF protection)
- JWT tokens expire after 24 hours
- Set `secure=True` in production (HTTPS only)

## Development Workflow

### Register yourself

```powershell
# Option 1: Use the script
python apps/api/scripts/register_user.py

# Option 2: Use curl
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "your-password",
    "name": "Your Name"
  }'
```

### Login via browser

1. Go to http://localhost:5173/login
2. Enter email/password
3. Done! Cookie is set automatically

### Login via API client

```bash
# Get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@tasteos.local", "password": "dev123"}' \
  | jq -r '.access_token'

# Use token in subsequent requests
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Troubleshooting

### "500 Internal Server Error" when registering

- Make sure the API server is running (`tasteos-api` task)
- Check the API server terminal for error details
- Try restarting the API server

### "Invalid email or password"

- Check you're using the correct credentials
- Default test user: `dev@tasteos.local` / `dev123`
- Register a new user if needed

### "Could not validate credentials"

- Your session may have expired (24h limit)
- Go back to /login and sign in again
- Check that `credentials: 'include'` is set in fetch() calls

### Cookie not being sent

- Verify frontend is using `credentials: 'include'` in fetch()
- Check CORS settings allow credentials
- Ensure frontend and backend are on compatible origins

## Files Changed

### Backend
- `tasteos_api/routers/auth.py`: Added cookie support, JSON login, logout endpoint
- `tasteos_api/core/dependencies.py`: Updated `get_current_user` to accept cookies
- `tasteos_api/core/database.py`: Added household models to init

### Frontend
- `apps/app/src/routes/login.tsx`: New email/password form with dark theme
- All API calls use `credentials: 'include'`

### Scripts
- `apps/api/scripts/register_user.py`: Helper to create test users
