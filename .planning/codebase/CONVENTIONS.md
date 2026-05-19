# Coding Conventions

**Analysis Date:** 2026-05-19

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `production_run.py`, `image_storage.py`)
- Python test files: `test_<module_name>.py` (e.g., `test_production_run_service.py`)
- TypeScript components: `PascalCase.tsx` (e.g., `SpoolList.tsx`, `CreateRunWizard.tsx`)
- TypeScript test files: `<ComponentName>.test.tsx` or `<hookName>.test.ts` (co-located)
- TypeScript hooks: `use<Name>.ts` (e.g., `useModules.ts`, `useSKU.ts`)
- TypeScript API modules: `<resource>.ts` under `src/lib/api/`
- TypeScript type definitions: `<resource>.ts` under `src/types/`

**Functions:**
- Python: `snake_case` (e.g., `create_production_run`, `ensure_material_type_exists`)
- TypeScript: `camelCase` (e.g., `createTestQueryClient`, `renderWithQueryClient`)
- React components: `PascalCase`
- React hooks: `use<Name>` prefix enforced by ESLint

**Variables:**
- Python: `snake_case`
- TypeScript: `camelCase` for variables, `UPPER_SNAKE_CASE` for constants (e.g., `TEST_S3_BUCKET`, `SQUARE_ERROR_MESSAGES`)

**Types/Interfaces:**
- Python: `PascalCase` classes (e.g., `SpoolCreate`, `SpoolResponse`, `ProductionRunService`)
- TypeScript interfaces: `PascalCase` with descriptive suffix — `interface SpoolBase`, `interface SpoolListResponse`, `interface SpoolListParams`
- Pydantic schemas follow Base/Create/Update/Response naming pattern

## Code Style

**Formatting (Backend):**
- Tool: `black` + `ruff`
- Line length: 100 characters
- Target: Python 3.11+
- Config: `backend/pyproject.toml`

**Linting (Backend):**
- Tool: `ruff`
- Ignored rules: `F821` (SQLAlchemy string annotations), `E402` (conditional imports)
- Type checking: `mypy` with `disallow_untyped_defs = true`

**Formatting (Frontend):**
- Tool: TypeScript ESLint (`typescript-eslint`)
- Config: `frontend/eslint.config.js`
- Rules: `react-hooks/rules-of-hooks` (error), `react-hooks/exhaustive-deps` (warn)

## Import Organization

**Backend (Python):**
1. Standard library imports
2. Third-party imports (fastapi, sqlalchemy, pydantic, etc.)
3. Local app imports (`from app.auth...`, `from app.database...`, `from app.models...`, `from app.schemas...`)

Example from `backend/app/api/v1/spools.py`:
```python
# stdlib
import csv, io, json
from typing import Optional
from uuid import UUID

# third-party
import yaml
from fastapi import APIRouter, Depends, HTTPException, ...
from sqlalchemy import func, select

# local
from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.spool import Spool
from app.schemas.spool import SpoolCreate, SpoolResponse
```

**Frontend (TypeScript):**
1. External packages (react, vitest, @tanstack/*)
2. Internal aliases using `@/` prefix (e.g., `@/lib/api/spools`, `@/types/spool`)

Path aliases configured in `frontend/vite.config.ts` and `frontend/vitest.config.ts`:
- `@` → `src/`

## Error Handling

**Backend Patterns:**
- HTTP errors: `raise HTTPException(status_code=status.HTTP_4XX_..., detail="message")`
- Database integrity errors: catch `IntegrityError`, rollback, then raise `HTTPException(400)`
- Validation errors handled automatically by Pydantic/FastAPI (returns 422)
- Service errors: log with `logger.error()` then re-raise or rollback
- Auth errors: raise `HTTPException(status_code=401/403)`

```python
# Standard pattern in API endpoints
try:
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid foreign key reference - check material_type_id exists.",
    )
```

**Frontend Patterns:**
- Axios interceptor handles 401 → auto token refresh → redirect to `/login`
- TanStack Query handles retry logic (disabled in tests)
- API errors bubble up through React Query's `error` state

## Logging

**Backend Framework:** Python standard `logging`

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)` at top of each file
- Info for successful state changes: `logger.info(f"Completed production run {run_id}")`
- Warning for non-critical failures: `logger.warning(f"Failed to record metrics: {e}")`
- Error for rollback/failure scenarios: `logger.error(f"Failed to complete production run {run_id}, rolled back: {e}")`
- f-strings used throughout for log message formatting

## Comments

**When to Comment:**
- Module docstrings required: `"""Spool inventory API endpoints."""`
- Class docstrings required with description of purpose
- Function docstrings: used on fixtures and complex functions
- Inline comments for non-obvious logic, tenant isolation, and security decisions
- Section dividers used in test files: `# ============================================`

**Backend Pattern:**
```python
"""Module docstring describing purpose."""

class Spool(Base, UUIDMixin, TimestampMixin):
    """
    Filament spool inventory item.

    Tracks individual spools of 3D printing filament with purchase info,
    weight tracking, and material type.
    """
```

**Frontend Pattern:**
```typescript
/**
 * SKU Generation Hook
 *
 * Provides auto-generation of sequential SKUs for various entity types.
 */
```

## Function Design

**Backend:**
- Async functions for all database operations and API endpoints
- Service methods accept `db: AsyncSession` and `tenant: Tenant` as first parameters
- Dependencies injected via FastAPI `Depends()` — not passed directly
- Functions under ~50 lines; complex orchestration split to service classes

**Frontend:**
- Hooks return destructured named properties (not raw query objects)
- Components receive typed props interfaces

## Module Design

**Backend — Service Layer Pattern:**
- Services are classes instantiated per-request: `ProductionRunService(db, tenant, user=None)`
- Located in `backend/app/services/`
- Methods are `async def` throughout

**Backend — Schema Layer Pattern:**
- Pydantic v2 with `ConfigDict` and `model_dump()`
- Base → Create → Update → Response inheritance hierarchy
- Field validation uses `Field(..., min_length=1, description="...")`

**Frontend — API Module Pattern:**
- API functions grouped by resource in `src/lib/api/<resource>.ts`
- Hooks wrap API functions with TanStack Query in `src/hooks/use<Name>.ts`
- Types mirroring backend Pydantic schemas in `src/types/<resource>.ts`

## Multi-Tenant Security Convention

Every model has `tenant_id` FK column. Every API endpoint injects `CurrentTenant` via `Depends(get_current_tenant)`. Services receive tenant as constructor parameter and scope all queries to it.

```python
@router.post("", response_model=SpoolResponse, status_code=status.HTTP_201_CREATED)
async def create_spool(
    spool_data: SpoolCreate,
    user: CurrentUser,           # Auth — REQUIRED
    tenant: CurrentTenant,       # Tenant scope — REQUIRED
    db: AsyncSession = Depends(get_db),
) -> SpoolResponse:
```

---

*Convention analysis: 2026-05-19*
