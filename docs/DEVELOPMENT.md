# Development Guide

**Nozzly - Local Development Setup**

---

## Prerequisites

### Required Software

- **Docker** 20.10+ & **Docker Compose** 2.0+
- **Python** 3.11+
- **Poetry** 1.5+ (Python package manager)
- **Node.js** 20+ (LTS)
- **pnpm** 8+ or **npm** 9+
- **Git** 2.30+

### Optional Tools

- **Make** (for convenient commands)
- **kubectl** (if deploying to k3s)
- **gh** (GitHub CLI)
- **act** (test GitHub Actions locally)

---

## Installation

### macOS

```bash
# Homebrew
brew install python@3.11 poetry node pnpm docker docker-compose git make

# Verify installations
python3 --version  # 3.11+
poetry --version   # 1.5+
node --version     # 20+
pnpm --version     # 8+
docker --version   # 20.10+
```

### Linux (Ubuntu/Debian)

```bash
# Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Node.js & pnpm
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs
npm install -g pnpm

# Docker
sudo apt install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### Windows (WSL2 Required)

Use WSL2 with Ubuntu and follow Linux instructions above.

---

## Project Setup

### 1. Clone Repository

```bash
git clone https://github.com/techize/nozzly.app.git
cd nozzly.app
```

### 2. Start Infrastructure Services

Start PostgreSQL, Redis, Authentik, and observability stack using Docker Compose.

```bash
# Start all services
docker-compose up -d

# Verify all services are healthy
docker-compose ps

# View logs
docker-compose logs -f

# Expected services:
# - postgres (port 5432)
# - redis (port 6379)
# - authentik-server (port 9000)
# - authentik-worker
# - authentik-postgres
# - authentik-redis
# - tempo (port 4317, 3200)
# - prometheus (port 9090)
# - loki (port 3100)
# - grafana (port 3000)
```

**Troubleshooting Docker Services:**

```bash
# If services fail to start, check logs
docker-compose logs postgres
docker-compose logs authentik-server

# Restart a specific service
docker-compose restart postgres

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

### 3. Backend Setup

```bash
cd backend

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# (See "Environment Variables" section below)
nano .env  # or vim, code, etc.

# Initialize database
poetry run alembic upgrade head

# Seed reference data (material types)
poetry run python scripts/seed_data.py

# Run development server
poetry run uvicorn app.main:app --reload --port 8000

# In a new terminal, run Celery worker (for background jobs)
cd backend
poetry run celery -A app.background.celery_app worker --loglevel=info
```

**Backend will be available at:**
- API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- API Docs (ReDoc): http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Run development server
pnpm dev
```

**Frontend will be available at:**
- App: http://localhost:5173

### 5. Configure Authentik

Authentik is your SSO provider. Configure it before first login:

1. **Access Authentik Admin**: http://localhost:9000/if/flow/initial-setup/
   - Follow initial setup wizard
   - Create admin account

2. **Create OAuth2 Application**:
   - Navigate to: Applications → Providers → Create
   - Provider Type: OAuth2/OpenID Provider
   - Name: Nozzly
   - Redirect URIs:
     ```
     http://localhost:5173/auth/callback
     https://nozzly.app/auth/callback
     ```
   - Client Type: Confidential
   - Save and note **Client ID** and **Client Secret**

3. **Update Backend .env**:
   ```env
   AUTHENTIK_CLIENT_ID=<client-id-from-step-2>
   AUTHENTIK_CLIENT_SECRET=<client-secret-from-step-2>
   ```

4. **Restart Backend** to apply new config

### 6. Verify Setup

**Backend Health Check:**

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

**Database Connection:**

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U nozzly -d nozzly

# List tables
\dt

# Expected tables: tenants, users, user_tenants, material_types, etc.
\q
```

**Frontend Access:**

Visit http://localhost:5173 in browser. You should see login page.

**Observability:**

- Grafana: http://localhost:3000
  - Default credentials: admin / admin (change on first login)
  - Datasources should be pre-configured

- Prometheus: http://localhost:9090
  - Query metrics: `http_requests_total`

- Tempo: http://localhost:3200
  - View traces via Grafana Explore

---

## Environment Variables

### Backend (.env)

```env
# App Configuration
APP_NAME=Nozzly
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://nozzly:nozzly@localhost:5432/nozzly

# For SQLite (development alternative):
# DATABASE_URL=sqlite+aiosqlite:///./nozzly.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Authentik
AUTHENTIK_URL=http://localhost:9000
AUTHENTIK_CLIENT_ID=<your-client-id>
AUTHENTIK_CLIENT_SECRET=<your-client-secret>

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=nozzly-backend
ENABLE_TRACING=true
ENABLE_METRICS=true

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Storage (local development)
STORAGE_TYPE=local
STORAGE_PATH=./uploads
```

### Frontend (.env)

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_API_BASE_PATH=/api/v1

# Authentik
VITE_AUTHENTIK_URL=http://localhost:9000
VITE_AUTHENTIK_CLIENT_ID=<same-as-backend>

# Feature Flags
VITE_ENABLE_QR_SCANNER=true
VITE_ENABLE_INTEGRATIONS=false
```

---

## Database Migrations

### Creating Migrations

```bash
cd backend

# Auto-generate migration from model changes
poetry run alembic revision --autogenerate -m "Add spools table"

# Manually create empty migration
poetry run alembic revision -m "Add custom index"
```

### Applying Migrations

```bash
# Upgrade to latest
poetry run alembic upgrade head

# Upgrade by 1 step
poetry run alembic upgrade +1

# Downgrade by 1 step
poetry run alembic downgrade -1

# Downgrade to specific revision
poetry run alembic downgrade <revision-id>
```

### Migration Best Practices

1. **Review Auto-Generated Migrations**: Always review before applying
2. **Test Migrations**: Test upgrade AND downgrade
3. **Data Migrations**: Add data migrations as separate steps
4. **Backups**: Always backup production before migrations

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_spools.py

# Run specific test
poetry run pytest tests/test_spools.py::test_create_spool

# Run with verbose output
poetry run pytest -v

# Run only unit tests
poetry run pytest tests/unit/

# Run only integration tests
poetry run pytest tests/integration/
```

### Frontend Tests

```bash
cd frontend

# Run all tests
pnpm test

# Run with coverage
pnpm test:coverage

# Run in watch mode (during development)
pnpm test:watch

# Run specific test file
pnpm test SpoolList.test.tsx
```

### E2E Tests (Optional, Phase 2+)

```bash
cd frontend

# Install Playwright
pnpm create playwright

# Run E2E tests
pnpm test:e2e

# Run E2E tests with UI
pnpm test:e2e:ui
```

---

## Code Quality

### Backend

**Linting:**

```bash
cd backend

# Run Ruff (linter)
poetry run ruff check .

# Fix auto-fixable issues
poetry run ruff check --fix .

# Type checking with MyPy
poetry run mypy .
```

**Formatting:**

```bash
cd backend

# Check formatting
poetry run black --check .

# Format code
poetry run black .
```

**All Quality Checks:**

```bash
cd backend
poetry run black . && poetry run ruff check . && poetry run mypy . && poetry run pytest
```

### Frontend

**Linting:**

```bash
cd frontend

# Run ESLint
pnpm lint

# Fix auto-fixable issues
pnpm lint:fix
```

**Formatting:**

```bash
cd frontend

# Check formatting
pnpm format:check

# Format code
pnpm format
```

**All Quality Checks:**

```bash
cd frontend
pnpm format && pnpm lint && pnpm test
```

---

## Common Development Tasks

### Using Make Commands

```bash
# Start full development stack
make dev

# Run all tests (backend + frontend)
make test

# Run linters
make lint

# Format all code
make format

# Run database migrations
make migrate

# Build Docker images
make build

# View logs
make logs

# Stop all services
make stop

# Clean up (remove containers, volumes)
make clean
```

### Manual Commands

**Backend Development Server:**

```bash
cd backend
poetry run uvicorn app.main:app --reload --port 8000 --log-level debug
```

**Frontend Development Server:**

```bash
cd frontend
pnpm dev --host  # Allow access from network
```

**Celery Worker (Background Jobs):**

```bash
cd backend
poetry run celery -A app.background.celery_app worker --loglevel=info
```

**Celery Beat (Scheduled Tasks):**

```bash
cd backend
poetry run celery -A app.background.celery_app beat --loglevel=info
```

**Database Shell:**

```bash
# PostgreSQL
docker-compose exec postgres psql -U nozzly -d nozzly

# Redis CLI
docker-compose exec redis redis-cli
```

---

## Debugging

### Backend Debugging

**VS Code Launch Configuration** (`.vscode/launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "DEBUG": "true"
      }
    }
  ]
}
```

**Debug with pdb:**

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

### Frontend Debugging

**Browser DevTools:**
- React DevTools extension
- Redux DevTools (if using Redux)
- Network tab for API calls

**VS Code Launch Configuration:**

```json
{
  "name": "Chrome: Frontend",
  "type": "chrome",
  "request": "launch",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src"
}
```

### Observability Debugging

**View Traces:**
1. Go to Grafana: http://localhost:3000
2. Navigate to Explore
3. Select Tempo datasource
4. Search for traces by service name: `nozzly-backend`

**View Logs:**
1. Go to Grafana: http://localhost:3000
2. Navigate to Explore
3. Select Loki datasource
4. Query: `{service_name="nozzly-backend"}`

**View Metrics:**
1. Go to Prometheus: http://localhost:9090
2. Query: `http_requests_total{service="nozzly-backend"}`

---

## Project Structure

```
nozzly.app/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── auth/            # Authentication
│   │   ├── background/      # Celery tasks
│   │   ├── models/          # SQLAlchemy models
│   │   ├── observability/   # OpenTelemetry setup
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── config.py        # Settings
│   │   ├── database.py      # Database connection
│   │   └── main.py          # FastAPI app
│   ├── alembic/             # Database migrations
│   ├── tests/               # Tests
│   ├── pyproject.toml       # Poetry dependencies
│   └── .env                 # Environment variables
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── lib/             # Utilities
│   │   ├── routes/          # Route definitions
│   │   └── types/           # TypeScript types
│   ├── public/              # Static assets
│   ├── package.json         # Dependencies
│   └── .env                 # Environment variables
│
├── infrastructure/
│   ├── k8s/                 # Kubernetes manifests
│   ├── observability/       # Grafana configs
│   └── cloudflare/          # Tunnel config
│
├── docs/                    # Documentation
├── docker-compose.yml       # Local dev stack
├── Makefile                 # Common commands
└── .gitignore
```

---

## Troubleshooting

### Backend Won't Start

**Issue:** `ModuleNotFoundError: No module named 'app'`

```bash
# Ensure you're in backend directory
cd backend

# Reinstall dependencies
poetry install

# Verify Poetry environment
poetry env info
```

**Issue:** `psycopg2.OperationalError: could not connect to server`

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Frontend Won't Build

**Issue:** `Module not found: Error: Can't resolve '@/components/...'`

```bash
# Check path aliases in vite.config.ts and tsconfig.json
# Ensure both have matching path configurations

# Clear node_modules and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Docker Compose Issues

**Issue:** `Error: Port 5432 is already in use`

```bash
# Check what's using the port
lsof -i :5432

# Stop conflicting service or change port in docker-compose.yml
```

**Issue:** `docker-compose: command not found`

```bash
# Install Docker Compose V2
sudo apt install docker-compose-plugin

# Or use: docker compose (without hyphen)
docker compose up -d
```

### Authentik Login Fails

**Issue:** `Invalid redirect URI`

- Verify redirect URI in Authentik matches exactly: `http://localhost:5173/auth/callback`
- Check for trailing slashes
- Ensure protocol (http vs https) matches

**Issue:** `Client authentication failed`

- Verify `AUTHENTIK_CLIENT_ID` and `AUTHENTIK_CLIENT_SECRET` match in backend `.env`
- Check Authentik admin for correct credentials

### Observability Not Working

**Issue:** No traces in Grafana

```bash
# Check Tempo is running
docker-compose ps tempo

# Check backend OTEL config
cat backend/.env | grep OTEL

# Verify endpoint is correct (should be http://localhost:4317)
```

**Issue:** Grafana datasources not configured

1. Go to Grafana: http://localhost:3000
2. Configuration → Data Sources
3. Add Tempo: http://tempo:3200
4. Add Prometheus: http://prometheus:9090
5. Add Loki: http://loki:3100

---

## Performance Optimization

### Backend

**Database Query Optimization:**

```python
# Use eager loading to avoid N+1 queries
from sqlalchemy.orm import selectinload

query = select(Product).options(
    selectinload(Product.materials),
    selectinload(Product.components)
)
```

**Caching:**

```python
# Use Redis for caching expensive calculations
import redis
cache = redis.Redis(host='localhost', port=6379)

cache.setex('product:123:cost', 3600, str(cost))  # Cache for 1 hour
```

### Frontend

**Code Splitting:**

```tsx
// Lazy load routes
const Dashboard = lazy(() => import('./routes/dashboard'))
```

**Memoization:**

```tsx
// Memoize expensive calculations
const totalCost = useMemo(() =>
  calculateCost(materials, components),
  [materials, components]
)
```

---

## Contributing Workflow

1. **Create Feature Branch:**
   ```bash
   git checkout -b feature/phase-1-inventory
   ```

2. **Make Changes:**
   - Write code
   - Write tests
   - Update documentation

3. **Run Quality Checks:**
   ```bash
   make lint test
   ```

4. **Commit Changes:**
   ```bash
   git add .
   git commit -m "feat: add spool management endpoints"
   ```

5. **Push and Create PR:**
   ```bash
   git push origin feature/phase-1-inventory
   gh pr create --title "Phase 1: Core Inventory Management"
   ```

6. **Wait for CI:**
   - GitHub Actions will run tests and linting
   - Fix any failures

7. **Merge:**
   - Once approved and CI passes, merge to main

---

## Useful Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [React Docs](https://react.dev/)
- [shadcn/ui Docs](https://ui.shadcn.com/)
- [Authentik Docs](https://goauthentik.io/docs/)

### Tools
- [Poetry Docs](https://python-poetry.org/docs/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [TanStack Query Docs](https://tanstack.com/query/latest)
- [Recharts Examples](https://recharts.org/en-US/examples)

### OpenTelemetry
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Tempo Docs](https://grafana.com/docs/tempo/latest/)

---

*Last Updated: 2025-10-29*
*Document Version: 1.0*
