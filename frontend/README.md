# Batchivo Frontend

React 19 + TypeScript + Vite frontend for the Batchivo 3D printing business management platform.

## Tech Stack

- **React 19** - UI library with modern features
- **TypeScript 5.9** - Type-safe development
- **Vite 7** - Fast build tool and dev server
- **TanStack Query** - Server state management
- **TanStack Router** - Type-safe routing
- **shadcn/ui** - Component library (Radix UI + Tailwind)
- **Tailwind CSS 3.4** - Utility-first styling
- **React Hook Form + Zod** - Form handling and validation

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── ui/          # shadcn/ui primitives
│   │   └── ...          # Feature components
│   ├── hooks/           # Custom React hooks
│   ├── lib/
│   │   ├── api/         # API client and queries
│   │   └── utils/       # Utility functions
│   ├── pages/           # Route page components
│   ├── routes/          # TanStack Router definitions
│   ├── types/           # TypeScript type definitions
│   └── main.tsx         # Application entry point
├── public/              # Static assets
├── e2e/                 # Playwright E2E tests
└── ...config files
```

## Development

### Prerequisites

- Node.js 20+ (LTS)
- pnpm 8+ (recommended) or npm 9+

### Setup

```bash
# Install dependencies
pnpm install

# Copy environment template
cp .env.example .env

# Start development server
pnpm dev
```

The app will be available at http://localhost:5173

### Environment Variables

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_API_BASE_PATH=/api/v1

# Feature Flags (optional)
VITE_ENABLE_QR_SCANNER=true
VITE_ENABLE_INTEGRATIONS=false
```

## Scripts

| Command | Description |
|---------|-------------|
| `pnpm dev` | Start development server |
| `pnpm build` | Build for production |
| `pnpm preview` | Preview production build |
| `pnpm lint` | Run ESLint |
| `pnpm typecheck` | Run TypeScript type checking |
| `pnpm test` | Run unit tests (Vitest) |
| `pnpm test:coverage` | Run tests with coverage |
| `pnpm test:e2e` | Run E2E tests (Playwright) |

## Architecture

### State Management

- **Server State**: TanStack Query for all API data
- **Client State**: React Context for auth/theme, local state for UI

### API Integration

API client is in `src/lib/api/`. Uses TanStack Query for:
- Automatic caching and background refetching
- Optimistic updates
- Request deduplication

### Component Guidelines

- Use shadcn/ui components as base
- Follow existing patterns in `src/components/`
- Keep components focused and composable
- Use TypeScript strictly (no `any`)

### Styling

- Tailwind CSS utility classes
- Component variants via `class-variance-authority`
- Dark mode support via CSS variables

## Testing

### Unit Tests (Vitest)

```bash
# Run tests
pnpm test

# Run in watch mode
pnpm test -- --watch

# With coverage
pnpm test:coverage
```

### E2E Tests (Playwright)

```bash
# Install browsers (first time)
pnpm exec playwright install

# Run E2E tests
pnpm test:e2e

# Run with UI
pnpm test:e2e:ui
```

## Production Build

```bash
# Build optimized bundle
pnpm build

# Preview locally
pnpm preview
```

Build output is in `dist/` directory.

## Docker

```bash
# Build Docker image
docker build -t batchivo-frontend .

# Run container
docker run -p 8080:8080 batchivo-frontend
```

The Docker image uses nginx to serve the static build.

## Related Documentation

- [Main README](../README.md) - Project overview
- [Development Guide](../docs/DEVELOPMENT.md) - Full setup instructions
- [Architecture](../docs/ARCHITECTURE.md) - System design
- [Contributing](../CONTRIBUTING.md) - Contribution guidelines
