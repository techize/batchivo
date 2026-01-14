# Contributing to Batchivo

Thank you for your interest in contributing to Batchivo! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Messages](#commit-messages)
- [Documentation](#documentation)

---

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

---

## Getting Started

### Prerequisites

- **Docker** 20.10+ & **Docker Compose** 2.0+
- **Python** 3.11+
- **Poetry** 1.5+ (Python package manager)
- **Node.js** 20+ (LTS)
- **pnpm** 8+ (or npm 9+)
- **Git** 2.30+

### Finding Issues to Work On

1. Check the [Issues](https://github.com/techize/batchivo/issues) page
2. Look for issues labeled `good first issue` or `help wanted`
3. Comment on an issue to express interest before starting work
4. Wait for maintainer confirmation before beginning

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/batchivo.git
cd batchivo

# Add upstream remote
git remote add upstream https://github.com/techize/batchivo.git
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL, Redis, and observability stack
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

### 3. Backend Setup

```bash
cd backend

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment template
cp .env.example .env

# Start development server
pnpm dev
```

### Verification

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Health check: `curl http://localhost:8000/health`

For detailed setup instructions, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Making Changes

### Branch Strategy

1. Always create a feature branch from `main`:
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/your-feature-name
   ```

2. Branch naming conventions:
   - `feature/description` - New features
   - `fix/description` - Bug fixes
   - `docs/description` - Documentation updates
   - `refactor/description` - Code refactoring
   - `test/description` - Test additions/updates

### Development Workflow

1. **Write code** following the [coding standards](#coding-standards)
2. **Write tests** for all new functionality
3. **Run quality checks**:
   ```bash
   # Backend
   cd backend
   poetry run pytest
   poetry run ruff check
   poetry run ruff format --check

   # Frontend
   cd frontend
   pnpm test
   pnpm lint
   ```
4. **Update documentation** if needed
5. **Commit changes** using [conventional commits](#commit-messages)

---

## Pull Request Process

### Before Submitting

1. Ensure all tests pass locally
2. Update documentation for any changed functionality
3. Rebase on latest `main` to resolve conflicts
4. Verify your changes work end-to-end

### Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request against `main` branch

3. Fill out the PR template completely:
   - Clear description of changes
   - Link to related issue(s)
   - Testing performed
   - Screenshots (for UI changes)

### Review Process

- Maintainers will review your PR within 1-2 weeks
- Address feedback promptly
- Keep PRs focused and reasonably sized
- Be patient and respectful during review

### After Merge

- Delete your feature branch
- Sync your fork with upstream

---

## Coding Standards

### Python (Backend)

- **Style**: Follow PEP 8, enforced by Ruff
- **Type Hints**: Required for all function signatures
- **Docstrings**: Required for public functions and classes
- **Imports**: Sorted by Ruff (isort compatible)

```python
# Example endpoint pattern
@router.get("/items/{item_id}")
async def get_item(
    item_id: int,
    tenant: Tenant = Depends(get_current_tenant),  # Always include tenant
    db: AsyncSession = Depends(get_db),
) -> ItemResponse:
    """Retrieve a single item by ID."""
    ...
```

### TypeScript (Frontend)

- **Style**: ESLint + Prettier configuration
- **Types**: Explicit types required (no `any` without justification)
- **Components**: Functional components with hooks
- **State**: TanStack Query for server state

```tsx
// Example component pattern
interface ItemCardProps {
  item: Item;
  onSelect: (id: number) => void;
}

export function ItemCard({ item, onSelect }: ItemCardProps) {
  // Component implementation
}
```

### Multi-Tenant Security

**Critical**: Every database query must be tenant-scoped.

```python
# CORRECT - uses tenant scope
@router.get("/spools")
async def list_spools(
    tenant: Tenant = Depends(get_current_tenant),  # Required
    db: AsyncSession = Depends(get_db),
):
    query = select(Spool).where(Spool.tenant_id == tenant.id)
    ...

# INCORRECT - missing tenant scope (will be rejected)
@router.get("/spools")
async def list_spools(db: AsyncSession = Depends(get_db)):
    query = select(Spool)  # Security vulnerability!
    ...
```

---

## Testing Requirements

**All code changes must include tests. No exceptions.**

### Required Test Coverage

| Change Type | Required Tests |
|-------------|----------------|
| New endpoint | Success (200/201), auth (401), validation (422), not found (404) |
| Business logic | Success path, edge cases, error conditions |
| Bug fix | Regression test proving fix works |
| Schema change | Model CRUD, relationships, constraints |

### Running Tests

```bash
# Backend - full test suite with coverage
cd backend
poetry run pytest --cov=app --cov-report=term-missing

# Backend - specific test file
poetry run pytest tests/test_spools.py -v

# Frontend - run tests
cd frontend
pnpm test

# Frontend - with coverage
pnpm test:coverage
```

### Test Fixtures

Available fixtures in `backend/tests/conftest.py`:
- `client` - Test HTTP client
- `db_session` - Database session
- `test_tenant` - Pre-created tenant
- `test_user` - Pre-created user
- `test_spool` - Pre-created spool

---

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type: short description

Optional longer description explaining the change.
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, no logic change)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### Examples

```bash
# Good commit messages
git commit -m "feat: add spool weight tracking endpoint"
git commit -m "fix: correct cost calculation for multi-material products"
git commit -m "docs: update API documentation for spools"
git commit -m "test: add integration tests for production runs"

# Bad commit messages (avoid)
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "updates"
```

**Note**: Do not include AI markers (e.g., "Co-Authored-By: Claude") in commits to this repository.

---

## Documentation

### When to Update Documentation

- Adding new features
- Changing existing behavior
- Adding new API endpoints
- Modifying configuration options
- Updating setup/installation steps

### Documentation Locations

- `README.md` - Project overview
- `docs/DEVELOPMENT.md` - Local development setup
- `docs/ARCHITECTURE.md` - System design
- `docs/DATABASE_SCHEMA.md` - Database structure
- `docs/api-reference/` - API endpoint documentation

### API Documentation

API docs are auto-generated from code:
- FastAPI generates OpenAPI spec at `/docs` and `/redoc`
- Keep docstrings and Pydantic schemas accurate

---

## Questions?

- Check existing [Issues](https://github.com/techize/batchivo/issues) and [Discussions](https://github.com/techize/batchivo/discussions)
- Open a new Discussion for questions
- For security issues, see [SECURITY.md](SECURITY.md)

---

Thank you for contributing to Batchivo!
