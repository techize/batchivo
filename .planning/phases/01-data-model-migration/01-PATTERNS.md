# Phase 1: Data Model Migration - Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 9 (3 new, 6 modified)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/models/filament_type.py` | model | CRUD | `backend/app/models/spool.py` | exact |
| `backend/app/schemas/filament_type.py` | schema | request-response | `backend/app/schemas/spool.py` | exact |
| `backend/alembic/versions/XXXX_filament_type_migration.py` | migration | batch | `backend/alembic/versions/b2c3d4e5f6g7_add_customers.py` + `backend/alembic/versions/8c3c671816d9_create_rls_policies.py` | exact (composite) |
| `backend/app/api/v1/filament_types.py` | controller | CRUD | `backend/app/api/v1/spools.py` | exact |
| `backend/app/modules/threed_print/filament_types.py` | module | request-response | `backend/app/modules/threed_print/consumables.py` | exact |
| `backend/app/models/spool.py` | model | CRUD | `backend/app/models/spool.py` (self) | self |
| `backend/app/schemas/spool.py` | schema | request-response | `backend/app/schemas/spool.py` (self) | self |
| `backend/app/modules/threed_print/spools.py` | module | request-response | `backend/app/modules/threed_print/spools.py` (self) | self |
| `backend/app/modules/threed_print/__init__.py` | config | — | `backend/app/modules/threed_print/__init__.py` (self) | self |
| `backend/tests/conftest.py` | test | — | `backend/tests/conftest.py` (self — add fixture) | self |
| `backend/alembic/env.py` | config | — | `backend/alembic/env.py` (self — add import) | self |

---

## Pattern Assignments

### `backend/app/models/filament_type.py` (model, CRUD)

**Analog:** `backend/app/models/spool.py`

**Imports pattern** (spool.py lines 1-12):
```python
"""Filament type definition model."""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
```

**Class skeleton with tenant_id pattern** (spool.py lines 14-38):
```python
class FilamentType(Base, UUIDMixin, TimestampMixin):
    """Shared filament type definition."""

    __tablename__ = "filament_types"

    # Tenant isolation — REQUIRED on every tenant-scoped model
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Reference to material type (global, no tenant_id)
    material_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_types.id"),
        nullable=False,
        index=True,
        comment="Material type (PLA, PETG, etc.)",
    )
```

**Numeric/String field pattern** (spool.py lines 73-98):
```python
    diameter: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=1.75,
        server_default="1.75",
        comment="Filament diameter in mm (typically 1.75 or 2.85)",
    )

    density: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Filament density in g/cm³ (e.g., 1.24 for PLA)",
    )

    extruder_temp: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Recommended extruder temperature in °C",
    )
```

**Boolean field pattern** (spool.py lines 101-110):
```python
    translucent: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether filament is translucent/transparent",
    )

    glow: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether filament is glow-in-the-dark",
    )
```

**Relationship pattern with lazy="joined"** (spool.py lines 209-213):
```python
    # Relationships
    material_type: Mapped["MaterialType"] = relationship(
        "MaterialType",
        lazy="joined",
    )
```

**Spool back-reference** (new, mirrors spool.py production_run_materials at lines 215-219):
```python
    spools: Mapped[list["Spool"]] = relationship(
        "Spool",
        back_populates="filament_type",
        lazy="select",
    )
```

---

### `backend/app/schemas/filament_type.py` (schema, request-response)

**Analog:** `backend/app/schemas/spool.py`

**Imports pattern** (spool.py lines 1-7):
```python
"""Pydantic schemas for FilamentType API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
```

**Base schema with Field validators** (spool.py lines 11-61, adapted for FilamentType fields):
```python
class FilamentTypeBase(BaseModel):
    """Base filament type schema with common fields."""

    material_type_id: UUID = Field(..., description="Material type ID (PLA, PETG, etc.)")
    brand: str = Field(..., min_length=1, max_length=100, description="Filament brand")
    color: str = Field(..., min_length=1, max_length=50, description="Filament color")
    color_hex: Optional[str] = Field(None, max_length=9, description="Hex color code (e.g., FF5733)")
    finish: Optional[str] = Field(None, max_length=50, description="Finish type (matte, glossy, etc.)")
    diameter: float = Field(1.75, gt=0, le=5, description="Filament diameter in mm")
    density: Optional[float] = Field(None, gt=0, le=10, description="Filament density in g/cm³")
    extruder_temp: Optional[int] = Field(None, ge=150, le=400, description="Recommended extruder temp °C")
    bed_temp: Optional[int] = Field(None, ge=0, le=150, description="Recommended bed temp °C")
    translucent: bool = Field(False, description="Whether filament is translucent")
    glow: bool = Field(False, description="Whether filament is glow-in-the-dark")
    pattern: Optional[str] = Field(None, max_length=50, description="Pattern type (marble, etc.)")
    spool_type: Optional[str] = Field(None, max_length=50, description="Spool type (cardboard, plastic, etc.)")
    notes: Optional[str] = Field(None, description="Additional notes")
    has_sample: bool = Field(False, description="Whether a sample benchy has been printed")
```

**Create schema pattern** (spool.py lines 64-68):
```python
class FilamentTypeCreate(FilamentTypeBase):
    """Schema for creating a new filament type."""

    pass  # Inherits all fields from FilamentTypeBase
```

**Update schema pattern — all Optional** (spool.py lines 71-112):
```python
class FilamentTypeUpdate(BaseModel):
    """Schema for updating a filament type (all fields optional)."""

    material_type_id: Optional[UUID] = None
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=50)
    # ... all fields Optional, same Field validators as Base
```

**Response schema with ConfigDict** (spool.py lines 115-132):
```python
class FilamentTypeResponse(FilamentTypeBase):
    """Schema for filament type responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Material type info (nested — from lazy="joined" relationship)
    material_type_code: str = Field(..., description="Material code (PLA, PETG, etc.)")
    material_type_name: str = Field(..., description="Material name")

    model_config = ConfigDict(from_attributes=True)


class FilamentTypeListResponse(BaseModel):
    """Schema for paginated filament type list."""

    total: int = Field(..., description="Total number of filament types")
    filament_types: list[FilamentTypeResponse]
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
```

---

### `backend/alembic/versions/XXXX_filament_type_migration.py` (migration, batch)

**Composite analog:** `backend/alembic/versions/b2c3d4e5f6g7_add_customers.py` (create_table DDL pattern) + `backend/alembic/versions/8c3c671816d9_create_rls_policies.py` (RLS policy pattern)

**File header / revision identifiers** (b2c3d4e5f6g7 lines 1-19):
```python
"""Create filament_type table and migrate spools to two-tier structure.

Revision ID: XXXX
Revises: (tuple of all 5 current heads — see RESEARCH.md Pitfall 1)
Create Date: 2026-05-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "XXXX"
down_revision: Union[str, Sequence[str], None] = (
    "a0b1c2d3e4f5",
    "h2i3j4k5l6m7",
    "s6t7u8v9w0x1",
    "y2z3a4b5c6d7",
    "k2l3m4n5o6p7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**create_table DDL pattern** (b2c3d4e5f6g7 lines 23-132 — use this structure for filament_types table):
```python
def upgrade() -> None:
    # ── Step 1: FAIL FAST ─────────────────────────────────────────────────
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT id FROM spools WHERE brand IS NULL OR color IS NULL"
    ))
    null_rows = result.fetchall()
    if null_rows:
        ids = [str(r[0]) for r in null_rows]
        raise RuntimeError(
            f"Migration aborted: {len(ids)} spool(s) have NULL brand or color. "
            f"Fix these spool IDs before running: {ids}"
        )

    # ── Step 2: Create filament_types table ───────────────────────────────
    op.create_table(
        "filament_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False,
                  comment="Tenant ID for multi-tenant isolation"),
        sa.Column("material_type_id", sa.UUID(), nullable=False),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("color", sa.String(50), nullable=False),
        # ... all FilamentType fields
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_type_id"], ["material_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_filament_types_tenant_id"), "filament_types", ["tenant_id"])
    op.create_index(op.f("ix_filament_types_material_type_id"), "filament_types", ["material_type_id"])
```

**RLS policy pattern — inline after table creation** (8c3c671816d9 lines 91-156):
```python
    # ── Step N: Enable RLS on new table (inline — not a separate migration) ─
    op.execute(text("ALTER TABLE filament_types ENABLE ROW LEVEL SECURITY"))
    op.execute(text("ALTER TABLE filament_types FORCE ROW LEVEL SECURITY"))

    op.execute(text("""
        CREATE POLICY tenant_isolation_select ON filament_types
        FOR SELECT USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
    op.execute(text("""
        CREATE POLICY tenant_isolation_insert ON filament_types
        FOR INSERT WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
    op.execute(text("""
        CREATE POLICY tenant_isolation_update ON filament_types
        FOR UPDATE USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
    op.execute(text("""
        CREATE POLICY tenant_isolation_delete ON filament_types
        FOR DELETE USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
```

**downgrade() pattern** (b2c3d4e5f6g7 lines 261-275):
```python
def downgrade() -> None:
    # Drop FK + index first, then drop column, then restore old columns
    op.drop_constraint("fk_spools_filament_type_id", "spools", type_="foreignkey")
    op.drop_column("spools", "filament_type_id")
    op.drop_column("spools", "is_labeled")

    # Restore removed columns as nullable (D-08: NULL-filled is acceptable)
    op.add_column("spools", sa.Column("purchased_quantity", sa.Integer(), nullable=True))
    op.add_column("spools", sa.Column("spools_remaining", sa.Integer(), nullable=True))
    # Restore all brand/color/type fields as nullable
    op.add_column("spools", sa.Column("brand", sa.String(100), nullable=True))
    # ... etc.

    # Drop RLS policies before dropping table
    op.execute(text("DROP POLICY IF EXISTS tenant_isolation_select ON filament_types"))
    op.execute(text("DROP POLICY IF EXISTS tenant_isolation_insert ON filament_types"))
    op.execute(text("DROP POLICY IF EXISTS tenant_isolation_update ON filament_types"))
    op.execute(text("DROP POLICY IF EXISTS tenant_isolation_delete ON filament_types"))

    # Drop indexes and table
    op.drop_index(op.f("ix_filament_types_material_type_id"), table_name="filament_types")
    op.drop_index(op.f("ix_filament_types_tenant_id"), table_name="filament_types")
    op.drop_table("filament_types")
```

---

### `backend/app/api/v1/filament_types.py` (controller, CRUD)

**Analog:** `backend/app/api/v1/spools.py`

**Imports pattern — CRITICAL: use TenantDB not get_db** (spools.py lines 1-22, corrected):
```python
"""FilamentType CRUD API endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser, TenantDB
from app.models.filament_type import FilamentType
from app.schemas.filament_type import (
    FilamentTypeCreate,
    FilamentTypeListResponse,
    FilamentTypeResponse,
    FilamentTypeUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Helper function pattern** (spools.py lines 27-35):
```python
def filament_type_to_response(ft: FilamentType) -> dict:
    """Convert FilamentType model to response dict."""
    return {
        **ft.__dict__,
        "material_type_code": ft.material_type.code if ft.material_type else "UNKNOWN",
        "material_type_name": ft.material_type.name if ft.material_type else "Unknown",
    }
```

**POST handler pattern** (spools.py lines 48-80):
```python
@router.post("", response_model=FilamentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_filament_type(
    data: FilamentTypeCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,  # TenantDB — NOT Depends(get_db)
) -> FilamentTypeResponse:
    """Create a new filament type. Requires authentication."""
    ft = FilamentType(tenant_id=tenant.id, **data.model_dump())
    db.add(ft)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference — check material_type_id exists.",
        )
    await db.refresh(ft)
    return FilamentTypeResponse(**filament_type_to_response(ft))
```

**GET list with pagination pattern** (spools.py lines 83-149):
```python
@router.get("", response_model=FilamentTypeListResponse)
async def list_filament_types(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FilamentTypeListResponse:
    query = select(FilamentType).where(FilamentType.tenant_id == tenant.id)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(FilamentType.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return FilamentTypeListResponse(
        total=total,
        filament_types=[FilamentTypeResponse(**filament_type_to_response(ft)) for ft in items],
        page=page,
        page_size=page_size,
    )
```

**GET by ID with 404 pattern** (spools.py lines 251-278):
```python
@router.get("/{filament_type_id}", response_model=FilamentTypeResponse)
async def get_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> FilamentTypeResponse:
    result = await db.execute(
        select(FilamentType).where(
            FilamentType.id == filament_type_id,
            FilamentType.tenant_id == tenant.id,
        )
    )
    ft = result.scalar_one_or_none()
    if not ft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FilamentType {filament_type_id} not found",
        )
    return FilamentTypeResponse(**filament_type_to_response(ft))
```

**PUT update pattern using model_dump(exclude_unset=True)** (spools.py lines 281-329):
```python
@router.put("/{filament_type_id}", response_model=FilamentTypeResponse)
async def update_filament_type(
    filament_type_id: UUID,
    data: FilamentTypeUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> FilamentTypeResponse:
    # ... select with tenant filter, 404 if missing
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ft, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid FK reference.")
    await db.refresh(ft)
    return FilamentTypeResponse(**filament_type_to_response(ft))
```

**DELETE pattern** (spools.py lines 332-360):
```python
@router.delete("/{filament_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filament_type(
    filament_type_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,
) -> None:
    # ... select with tenant filter, 404 if missing
    await db.delete(ft)
    await db.commit()
```

---

### `backend/app/modules/threed_print/filament_types.py` (module, request-response)

**Analog:** `backend/app/modules/threed_print/consumables.py` (exact match)

**Full file pattern** (consumables.py lines 1-33):
```python
"""FilamentType module for 3D print tenants."""

from fastapi import APIRouter

from app.modules.base import BaseModule
from app.schemas.tenant_settings import TenantType


class FilamentTypesModule(BaseModule):
    """
    Filament type definition management module.

    Provides functionality for:
    - Managing shared filament type definitions (brand, color, material, specs)
    - Decoupling filament type data from individual spool records
    """

    name = "filament_types"
    display_name = "Filament Types"
    icon = "layers"
    description = "Manage filament type definitions for 3D printing"

    # Same tenant types as spools
    tenant_types = [TenantType.THREE_D_PRINT, TenantType.GENERIC]

    def register_routes(self, router: APIRouter) -> None:
        """Register filament type management routes."""
        from app.api.v1 import filament_types

        for route in filament_types.router.routes:
            router.routes.append(route)
```

---

### `backend/app/models/spool.py` (MODIFIED — remove type fields, add filament_type_id + is_labeled)

**Analog:** Self — apply surgical changes per D-01/D-02/D-03

**Fields to REMOVE** (current spool.py lines 33-38, 48-118, 164-178, 187-192):
- `material_type_id` FK column and index (moves to FilamentType)
- `brand`, `color`, `color_hex`, `finish` (lines 48-69)
- `diameter`, `density`, `extruder_temp`, `bed_temp` (lines 73-98)
- `translucent`, `glow`, `pattern`, `spool_type` (lines 101-123)
- `purchased_quantity`, `spools_remaining` (lines 164-178)
- `notes` (lines 187-192)
- `material_type` relationship (lines 210-213)

**Fields to ADD** — copy FK pattern from existing material_type_id (lines 33-38):
```python
    filament_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("filament_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FilamentType this spool belongs to",
    )

    is_labeled: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether a physical label has been printed for this spool",
    )
```

**Relationship to ADD** — copy lazy="joined" pattern from existing (lines 210-213):
```python
    filament_type: Mapped["FilamentType"] = relationship(
        "FilamentType",
        lazy="joined",
    )
```

**__repr__ to update** (spool.py line 222):
```python
    def __repr__(self) -> str:
        ft = self.filament_type
        return f"<Spool(id={self.spool_id}, type={ft.brand}/{ft.color if ft else 'N/A'})>"
```

---

### `backend/app/schemas/spool.py` (MODIFIED — replace inline type fields with filament_type_id)

**Analog:** Self — apply surgical field changes

**Fields to REMOVE from SpoolBase** (lines 15-39 of current spool.py):
- `material_type_id`, `brand`, `color`, `color_hex`, `finish`
- `diameter`, `density`, `extruder_temp`, `bed_temp`
- `translucent`, `glow`, `pattern`, `spool_type`
- `purchased_quantity`, `spools_remaining`
- `notes`

**Fields to ADD to SpoolBase** — copy existing Field pattern:
```python
    filament_type_id: UUID = Field(..., description="FilamentType ID")
    is_labeled: bool = Field(False, description="Whether a label has been printed for this spool")
```

**SpoolResponse to UPDATE** — nest FilamentTypeResponse instead of flat material_type fields (copy nested pattern approach from SpoolResponse lines 115-132):
```python
class SpoolResponse(SpoolBase):
    """Schema for spool responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    remaining_weight: float = Field(..., description="Remaining weight in grams")
    remaining_percentage: float = Field(..., description="Remaining percentage")

    # Nested filament type (loaded via lazy="joined" relationship)
    filament_type: "FilamentTypeResponse"

    model_config = ConfigDict(from_attributes=True)
```

---

### `backend/app/modules/threed_print/__init__.py` (MODIFIED — add FilamentTypesModule)

**Analog:** Self — add two lines following exact pattern (lines 4-13 and 23-33):

```python
# Add import (after existing SpoolsModule import):
from app.modules.threed_print.filament_types import FilamentTypesModule

# Add to get_modules() return list (before SpoolsModule or after — logically first):
def get_modules() -> list[BaseModule]:
    return [
        FilamentTypesModule(),   # ← ADD
        SpoolsModule(),
        # ... rest unchanged
    ]

# Add to __all__:
__all__ = [
    "FilamentTypesModule",   # ← ADD
    "SpoolsModule",
    # ... rest unchanged
]
```

---

### `backend/tests/conftest.py` (MODIFIED — add test_filament_type fixture)

**Analog:** Self — copy `test_spool` fixture pattern (lines 375-395):

```python
@pytest_asyncio.fixture(scope="function")
async def test_filament_type(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_material_type: MaterialType,
) -> "FilamentType":
    """Create a test filament type."""
    from app.models.filament_type import FilamentType

    ft = FilamentType(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        brand="Test Brand",
        color="Red",
        diameter=1.75,
        has_sample=False,
        translucent=False,
        glow=False,
    )
    db_session.add(ft)
    await db_session.commit()
    await db_session.refresh(ft)
    return ft
```

**Also add to imports at top of conftest.py** (lines 26-31, after existing model imports):
```python
from app.models.filament_type import FilamentType
```

**Update test_spool fixture** (lines 375-395) — replace `material_type_id` + `brand` + `color` fields with `filament_type_id`, remove `brand`/`color`:
```python
@pytest_asyncio.fixture(scope="function")
async def test_spool(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_filament_type: FilamentType,  # ← depends on FilamentType fixture
) -> Spool:
    """Create a test spool."""
    spool = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        filament_type_id=test_filament_type.id,  # ← new FK
        spool_id="TEST-SPOOL-001",
        initial_weight=1000.0,
        current_weight=800.0,
        purchase_price=Decimal("25.00"),
        is_active=True,
        is_labeled=False,
    )
    # ... rest unchanged
```

---

### `backend/alembic/env.py` (MODIFIED — add FilamentType import)

**Analog:** Self — copy exact import line pattern (lines 38-41):

```python
# Add after existing model imports (lines 38-41):
from app.models.filament_type import FilamentType  # noqa: F401
```

---

## Shared Patterns

### TenantDB (RLS-enabled database session)
**Source:** `backend/app/auth/dependencies.py` lines 249-296
**Apply to:** All new FilamentType endpoints — `filament_types.py` controller
**Critical:** The existing `spools.py` uses `Depends(get_db)` (no RLS). New endpoints MUST use `TenantDB`:
```python
# CORRECT — use this in all new FilamentType routes
from app.auth.dependencies import TenantDB

@router.get("")
async def list_filament_types(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: TenantDB,          # ← TenantDB not AsyncSession = Depends(get_db)
) -> FilamentTypeListResponse:
```

### CurrentUser + CurrentTenant type aliases
**Source:** `backend/app/auth/dependencies.py` lines 218-220
**Apply to:** All protected endpoints in `filament_types.py` and updated `spools.py`
```python
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
```

### Error handling — IntegrityError pattern
**Source:** `backend/app/api/v1/spools.py` lines 70-77 and 319-326
**Apply to:** All POST and PUT handlers in `filament_types.py`
```python
try:
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid foreign key reference — check material_type_id exists.",
    )
```

### Module logger
**Source:** Any `backend/app/api/v1/*.py` file
**Apply to:** `filament_types.py` controller
```python
import logging
logger = logging.getLogger(__name__)
```

### Alembic raw SQL (no ORM in migrations)
**Source:** `backend/alembic/versions/q4r5s6t7u8v9_split_filament_tracking.py` lines 26-28 — uses only `op.*` and `sa.Column`, never imports model classes
**Apply to:** XXXX migration file — all data operations use `op.get_bind()` + `sa.text()`
```python
# In upgrade(), for data operations:
conn = op.get_bind()
conn.execute(sa.text("SELECT ..."))
conn.execute(sa.text("INSERT INTO ..."))
conn.execute(sa.text("UPDATE ..."))
```

### Field comment convention
**Source:** `backend/app/models/spool.py` throughout
**Apply to:** All columns in `filament_type.py` model
```python
# Every mapped_column gets a comment= kwarg describing the field purpose
comment="Tenant ID for multi-tenant isolation"
```

---

## No Analog Found

All files have close analogs in the codebase. No new patterns are required.

---

## Metadata

**Analog search scope:** `backend/app/models/`, `backend/app/schemas/`, `backend/app/api/v1/`, `backend/app/modules/threed_print/`, `backend/app/auth/`, `backend/alembic/versions/`, `backend/tests/`
**Files scanned:** 14
**Pattern extraction date:** 2026-05-19
