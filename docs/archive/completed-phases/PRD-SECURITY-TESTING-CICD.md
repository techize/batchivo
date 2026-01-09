# PRD: Security Hardening, Testing Infrastructure & GitOps CI/CD

**Document Version**: 1.0
**Created**: 2025-12-12
**Author**: Jonathan Gill (with Nexus AI)
**Status**: Draft → Ready for Implementation
**Priority**: CRITICAL

---

## Executive Summary

This PRD addresses critical security vulnerabilities, establishes testing infrastructure, and implements GitOps-based CI/CD for the nozzly.app codebase. These issues were identified during a comprehensive code review on 2025-12-12.

**Business Impact**:
- Current state blocks production deployment confidence
- Security issues expose payment processing and user data
- No automated quality gates increase deployment risk

**Success Criteria**:
- [ ] Zero critical security vulnerabilities
- [ ] 60%+ backend test coverage, 30%+ frontend
- [ ] Automated CI/CD pipeline with quality gates
- [ ] GitOps deployment to k3s cluster

---

## Table of Contents

1. [Critical Security Fixes](#1-critical-security-fixes)
2. [Testing Infrastructure](#2-testing-infrastructure)
3. [GitOps CI/CD Pipeline](#3-gitops-cicd-pipeline)
4. [Implementation Phases](#4-implementation-phases)
5. [Acceptance Criteria](#5-acceptance-criteria)

---

## 1. Critical Security Fixes

### 1.1 JWT Secret Key Rotation

**Current State**: Weak default secret key in `.env`
```bash
SECRET_KEY=change-this-in-production-use-random-string
```

**Risk**: JWT token forgery, complete authentication bypass

**Solution**:

#### 1.1.1 Generate Secure Secret
```bash
# Generate 64-byte cryptographically secure key
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### 1.1.2 Create Kubernetes Secret
```yaml
# infrastructure/k8s/backend/secrets.yaml (DO NOT COMMIT - template only)
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: nozzly
type: Opaque
stringData:
  SECRET_KEY: "<generated-key>"
  DATABASE_URL: "postgresql+psycopg://nozzly:<password>@postgres:5432/nozzly"
```

#### 1.1.3 Update Deployment to Use Secret
```yaml
# infrastructure/k8s/backend/deployment.yaml
env:
  - name: SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: backend-secrets
        key: SECRET_KEY
```

#### 1.1.4 Remove from .env
- Delete `SECRET_KEY` line from `backend/.env`
- Keep in `.env.example` as: `SECRET_KEY=generate-with-python-secrets`

**Acceptance Criteria**:
- [ ] New secret key is 64+ characters, cryptographically random
- [ ] Secret stored in K8s Secret, not in git
- [ ] Application starts successfully with new key
- [ ] Existing tokens invalidated (expected behavior)

---

### 1.2 Square API Credentials Management

**Current State**: Credentials in `.env` file (committed to git)
```bash
SQUARE_ACCESS_TOKEN=***REMOVED***
SQUARE_LOCATION_ID=***REMOVED***
```

**Risk**: Payment API credential exposure (MEDIUM for private repo)

**Solution**:

#### 1.2.1 Create Dedicated Square Secret
```bash
kubectl create secret generic square-credentials \
  --from-literal=access-token='<token>' \
  --from-literal=location-id='***REMOVED***' \
  --from-literal=environment='sandbox' \
  -n nozzly
```

#### 1.2.2 Update Backend Deployment
```yaml
env:
  - name: SQUARE_ACCESS_TOKEN
    valueFrom:
      secretKeyRef:
        name: square-credentials
        key: access-token
  - name: SQUARE_LOCATION_ID
    valueFrom:
      secretKeyRef:
        name: square-credentials
        key: location-id
```

#### 1.2.3 Remove from .env and Git History
```bash
# Remove from .env
sed -i '' '/SQUARE_ACCESS_TOKEN/d' backend/.env
sed -i '' '/SQUARE_LOCATION_ID/d' backend/.env

# Optional: Remove from git history (if needed)
# git filter-branch --force --index-filter \
#   "git rm --cached --ignore-unmatch backend/.env" HEAD
```

#### 1.2.4 Update .env.example
```bash
# Square Payment Integration (get from K8s secret)
SQUARE_ACCESS_TOKEN=from-kubernetes-secret
SQUARE_LOCATION_ID=from-kubernetes-secret
SQUARE_ENVIRONMENT=sandbox
```

**Acceptance Criteria**:
- [ ] Credentials removed from `.env` file
- [ ] K8s Secret created and applied
- [ ] Payment flow still works (test checkout)
- [ ] .env.example updated with placeholder

---

### 1.3 Remove Hardcoded Tenant ID

**Current State**: `backend/app/api/v1/shop.py:637`
```python
# Hardcoded tenant_id for mystmereforge (same tenant as products)
tenant_id = UUID("ad62b515-17b3-4830-bcb4-3f4c470c26e2")
```

**Risk**: Multi-tenant isolation bypass

**Solution**:

#### 1.3.1 Add Sales Channel Tenant Lookup
```python
# backend/app/api/v1/shop.py

async def get_tenant_from_sales_channel(
    channel_id: str,
    db: AsyncSession
) -> Tenant:
    """Look up tenant from sales channel configuration."""
    result = await db.execute(
        select(SalesChannel)
        .options(selectinload(SalesChannel.tenant))
        .where(SalesChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(404, "Sales channel not found")
    return channel.tenant
```

#### 1.3.2 Update Shop Endpoints
```python
@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
):
    # Get tenant from sales channel instead of hardcoded value
    tenant = await get_tenant_from_sales_channel(
        request.sales_channel_id,
        db
    )

    # Use tenant.id instead of hardcoded UUID
    order = Order(tenant_id=tenant.id, ...)
```

**Acceptance Criteria**:
- [ ] No hardcoded UUIDs in codebase (grep verification)
- [ ] Shop checkout works with sales channel lookup
- [ ] Multi-tenant isolation maintained

---

### 1.4 Add Rate Limiting to Auth Endpoints

**Current State**: No rate limiting on login/password reset

**Risk**: Brute force attacks, credential stuffing

**Solution**:

#### 1.4.1 Install SlowAPI
```bash
cd backend
poetry add slowapi
```

#### 1.4.2 Configure Rate Limiter
```python
# backend/app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

#### 1.4.3 Add to Main App
```python
# backend/app/main.py
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

#### 1.4.4 Apply to Auth Endpoints
```python
# backend/app/api/v1/auth.py
from app.core.rate_limit import limiter

@router.post("/login")
@limiter.limit("5/minute")  # 5 attempts per minute per IP
async def login(request: Request, ...):
    ...

@router.post("/forgot-password")
@limiter.limit("3/minute")  # 3 requests per minute per IP
async def forgot_password(request: Request, ...):
    ...

@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, ...):
    ...
```

**Acceptance Criteria**:
- [ ] Rate limiting active on all auth endpoints
- [ ] 429 response returned when limit exceeded
- [ ] Legitimate users not impacted (reasonable limits)
- [ ] Rate limit headers in responses

---

### 1.5 Add Security Headers

**Current State**: No security headers configured

**Solution**:

```python
# backend/app/middleware/security.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS (HTTPS enforcement)
        response.headers["Strict-Transport-Security"] = \
            "max-age=31536000; includeSubDomains"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy
        response.headers["Permissions-Policy"] = \
            "geolocation=(), microphone=(), camera=()"

        return response
```

```python
# backend/app/main.py
from app.middleware.security import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
```

**Acceptance Criteria**:
- [ ] All 6 security headers present in responses
- [ ] Headers verified via browser DevTools
- [ ] No functional regressions

---

## 2. Testing Infrastructure

### 2.1 Frontend Test Setup

**Current State**:
- 1 test file exists (`SpoolList.test.tsx`)
- No test runner installed
- Tests cannot execute

**Solution**:

#### 2.1.1 Install Test Dependencies
```bash
cd frontend
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom \
  @testing-library/user-event jsdom @vitest/coverage-v8
```

#### 2.1.2 Create Vitest Configuration
```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
      ],
      thresholds: {
        statements: 30,
        branches: 30,
        functions: 30,
        lines: 30,
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

#### 2.1.3 Create Test Setup File
```typescript
// frontend/src/test/setup.ts
import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))
```

#### 2.1.4 Update package.json Scripts
```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage",
    "test:ci": "vitest run --coverage --reporter=junit --outputFile=test-results.xml"
  }
}
```

#### 2.1.5 Verify Existing Test Runs
```bash
npm run test -- --run
# Expected: SpoolList.test.tsx passes
```

**Acceptance Criteria**:
- [ ] `npm run test` executes successfully
- [ ] SpoolList.test.tsx passes (25 tests)
- [ ] Coverage report generates
- [ ] CI-compatible output available

---

### 2.2 Backend Test Enhancement

**Current State**:
- 5 test files, ~53 tests
- ~15% coverage
- Production Runs well-tested, others minimal

**Solution**:

#### 2.2.1 Add Critical Test Files

**Authentication Tests** (`tests/integration/test_auth_api.py`):
```python
import pytest
from httpx import AsyncClient

class TestAuthEndpoints:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login returns JWT token."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login with wrong password returns 401."""
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_rate_limiting(self, client: AsyncClient):
        """Test rate limiting blocks excessive login attempts."""
        for i in range(6):
            response = await client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client: AsyncClient):
        """Test protected endpoints return 401 without token."""
        response = await client.get("/api/v1/products")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_token_validation(self, client: AsyncClient, auth_headers):
        """Test valid JWT allows access to protected endpoints."""
        response = await client.get("/api/v1/products", headers=auth_headers)
        assert response.status_code == 200
```

**Products API Tests** (`tests/integration/test_products_api.py`):
```python
import pytest
from httpx import AsyncClient
from uuid import uuid4

class TestProductsEndpoints:
    """Test products API endpoints."""

    @pytest.mark.asyncio
    async def test_create_product(self, client: AsyncClient, auth_headers):
        """Test product creation."""
        response = await client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "sku": f"TEST-{uuid4().hex[:8]}",
                "name": "Test Product",
                "description": "A test product"
            }
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_list_products(self, client: AsyncClient, auth_headers, test_product):
        """Test product listing with pagination."""
        response = await client.get(
            "/api/v1/products",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "items" in response.json() or isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_product_tenant_isolation(
        self,
        client: AsyncClient,
        auth_headers,
        other_tenant_product
    ):
        """Test products from other tenants are not visible."""
        response = await client.get(
            f"/api/v1/products/{other_tenant_product.id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_product_cost_calculation(
        self,
        client: AsyncClient,
        auth_headers,
        test_product_with_models
    ):
        """Test cost calculation returns expected breakdown."""
        response = await client.get(
            f"/api/v1/products/{test_product_with_models.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "cost_breakdown" in data
        assert data["cost_breakdown"]["total_make_cost"] > 0
```

**Inventory Tests** (`tests/integration/test_spools_api.py`):
```python
import pytest
from httpx import AsyncClient
from decimal import Decimal

class TestSpoolsEndpoints:
    """Test spool/inventory API endpoints."""

    @pytest.mark.asyncio
    async def test_create_spool(self, client: AsyncClient, auth_headers, test_material_type):
        """Test spool creation with material type."""
        response = await client.post(
            "/api/v1/spools",
            headers=auth_headers,
            json={
                "material_type_id": str(test_material_type.id),
                "manufacturer": "Test Manufacturer",
                "initial_weight": 1000,
                "current_weight": 1000,
                "price_per_kg": "25.00"
            }
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_update_spool_weight(
        self,
        client: AsyncClient,
        auth_headers,
        test_spool
    ):
        """Test weight update creates transaction."""
        response = await client.patch(
            f"/api/v1/spools/{test_spool.id}/weight",
            headers=auth_headers,
            json={"new_weight": 800, "reason": "Production usage"}
        )
        assert response.status_code == 200
        assert response.json()["current_weight"] == 800

    @pytest.mark.asyncio
    async def test_low_stock_alert(
        self,
        client: AsyncClient,
        auth_headers,
        test_spool_low_stock
    ):
        """Test low stock spools appear in alerts."""
        response = await client.get(
            "/api/v1/spools?low_stock=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Verify low stock spool is included
```

#### 2.2.2 Add Test Fixtures
```python
# tests/conftest.py (additions)

@pytest.fixture
async def test_product(db_session, test_tenant):
    """Create a test product."""
    product = Product(
        tenant_id=test_tenant.id,
        sku="TEST-001",
        name="Test Product",
        description="Test description"
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product

@pytest.fixture
async def test_product_with_models(db_session, test_tenant, test_model):
    """Create a product with model associations."""
    product = Product(
        tenant_id=test_tenant.id,
        sku="TEST-002",
        name="Test Product with Model"
    )
    db_session.add(product)
    await db_session.flush()

    product_model = ProductModel(
        product_id=product.id,
        model_id=test_model.id,
        quantity=2
    )
    db_session.add(product_model)
    await db_session.commit()
    await db_session.refresh(product)
    return product

@pytest.fixture
async def other_tenant_product(db_session):
    """Create a product belonging to a different tenant."""
    other_tenant = Tenant(name="Other Tenant", slug="other-tenant")
    db_session.add(other_tenant)
    await db_session.flush()

    product = Product(
        tenant_id=other_tenant.id,
        sku="OTHER-001",
        name="Other Tenant Product"
    )
    db_session.add(product)
    await db_session.commit()
    return product
```

#### 2.2.3 Update pytest Configuration
```toml
# pyproject.toml (additions)
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --cov=app --cov-report=term-missing --cov-report=xml"
filterwarnings = [
    "ignore::DeprecationWarning",
]

[tool.coverage.run]
source = ["app"]
omit = ["app/alembic/*", "app/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
fail_under = 50
```

**Acceptance Criteria**:
- [ ] Backend coverage reaches 50%+
- [ ] All critical paths tested (auth, products, spools)
- [ ] Multi-tenant isolation verified in tests
- [ ] Tests run in < 30 seconds

---

## 3. GitOps CI/CD Pipeline

### 3.1 GitHub Actions CI Pipeline

**Solution**:

#### 3.1.1 Create CI Workflow
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"

jobs:
  # ============================================
  # Backend Tests & Linting
  # ============================================
  backend-lint:
    name: Backend Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        working-directory: backend
        run: poetry install --no-interaction

      - name: Run Ruff (linter)
        working-directory: backend
        run: poetry run ruff check .

      - name: Run Ruff (formatter check)
        working-directory: backend
        run: poetry run ruff format --check .

      - name: Run MyPy (type checking)
        working-directory: backend
        run: poetry run mypy app --ignore-missing-imports

  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    needs: backend-lint

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_nozzly
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        working-directory: backend
        run: poetry install --no-interaction

      - name: Run tests with coverage
        working-directory: backend
        env:
          DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/test_nozzly
          SECRET_KEY: test-secret-key-for-ci-only
          DEBUG: false
        run: |
          poetry run pytest \
            --cov=app \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results.xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: backend/coverage.xml
          flags: backend
          fail_ci_if_error: false

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-test-results
          path: backend/test-results.xml

  # ============================================
  # Frontend Tests & Linting
  # ============================================
  frontend-lint:
    name: Frontend Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run ESLint
        working-directory: frontend
        run: npm run lint

      - name: Run TypeScript type check
        working-directory: frontend
        run: npx tsc --noEmit

  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    needs: frontend-lint
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run tests with coverage
        working-directory: frontend
        run: npm run test:ci

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: frontend/coverage/lcov.info
          flags: frontend
          fail_ci_if_error: false

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: frontend-test-results
          path: frontend/test-results.xml

  # ============================================
  # Build Docker Images
  # ============================================
  build-backend:
    name: Build Backend Image
    runs-on: ubuntu-latest
    needs: [backend-test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}/backend
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-frontend:
    name: Build Frontend Image
    runs-on: ubuntu-latest
    needs: [frontend-test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}/frontend
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VITE_API_URL=https://api.nozzly.app

  # ============================================
  # Security Scanning
  # ============================================
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: [build-backend, build-frontend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner (Backend)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-backend.sarif'

      - name: Run Trivy vulnerability scanner (Frontend)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-frontend.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-backend.sarif'
```

#### 3.1.2 Create CD Workflow (Deployment)
```yaml
# .github/workflows/cd.yml
name: CD Pipeline

on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    name: Deploy to k3s
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - uses: actions/checkout@v4

      - name: Update image tags in manifests
        run: |
          # Update backend deployment
          sed -i "s|image: ghcr.io/.*/backend:.*|image: ghcr.io/${{ github.repository }}/backend:${{ github.sha }}|g" \
            infrastructure/k8s/backend/deployment.yaml

          # Update frontend deployment
          sed -i "s|image: ghcr.io/.*/frontend:.*|image: ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}|g" \
            infrastructure/k8s/frontend/deployment.yaml

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config

      - name: Deploy to k3s
        run: |
          kubectl apply -f infrastructure/k8s/namespace/
          kubectl apply -f infrastructure/k8s/postgres/
          kubectl apply -f infrastructure/k8s/redis/
          kubectl apply -f infrastructure/k8s/backend/
          kubectl apply -f infrastructure/k8s/frontend/
          kubectl apply -f infrastructure/k8s/ingress/

      - name: Verify deployment
        run: |
          kubectl rollout status deployment/nozzly-backend -n nozzly --timeout=300s
          kubectl rollout status deployment/nozzly-frontend -n nozzly --timeout=300s

      - name: Run smoke tests
        run: |
          # Wait for services to be ready
          sleep 30

          # Test backend health endpoint
          kubectl run curl --image=curlimages/curl --rm -i --restart=Never -n nozzly -- \
            curl -sf http://nozzly-backend:8000/health || exit 1

          echo "Smoke tests passed!"
```

---

### 3.2 Branch Protection Rules

Configure in GitHub repository settings:

**Main Branch Protection**:
- [x] Require pull request reviews before merging (1 reviewer)
- [x] Require status checks to pass before merging:
  - `backend-lint`
  - `backend-test`
  - `frontend-lint`
  - `frontend-test`
- [x] Require branches to be up to date before merging
- [x] Restrict who can push to matching branches

---

### 3.3 Dependabot Configuration

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "backend"
    reviewers:
      - "techize"

  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "frontend"
    reviewers:
      - "techize"

  - package-ecosystem: "docker"
    directory: "/backend"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  - package-ecosystem: "docker"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "ci"
```

---

## 4. Implementation Phases

### Phase 1: Critical Security (Day 1-2)
**Estimated Time**: 4-6 hours

| Task | Priority | Est. Time | Dependencies |
|------|----------|-----------|--------------|
| Generate new JWT secret | CRITICAL | 15 min | None |
| Create K8s secrets | CRITICAL | 30 min | New secrets |
| Update deployment manifests | CRITICAL | 30 min | K8s secrets |
| Remove secrets from .env | CRITICAL | 15 min | Deployment update |
| Add rate limiting | HIGH | 2 hours | None |
| Add security headers | HIGH | 1 hour | None |
| Remove hardcoded tenant ID | HIGH | 1 hour | None |
| Test all changes | CRITICAL | 1 hour | All above |

### Phase 2: Testing Infrastructure (Day 2-3)
**Estimated Time**: 6-8 hours

| Task | Priority | Est. Time | Dependencies |
|------|----------|-----------|--------------|
| Install frontend test deps | HIGH | 30 min | None |
| Create vitest config | HIGH | 30 min | Dependencies |
| Create test setup file | HIGH | 30 min | Config |
| Verify SpoolList test runs | HIGH | 15 min | Setup |
| Add auth API tests | HIGH | 2 hours | None |
| Add products API tests | HIGH | 2 hours | None |
| Add spools API tests | MEDIUM | 1 hour | None |
| Update pytest config | MEDIUM | 30 min | None |

### Phase 3: CI/CD Pipeline (Day 3-4)
**Estimated Time**: 4-6 hours

| Task | Priority | Est. Time | Dependencies |
|------|----------|-----------|--------------|
| Create CI workflow | HIGH | 2 hours | None |
| Create CD workflow | HIGH | 1 hour | CI workflow |
| Configure branch protection | MEDIUM | 30 min | CI working |
| Add Dependabot config | MEDIUM | 15 min | None |
| Create K8s secrets for CI | HIGH | 30 min | Cluster access |
| Test full pipeline | HIGH | 2 hours | All above |

### Phase 4: Validation (Day 4-5)
**Estimated Time**: 2-4 hours

| Task | Priority | Est. Time | Dependencies |
|------|----------|-----------|--------------|
| Full regression test | HIGH | 1 hour | All changes |
| Security header verification | HIGH | 30 min | Headers deployed |
| Rate limit verification | HIGH | 30 min | Rate limiting deployed |
| CI/CD end-to-end test | HIGH | 1 hour | Pipeline complete |
| Documentation update | MEDIUM | 1 hour | All verified |

---

## 5. Acceptance Criteria

### Security
- [ ] JWT secret is cryptographically random (64+ chars)
- [ ] All secrets stored in K8s Secrets, not in git
- [ ] No hardcoded UUIDs in codebase
- [ ] Rate limiting returns 429 after threshold
- [ ] All 6 security headers present in responses
- [ ] HTTPS enforced (HSTS header)

### Testing
- [ ] Frontend tests execute with `npm run test`
- [ ] Backend coverage ≥ 50%
- [ ] Frontend coverage ≥ 30%
- [ ] All tests pass in CI
- [ ] Coverage reports upload to Codecov

### CI/CD
- [ ] CI pipeline runs on all PRs
- [ ] Lint failures block merge
- [ ] Test failures block merge
- [ ] Images build and push on main branch
- [ ] Deployment triggers automatically
- [ ] Smoke tests pass post-deployment
- [ ] Dependabot creates weekly PRs

### Quality Gates
- [ ] Branch protection enforced on main
- [ ] At least 1 approval required for PRs
- [ ] Status checks required before merge

---

## Appendix A: Files to Create/Modify

### New Files
- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`
- `.github/dependabot.yml`
- `backend/app/core/rate_limit.py`
- `backend/app/middleware/security.py`
- `backend/tests/integration/test_auth_api.py`
- `backend/tests/integration/test_products_api.py`
- `backend/tests/integration/test_spools_api.py`
- `frontend/vitest.config.ts`
- `frontend/src/test/setup.ts`

### Modified Files
- `backend/app/main.py` (add middleware)
- `backend/app/api/v1/auth.py` (add rate limiting)
- `backend/app/api/v1/shop.py` (remove hardcoded tenant)
- `backend/.env` (remove secrets)
- `backend/.env.example` (update placeholders)
- `backend/pyproject.toml` (add slowapi, update pytest)
- `frontend/package.json` (add test scripts)
- `infrastructure/k8s/backend/deployment.yaml` (use secrets)

### Files to Delete
- None

---

## Appendix B: Risk Mitigation

| Risk | Mitigation |
|------|------------|
| JWT rotation invalidates sessions | Announce maintenance window, users re-login |
| Rate limiting blocks legitimate users | Start with generous limits (5/min), monitor |
| CI pipeline flaky | Add retries, increase timeouts |
| K8s secrets misconfigured | Test in staging first, verify with kubectl |
| Breaking changes in deployment | Use rolling updates, have rollback plan |

---

## Appendix C: Rollback Plan

### If Security Changes Fail
1. Revert K8s deployment: `kubectl rollout undo deployment/nozzly-backend -n nozzly`
2. Restore previous secret values
3. Debug and fix before retrying

### If CI/CD Fails
1. Disable branch protection temporarily
2. Fix pipeline issues
3. Re-enable protection

### If Tests Fail in Production
1. Check if tests are environment-specific
2. Add environment markers to skip integration tests
3. Fix and re-run

---

**Document End**
