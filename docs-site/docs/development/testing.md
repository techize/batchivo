---
sidebar_position: 3
---

# Testing

Guide to testing Batchivo's backend and frontend.

## Backend Testing

### Running Tests

```bash
cd backend

# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=app --cov-report=html

# Verbose output
poetry run pytest -v

# Specific file
poetry run pytest tests/test_spools.py

# Specific test
poetry run pytest tests/test_spools.py::test_create_spool -v
```

### Test Structure

```
backend/tests/
├── conftest.py          # Fixtures and setup
├── test_auth.py         # Authentication tests
├── test_spools.py       # Spool CRUD tests
├── test_products.py     # Product tests
├── test_production.py   # Production run tests
└── integration/         # Integration tests
    └── test_workflows.py
```

### Writing Tests

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_spool(client: AsyncClient, auth_headers: dict):
    """Test creating a new spool."""
    response = await client.post(
        "/api/v1/spools",
        json={
            "material_type": "PLA",
            "color": "Black",
            "diameter_mm": 1.75,
            "net_weight_grams": 1000,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["material_type"] == "PLA"
    assert data["color"] == "Black"
```

### Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def auth_headers(client):
    """Get authentication headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def test_spool(client, auth_headers):
    """Create a test spool."""
    response = await client.post(
        "/api/v1/spools",
        json={...},
        headers=auth_headers,
    )
    return response.json()
```

### Database Testing

Tests use a separate test database:

```python
@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

## Frontend Testing

### Running Tests

```bash
cd frontend

# All tests
npm run test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage

# Specific file
npm run test -- SpoolList.test.tsx
```

### Test Structure

```
frontend/src/
├── components/
│   ├── SpoolList.tsx
│   └── SpoolList.test.tsx
├── hooks/
│   ├── useSpools.ts
│   └── useSpools.test.ts
└── __tests__/
    └── integration/
```

### Writing Tests

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SpoolList } from './SpoolList';

describe('SpoolList', () => {
  it('renders spool items', async () => {
    render(<SpoolList />);

    await waitFor(() => {
      expect(screen.getByText('PLA Black')).toBeInTheDocument();
    });
  });

  it('filters by material type', async () => {
    const user = userEvent.setup();
    render(<SpoolList />);

    await user.click(screen.getByRole('combobox', { name: /material/i }));
    await user.click(screen.getByRole('option', { name: 'PETG' }));

    await waitFor(() => {
      expect(screen.queryByText('PLA Black')).not.toBeInTheDocument();
    });
  });
});
```

### Mocking API Calls

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/v1/spools', (req, res, ctx) => {
    return res(ctx.json({
      items: [
        { id: '1', material_type: 'PLA', color: 'Black' },
      ],
      total: 1,
    }));
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Integration Testing

### End-to-End Workflows

```python
@pytest.mark.asyncio
async def test_production_run_workflow(client, auth_headers):
    """Test complete production run workflow."""

    # 1. Create spool
    spool = await create_spool(client, auth_headers)

    # 2. Create product
    product = await create_product(client, auth_headers)

    # 3. Start production run
    run = await client.post(
        "/api/v1/production-runs",
        json={
            "printer_name": "Test Printer",
            "estimated_print_time_hours": 2,
        },
        headers=auth_headers,
    )
    run_id = run.json()["id"]

    # 4. Add items and materials
    await client.post(f"/api/v1/production-runs/{run_id}/items", ...)
    await client.post(f"/api/v1/production-runs/{run_id}/materials", ...)

    # 5. Complete run
    result = await client.post(f"/api/v1/production-runs/{run_id}/complete")

    assert result.status_code == 200
    assert result.json()["status"] == "completed"
```

## CI/CD Testing

Tests run automatically on:

- Pull requests
- Pushes to main
- Release tags

See `.github/workflows/ci.yml` for configuration.
