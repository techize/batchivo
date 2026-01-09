# Nozzly Testing Guide

## Overview

This document describes the testing strategy and available tests for the Nozzly application.

## Test Categories

### 1. Unit Tests (Python/Pytest)

Located in `backend/tests/test_*.py`

**Test Files**:
- `test_auth_flow.py` - Comprehensive authentication flow tests

**Running Unit Tests**:

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_auth_flow.py

# Run specific test
pytest tests/test_auth_flow.py::TestAuthenticationFlow::test_login_and_get_user_info

# Run with verbose output
pytest -v --tb=short

# Run with coverage
pytest --cov=app --cov-report=html
```

**Test Coverage**:

`test_auth_flow.py` covers:
- Login flow
- Token management
- Multiple authenticated endpoint access
- Material types retrieval
- Spool creation with material types
- Unauthenticated access rejection
- Invalid token rejection
- Multi-tenant data isolation

### 2. Integration Tests (Bash/curl)

Located in `backend/tests/integration_test.sh`

**What it tests**:
1. Health check endpoint
2. User login (POST /auth/login)
3. Get user info (GET /users/me)
4. List material types (GET /spools/material-types)
5. List spools (GET /spools)
6. Create spool (POST /spools)
7. Authentication consistency (5 sequential requests)

**Running Integration Tests**:

```bash
cd backend

# Test against production
./tests/integration_test.sh https://nozzly.app/api/v1

# Test against local dev
./tests/integration_test.sh http://localhost:8000/api/v1

# Test with default (production)
./tests/integration_test.sh
```

**Requirements**:
- `curl` installed
- `jq` installed (JSON processor)
- Valid test user credentials (test@example.com)

**Expected Output**:

```
[TEST] Health check endpoint
[PASS] Health check passed

[TEST] User login
[PASS] Login successful - received access token

[TEST] Get user info (/users/me)
[PASS] Retrieved user info successfully
[INFO] User: test@example.com, Tenant: <uuid>

[TEST] List material types (/spools/material-types)
[PASS] Retrieved 8 material types
[INFO] PLA material ID: <uuid>

[TEST] List spools (/spools)
[PASS] Retrieved spools list (total: 0)

[TEST] Create new spool
[PASS] Created spool TEST-1234 with material PLA
[INFO] Spool ID: <uuid>

[TEST] Verify authentication consistency (multiple sequential requests)
[INFO] Request 1/5
[INFO] Request 2/5
[INFO] Request 3/5
[INFO] Request 4/5
[INFO] Request 5/5
[PASS] All 5 sequential requests succeeded

========================================
Test Summary
========================================
Tests Run:    7
Tests Passed: 7
Tests Failed: 0
========================================
All tests passed!
```

### 3. Frontend Tests (Vitest - TODO)

Location: `frontend/tests/`

**Planned Coverage**:
- Component rendering tests
- Form validation tests
- API client tests (mocked)
- Authentication flow tests

**Running Frontend Tests** (when implemented):

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

### 4. E2E Tests (Playwright - Future)

**Planned Coverage**:
- Complete user workflows
- Login → Dashboard → Create Spool → View Spool
- Multi-tenant isolation verification
- Error handling

## Test Fixtures

### Backend Test Fixtures (conftest.py)

Located in `backend/tests/conftest.py`

**Available Fixtures**:

```python
# Database fixtures
db_engine          # Test database engine (SQLite in-memory)
db_session         # Test database session
db                 # Alias for db_session

# HTTP client fixtures
client             # AsyncClient with db override
async_client       # Alias for client

# Data fixtures
seed_material_types  # Seeds 8 standard material types
test_tenant          # Creates test tenant
test_user            # Creates test user with hashed password
test_material_type   # Creates single test material type
test_spool           # Creates test spool
test_product         # Creates test product

# Auth fixtures
auth_headers         # Mock JWT auth headers
```

### Integration Test Configuration

Located in `backend/tests/integration_test.sh`

**Configuration Variables**:

```bash
API_BASE_URL="https://nozzly.app/api/v1"
TEST_EMAIL="test@example.com"
TEST_PASSWORD="testpassword123"
```

## Authentication Issue Fixed

### Problem

The frontend `getAuthTokens()` function had a race condition:

```typescript
// OLD CODE (problematic)
export function getAuthTokens(): AuthTokens | null {
  const tokens = JSON.parse(sessionStorage.getItem(TOKEN_STORAGE_KEY))

  // This triggered async refresh but returned old token immediately
  if (isTokenExpiringSoon(tokens)) {
    refreshAccessToken().catch(console.error)  // Async!
  }

  return tokens  // Old token returned before refresh completes
}
```

**Impact**: First API request would use expired token (401), second request would use refreshed token (200).

### Solution

Removed the auto-refresh from `getAuthTokens()` since the axios interceptor already handles token refresh properly:

```typescript
// NEW CODE (fixed)
export function getAuthTokens(): AuthTokens | null {
  const tokens = JSON.parse(sessionStorage.getItem(TOKEN_STORAGE_KEY))
  return tokens  // Just return tokens, interceptor handles refresh
}
```

**File**: `frontend/src/lib/auth.ts:175`

**Deployed in**: Frontend v1.14

## Running All Tests

### Full Test Suite

```bash
# Backend unit tests
cd backend && pytest -v

# Integration tests (requires running backend)
cd backend && ./tests/integration_test.sh

# Frontend tests (when implemented)
cd frontend && npm test
```

### CI/CD Pipeline (Future)

**Planned GitHub Actions workflow**:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install poetry
          poetry install
      - name: Run unit tests
        run: |
          cd backend
          poetry run pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
```

## Test Data Management

### Seeding Test Data

**Material Types** are automatically seeded via the `seed_material_types` fixture:

```python
material_types = [
    {"code": "PLA", "name": "PLA (Polylactic Acid)"},
    {"code": "PETG", "name": "PETG (...)"},
    # ... 6 more types
]
```

**Test User** is created with:
- Email: test@example.com
- Password: testpassword123 (hashed)
- Associated with test tenant

### Cleaning Test Data

Unit tests use SQLite in-memory database - data is automatically cleaned between tests.

Integration tests create real data in the system - use unique IDs to avoid conflicts:

```bash
RANDOM_ID=$((RANDOM % 10000))
SPOOL_DATA='{"spool_id": "TEST-'$RANDOM_ID'",...}'
```

## Debugging Tests

### Backend Unit Test Debugging

```bash
# Run with detailed output
pytest -vv --tb=long

# Run with print statements visible
pytest -s

# Run specific test with debugging
pytest tests/test_auth_flow.py::TestAuthenticationFlow::test_tenant_isolation -vv -s

# Use pytest-pdb for interactive debugging
pytest --pdb
```

### Integration Test Debugging

```bash
# Enable bash debugging
bash -x tests/integration_test.sh

# Check specific endpoint
curl -v -H "Authorization: Bearer $TOKEN" https://nozzly.app/api/v1/users/me
```

### Frontend Debugging (when tests exist)

```bash
# Run tests in debug mode
npm test -- --inspect-brk

# Run with browser UI
npm test -- --ui
```

## Known Issues

### Unit Tests

- Tests cannot currently be run via Docker (pytest not included in prod image)
- Solution: Run tests in local virtual environment or add test stage to Dockerfile

### Integration Tests

- Requires valid test user to exist in database
- Currently uses production credentials (consider test-specific user)

## Future Improvements

1. **Add Dockerfile test stage**:
   ```dockerfile
   FROM python:3.11-slim AS test
   COPY --from=builder /app /app
   RUN pip install pytest pytest-asyncio httpx
   CMD ["pytest"]
   ```

2. **Add frontend component tests**:
   - Test SpoolList rendering
   - Test AddSpoolDialog validation
   - Test material type dropdown

3. **Add E2E tests with Playwright**:
   - Full user journeys
   - Multi-browser testing

4. **Add performance tests**:
   - Load testing with Locust
   - Database query performance

5. **Add security tests**:
   - OWASP ZAP scanning
   - SQL injection tests
   - XSS tests

6. **Set up test coverage tracking**:
   - Codecov integration
   - Coverage badges in README
   - Minimum coverage requirements (80%+)

## Test Maintenance

### When to Update Tests

- **Adding new endpoints**: Add integration test cases
- **Changing authentication**: Update auth flow tests
- **Adding features**: Add unit tests for business logic
- **Fixing bugs**: Add regression test for the bug

### Test Review Checklist

- [ ] All tests pass locally
- [ ] Tests cover happy path
- [ ] Tests cover error cases
- [ ] Tests are isolated (no shared state)
- [ ] Tests are deterministic (no flaky tests)
- [ ] Test names are descriptive
- [ ] Fixtures are reused where possible

---

**Last Updated**: 2025-11-18
**Author**: Claude Code (Nexus)
**Version**: 1.0
