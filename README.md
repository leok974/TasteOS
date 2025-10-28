# 🍳 TasteOS

An agentic recipe engine that transforms cooking with AI-powered recipe variants, intelligent suggestions, and personalized culinary experiences.

## 🚀 Quick Start

```bash
# Install dependencies
pnpm install

# Start all development servers
pnpm dev

# Or start individual apps
pnpm dev:web   # Marketing site (http://localhost:3000)
pnpm dev:app   # Dashboard app (http://localhost:5173)
pnpm dev:api   # Backend API (http://localhost:8000)
```

## 📦 Monorepo Structure

```
tasteos/
├── apps/
│   ├── web/         # Next.js marketing site
│   ├── app/         # Vite + React dashboard
│   └── api/         # FastAPI + LangGraph backend
├── packages/
│   ├── design/      # Design tokens & Tailwind preset
│   ├── ui/          # Shared React components
│   ├── types/       # TypeScript type definitions
│   └── config/      # Shared tooling configurations
└── tests/
    └── e2e/         # Playwright end-to-end tests
```

## 🛠️ Available Scripts

- `pnpm dev` - Start all development servers
- `pnpm build` - Build all apps and packages
- `pnpm test` - Run all tests
- `pnpm lint` - Lint all code
- `pnpm typecheck` - Run TypeScript checks
- `pnpm e2e` - Run end-to-end tests
- `pnpm format` - Format code with Prettier

## 🔧 Development

### Prerequisites

- Node.js 18+
- pnpm 8+
- Python 3.11+ (for API)
- PostgreSQL (for production)

### Environment Setup

1. Copy `.env.example` to `.env` and configure your environment variables
2. Install dependencies: `pnpm install`
3. Set up the database (see `apps/api/README.md`)
4. Start development servers: `pnpm dev`

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Documentation](apps/api/README.md)
- [Frontend Development](apps/app/README.md)
- [Design System](packages/design/README.md)

## 🧪 Testing

- **Unit Tests**: `pnpm test:unit`
- **API Tests**: `pnpm test:api`
- **E2E Tests**: `pnpm e2e`

## 🔒 Security

Run security scans with:
```bash
pnpm security:scan
```

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## 📄 License

Private - All rights reserved.
