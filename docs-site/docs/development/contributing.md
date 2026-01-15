---
sidebar_position: 1
---

# Contributing

Thank you for your interest in contributing to Batchivo! This guide will help you get started.

## Code of Conduct

Please read our [Code of Conduct](https://github.com/techize/batchivo/blob/main/CODE_OF_CONDUCT.md) before contributing.

## Ways to Contribute

- **Report Bugs**: Open an issue describing the bug
- **Suggest Features**: Share ideas in GitHub Discussions
- **Fix Bugs**: Submit pull requests for open issues
- **Write Documentation**: Improve guides and API docs
- **Review PRs**: Help review pull requests

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Poetry
- Git

### Clone and Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/batchivo.git
cd batchivo

# Backend setup
cd backend
poetry install
cp .env.example .env
poetry run alembic upgrade head

# Frontend setup
cd ../frontend
npm install
```

### Running Locally

```bash
# Terminal 1: Backend
cd backend
poetry run uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Follow existing code style
- Add tests for new features
- Update documentation if needed

### 3. Test Your Changes

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend tests
cd frontend
npm run test

# Linting
poetry run ruff check .
npm run lint
```

### 4. Commit

Write clear commit messages:

```
feat: add spool bulk import feature

- Add CSV parser for spool data
- Create bulk import API endpoint
- Add frontend upload UI
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a pull request on GitHub.

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Format with Ruff

```python
# Good
def get_spool(spool_id: UUID, db: AsyncSession) -> Spool:
    """Retrieve a spool by ID."""
    ...

# Bad
def get_spool(id, db):
    ...
```

### TypeScript (Frontend)

- Use TypeScript strictly
- Follow React best practices
- Format with Prettier

```typescript
// Good
interface SpoolProps {
  spool: Spool;
  onEdit: (id: string) => void;
}

// Bad
const SpoolCard = (props: any) => { ... }
```

## Testing

### Backend

```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=app

# Specific test
poetry run pytest tests/test_spools.py -v
```

### Frontend

```bash
# Run tests
npm run test

# Watch mode
npm run test:watch
```

## Documentation

- Update relevant docs when changing behavior
- Add docstrings to Python functions
- Add JSDoc comments to TypeScript functions

## Getting Help

- **Questions**: [GitHub Discussions](https://github.com/techize/batchivo/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/techize/batchivo/issues)
- **Security**: See [SECURITY.md](https://github.com/techize/batchivo/blob/main/SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
