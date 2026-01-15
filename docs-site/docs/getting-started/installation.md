---
sidebar_position: 3
---

# Installation

Detailed installation instructions for different deployment scenarios.

## Docker Compose (Recommended)

The simplest way to run Batchivo. See the [Quick Start](/docs/getting-started/quickstart) guide.

## Development Setup

For contributing to Batchivo or running locally without Docker.

### Backend

```bash
# Navigate to backend directory
cd backend

# Install dependencies with Poetry
poetry install

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload --port 8000
```

**Verify backend is running:**
```bash
curl http://localhost:8000/health
```

### Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Verify frontend is running:**
Open http://localhost:5173 in your browser.

## Production Deployment

For production deployments, see the [Self-Hosting](/docs/self-hosting/overview) section.

## Database Options

### SQLite (Development)

SQLite works out of the box for development:

```bash
DATABASE_URL=sqlite+aiosqlite:///./batchivo.db
```

### PostgreSQL (Production)

For production, use PostgreSQL for Row-Level Security support:

```bash
# Create database
createdb batchivo

# Set connection string
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/batchivo

# Run migrations
poetry run alembic upgrade head
```

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.12+

# Reinstall dependencies
poetry install --no-cache

# Check migration state
poetry run alembic current
```

### Database migration errors

```bash
# Reset database (CAUTION: deletes all data)
rm backend/batchivo.db  # For SQLite
poetry run alembic upgrade head
```

### Frontend build errors

```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### API returns 422 validation errors

- Check request body matches schema in API docs
- Ensure all required fields are provided
- Verify UUID formats are correct
