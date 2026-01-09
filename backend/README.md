# Nozzly Backend

FastAPI backend for Nozzly 3D print business management platform.

## Development

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint
poetry run ruff check .
```

## Environment Variables

Copy `.env.example` to `.env` and configure.
# Trigger CI Tue 30 Dec 2025 15:08:01 GMT
