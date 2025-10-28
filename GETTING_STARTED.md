# 🚀 TasteOS Setup Guide

This guide will help you get TasteOS up and running on your local machine.

## Prerequisites

- **Node.js** 18+ and **pnpm** 8+ (JavaScript/TypeScript)
- **Python** 3.11+ (for the API)
- **PostgreSQL** (optional, can use SQLite for development)

## Quick Start

### 1. Install Python Dependencies

Run the PowerShell setup script:

```powershell
.\setup-api.ps1
```

Or manually:

```powershell
cd apps/api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required for API
DATABASE_URL=sqlite:///./tasteos.db
JWT_SECRET=your-secret-key-change-in-production
OPENAI_API_KEY=your-openai-key

# Optional for full features
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 3. Start Development Servers

Start all services at once:

```bash
pnpm dev
```

Or start individually:

```bash
# Marketing site (Next.js)
pnpm dev:web   # → http://localhost:3000

# Dashboard (Vite + React)
pnpm dev:app   # → http://localhost:5173

# API (FastAPI)
pnpm dev:api   # → http://localhost:8000
```

### 4. Access the Applications

- **Marketing Site**: http://localhost:3000
- **Dashboard App**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/api/v1/ready

## What's Implemented

### ✅ Completed Features

#### Backend API
- ✅ User registration and authentication with JWT
- ✅ Login/logout with secure password hashing
- ✅ Recipe CRUD operations (Create, Read, Update, Delete)
- ✅ Recipe filtering by cuisine and difficulty
- ✅ User authorization and access control
- ✅ Database models for User, Recipe, and Variant
- ✅ Health check endpoints

#### Database
- ✅ SQLModel ORM setup with async support
- ✅ User model with authentication fields
- ✅ Recipe model with JSON fields for complex data
- ✅ Variant model for AI-generated alternatives
- ✅ Database auto-initialization

#### Frontend Structure
- ✅ Next.js marketing site with Tailwind CSS
- ✅ Vite React dashboard with routing
- ✅ Shared design system with brand colors
- ✅ Shared UI component library
- ✅ TypeScript types for all entities

### 🚧 To Be Implemented

#### High Priority
- [ ] Recipe variant generation with LangGraph
- [ ] AI-powered recipe import from URLs
- [ ] Cooking session tracking
- [ ] Recipe diff visualization
- [ ] User preferences and dietary restrictions

#### Medium Priority
- [ ] Stripe subscription integration
- [ ] Usage tracking and billing
- [ ] Recipe search and advanced filtering
- [ ] Recipe images upload
- [ ] Social features (sharing, reviews)

#### Lower Priority
- [ ] Email notifications
- [ ] Analytics dashboard
- [ ] Mobile responsiveness improvements
- [ ] PWA features

## Testing Your Setup

### 1. Test the API

Open http://localhost:8000/docs in your browser to see the interactive API documentation.

Try the health check:

```bash
curl http://localhost:8000/api/v1/ready
```

### 2. Register a User

Using the API docs at `/docs`, or with curl:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "name": "Test User",
    "password": "password123"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"
```

Save the returned `access_token` for subsequent requests.

### 4. Create a Recipe

```bash
curl -X POST http://localhost:8000/api/v1/recipes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "Simple Pasta",
    "description": "A quick and easy pasta dish",
    "servings": 4,
    "prep_time": 10,
    "cook_time": 15,
    "difficulty": "easy",
    "cuisine": "italian",
    "tags": ["pasta", "quick", "easy"],
    "ingredients": [
      {
        "name": "pasta",
        "amount": 400,
        "unit": "g"
      },
      {
        "name": "olive oil",
        "amount": 2,
        "unit": "tbsp"
      }
    ],
    "instructions": [
      {
        "stepNumber": 1,
        "description": "Boil water and cook pasta"
      },
      {
        "stepNumber": 2,
        "description": "Drain and toss with olive oil"
      }
    ]
  }'
```

## Development Workflow

### Running Type Checks

```bash
pnpm typecheck
```

### Linting

```bash
pnpm lint
```

### Formatting

```bash
pnpm format
```

### Running Tests

```bash
# All tests
pnpm test

# Frontend unit tests
pnpm test:unit

# API tests (when implemented)
pnpm test:api

# E2E tests
pnpm e2e
```

## Troubleshooting

### Python Module Not Found

Make sure you've activated the virtual environment:

```powershell
.\apps\api\venv\Scripts\Activate.ps1
```

Then reinstall dependencies:

```powershell
pip install -r apps/api/requirements.txt
```

### TypeScript Errors

Install all dependencies:

```bash
pnpm install
```

### Database Issues

The default SQLite database will be created automatically. To reset it:

```powershell
rm apps/api/tasteos.db
```

Then restart the API server.

### Port Already in Use

If ports 3000, 5173, or 8000 are in use, you can change them:

- **Web**: Edit `apps/web/package.json` dev script
- **App**: Edit `apps/app/vite.config.ts` server port
- **API**: Edit `apps/api/tasteos_api/main.py` uvicorn port

## Next Steps

Now that your environment is set up, you can:

1. **Implement AI Features**: Add LangGraph workflows for variant generation
2. **Build Frontend Components**: Create recipe cards, forms, and cooking interfaces
3. **Add Authentication UI**: Build login/signup pages with the API integration
4. **Integrate Stripe**: Set up subscription management
5. **Deploy**: Prepare for production deployment

Check out the main README.md and SETUP_COMPLETE.md for more detailed information about the architecture and implementation priorities.

## Getting Help

- Check the API documentation at `/docs`
- Review type definitions in `packages/types`
- Look at the design system in `packages/design`
- Examine existing router implementations in `apps/api/tasteos_api/routers`

Happy cooking! 🍳✨
