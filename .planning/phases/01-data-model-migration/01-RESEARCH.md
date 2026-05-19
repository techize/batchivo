# Phase 1: Data Model Migration - Research

**Researched:** 2026-05-19
**Domain:** SQLAlchemy 2.0 async models, Alembic data migrations, PostgreSQL RLS
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** FilamentType fields: `brand`, `color`, `color_hex`, `finish`, `pattern`, `spool_type`, `translucent`, `glow`, `diameter`, `density`, `extruder_temp`, `bed_temp`, `notes`, `has_sample` (new).
- **D-02:** Spool retains: `spool_id`, `initial_weight`, `current_weight`, `empty_spool_weight`, `storage_location`, `qr_code_id`, `is_active`, `is_labeled` (new), `purchase_price`, `supplier`, `purchase_date`.
- **D-03:** `material_type_id` FK moves from Spool to FilamentType. Spool gets new `filament_type_id` FK.
- **D-04:** Deduplication key is `brand + color + material_type_id` (case-sensitive, NULL = non-matching). Diameter is NOT in the key.
- **D-05:** When multiple spools share a deduplication key, the **oldest spool by `created_at`** supplies the shared field values (color_hex, density, temps, finish, pattern, etc.).
- **D-06:** NULL `brand` or NULL `color` on any existing Spool — migration fails fast with a list of affected spool IDs. No proceeding with nulls.
- **D-07:** `purchased_quantity` and `spools_remaining` removed in this migration (clean break).
- **D-08:** Full `downgrade()` path required: restore `purchased_quantity` and `spools_remaining` (NULL-filled), drop FilamentType table, restore brand/color/etc. on Spool.

### Claude's Discretion

None — all decisions were locked.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | System has a FilamentType model storing brand, color, material type, diameter, finish, pattern, temperatures, and notes as a shared definition record | FilamentType model design section covers all fields; RLS section covers tenant enforcement |
| DATA-02 | Spool model references FilamentType instead of duplicating all filament properties; retains unique spool_id, weight, storage location, QR code, is_active | Spool field split (D-01/D-02) maps directly; existing relationship pattern (`lazy="joined"`) applies |
| DATA-03 | Existing Spool records are migrated to the new two-tier structure without data loss | Data backfill strategy section covers deduplication logic and ordered steps |
| DATA-04 | FilamentType has `has_sample` boolean field | Field included in FilamentType design; default False |
| DATA-05 | Spool has `is_labeled` boolean field | Field included in Spool model update; default False |

</phase_requirements>

---

## Summary

Phase 1 is a pure backend migration: create a new `filament_types` table, restructure the `spools` table, and backfill existing data in a single Alembic migration. The codebase already uses all the patterns needed — `UUIDMixin + TimestampMixin`, tenant_id with RLS, `lazy="joined"` FK relationships, and Pydantic Base/Create/Update/Response schema hierarchies.

The migration is the highest-risk deliverable. It must: (1) fail fast on NULL brand/color data, (2) deduplicate spools into FilamentType records using the oldest spool's values, (3) set each spool's new `filament_type_id`, (4) remove deprecated columns, and (5) include a complete downgrade path. The migration runs as the database superuser so RLS policies do not block it.

A significant pre-existing issue was discovered: **the existing `spools.py` API uses `get_db` instead of `get_tenant_db`**, meaning RLS is currently bypassed on spool endpoints. This must be corrected on the new FilamentType endpoints and flagged as a remediation task for the existing Spool endpoints.

**Primary recommendation:** Write the migration as a hand-crafted `upgrade()` body using `op.get_bind()` + `sa.text()` for the data backfill. Do not attempt to use ORM session in Alembic — use raw SQL for all data operations.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FilamentType persistence | Database/Storage | — | New table with RLS enforcement at PostgreSQL layer |
| Data deduplication/backfill | Database/Storage | — | Pure SQL in Alembic upgrade() — no ORM |
| FilamentType CRUD API | API/Backend | — | FastAPI router, new file `filament_types.py` |
| Spool FK update (filament_type_id) | Database/Storage | API/Backend | Schema change in migration; endpoint update in API layer |
| RLS enforcement | Database/Storage | — | PostgreSQL policies via `app.current_tenant_id` session variable |
| Schema validation | API/Backend | — | Pydantic schemas for FilamentType and updated Spool |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0 (async) | ORM and model definitions | Already in use; all models follow this pattern [VERIFIED: codebase] |
| Alembic | >=1.13.0 | Database migrations | Already in use; ~90 migrations in `backend/alembic/versions/` [VERIFIED: codebase] |
| Pydantic v2 | >=2.0 | Schema validation | Project standard; all schemas use `ConfigDict` and `model_dump()` [VERIFIED: codebase] |
| psycopg[binary,pool] | >=3.1.0 | PostgreSQL async driver | Project standard [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sa.text()` | (built-in) | Raw SQL in Alembic data migrations | Data backfill logic — never use ORM in migrations |
| `op.get_bind()` | (built-in) | Get connection in Alembic upgrade() | Required for executing raw SQL in sync migration body |

**No new packages required.** [VERIFIED: codebase]

---

## Package Legitimacy Audit

No new packages are introduced in this phase. All dependencies are existing project dependencies.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Existing Spool (flat)                    New Two-Tier Structure
┌──────────────────────┐                 ┌──────────────────────┐
│ Spool                │                 │ FilamentType         │
│ ├─ tenant_id (FK)    │   migration →   │ ├─ tenant_id (FK)    │
│ ├─ material_type_id  │                 │ ├─ material_type_id  │
│ ├─ brand             │                 │ ├─ brand             │
│ ├─ color             │                 │ ├─ color             │
│ ├─ color_hex         │                 │ ├─ color_hex         │
│ ├─ finish            │                 │ ├─ finish            │
│ ├─ diameter          │                 │ ├─ diameter          │
│ ├─ density           │                 │ ├─ density           │
│ ├─ extruder_temp     │                 │ ├─ extruder_temp     │
│ ├─ bed_temp          │                 │ ├─ bed_temp          │
│ ├─ translucent       │                 │ ├─ translucent       │
│ ├─ glow              │                 │ ├─ glow              │
│ ├─ pattern           │                 │ ├─ pattern           │
│ ├─ spool_type        │                 │ ├─ spool_type        │
│ ├─ notes             │                 │ ├─ notes             │
│ ├─ purchased_quantity│                 │ └─ has_sample        │
│ ├─ spools_remaining  │                 └──────────────────────┘
│ ├─ spool_id          │                          │ 1
│ ├─ initial_weight    │                          │
│ ├─ current_weight    │                          │ N
│ ├─ empty_spool_weight│                 ┌──────────────────────┐
│ ├─ storage_location  │                 │ Spool (per-unit)     │
│ ├─ qr_code_id        │                 │ ├─ tenant_id (FK)    │
│ ├─ is_active         │                 │ ├─ filament_type_id  │◄─── NEW FK
│ ├─ purchase_price    │                 │ ├─ spool_id          │
│ ├─ supplier          │                 │ ├─ initial_weight    │
│ └─ purchase_date     │                 │ ├─ current_weight    │
└──────────────────────┘                 │ ├─ empty_spool_weight│
                                         │ ├─ storage_location  │
                                         │ ├─ qr_code_id        │
                                         │ ├─ is_active         │
                                         │ ├─ is_labeled        │◄─── NEW
                                         │ ├─ purchase_price    │
                                         │ ├─ supplier          │
                                         └─ purchase_date       │
                                         └──────────────────────┘

API Layer:
  GET/POST/PUT/DELETE /api/v1/filament-types   ← new router
  GET/POST/PUT/DELETE /api/v1/spools           ← updated (filament_type_id replaces inline fields)
```

### Recommended Project Structure
```
backend/app/models/
├── filament_type.py          # NEW: FilamentType model
├── spool.py                  # UPDATED: remove type fields, add filament_type_id + is_labeled
└── ...

backend/app/schemas/
├── filament_type.py          # NEW: Base/Create/Update/Response schemas
├── spool.py                  # UPDATED: remove type fields, add filament_type_id + is_labeled

backend/app/api/v1/
├── filament_types.py         # NEW: CRUD endpoints for FilamentType
├── spools.py                 # UPDATED: accepts filament_type_id, drops brand/color direct fields

backend/alembic/versions/
└── XXXX_filament_type_model_and_spool_migration.py  # NEW: single migration

backend/tests/
├── unit/test_filament_type_schemas.py    # NEW
├── integration/test_filament_types_api.py  # NEW
├── integration/test_spools_api.py        # UPDATED
└── conftest.py                           # UPDATED: add test_filament_type fixture
```

### Pattern 1: SQLAlchemy 2.0 Async Model with Tenant Scope

All tenant-scoped models follow this exact pattern. FilamentType must mirror it. [VERIFIED: codebase — spool.py, ams_slot_mapping.py, customer.py]

```python
# Source: backend/app/models/spool.py (existing pattern)
import uuid
from sqlalchemy import ForeignKey, String, Text, Boolean, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

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

    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    color_hex: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)
    finish: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    diameter: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False, default=1.75, server_default="1.75"
    )
    density: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
    extruder_temp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bed_temp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    translucent: Mapped[bool] = mapped_column(default=False, nullable=False)
    glow: Mapped[bool] = mapped_column(default=False, nullable=False)
    pattern: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    spool_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_sample: Mapped[bool] = mapped_column(
        default=False, nullable=False,
        comment="Whether a display benchy has been printed for this filament type",
    )

    # Relationships
    material_type: Mapped["MaterialType"] = relationship("MaterialType", lazy="joined")
    spools: Mapped[list["Spool"]] = relationship(
        "Spool", back_populates="filament_type", lazy="select"
    )
```

### Pattern 2: Alembic Data Migration — create table + backfill + modify existing table

The codebase uses `op.get_bind()` + `sa.text()` for data operations in migrations. [VERIFIED: codebase — a0b1c2d3e4f5]

```python
# Source: alembic migration pattern from codebase
def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: FAIL FAST — check for NULL brand or color
    result = conn.execute(sa.text(
        "SELECT id FROM spools WHERE brand IS NULL OR color IS NULL"
    ))
    null_rows = result.fetchall()
    if null_rows:
        ids = [str(r[0]) for r in null_rows]
        raise RuntimeError(
            f"Migration aborted: {len(ids)} spool(s) have NULL brand or color. "
            f"Fix these before running migration: {ids}"
        )

    # Step 2: Create filament_types table
    op.create_table("filament_types", ...)

    # Step 3: Insert FilamentType records (deduplication + oldest-spool values)
    conn.execute(sa.text("""
        INSERT INTO filament_types (id, tenant_id, material_type_id, brand, color, ...)
        SELECT
            gen_random_uuid(),
            tenant_id,
            material_type_id,
            brand,
            color,
            ...
        FROM (
            SELECT DISTINCT ON (tenant_id, brand, color, material_type_id)
                tenant_id, material_type_id, brand, color,
                color_hex, finish, diameter, density, extruder_temp, bed_temp,
                translucent, glow, pattern, spool_type, notes,
                now() AS created_at, now() AS updated_at,
                false AS has_sample
            FROM spools
            ORDER BY tenant_id, brand, color, material_type_id, created_at ASC
        ) oldest_spool
    """))

    # Step 4: Add filament_type_id column to spools (nullable initially)
    op.add_column("spools", sa.Column("filament_type_id", sa.UUID(), nullable=True))

    # Step 5: Populate filament_type_id on each spool
    conn.execute(sa.text("""
        UPDATE spools s
        SET filament_type_id = ft.id
        FROM filament_types ft
        WHERE s.tenant_id = ft.tenant_id
          AND s.brand = ft.brand
          AND s.color = ft.color
          AND s.material_type_id = ft.material_type_id
    """))

    # Step 6: Make filament_type_id NOT NULL now that it's populated
    op.alter_column("spools", "filament_type_id", nullable=False)

    # Step 7: Add FK constraint
    op.create_foreign_key("fk_spools_filament_type_id", "spools", "filament_types", ...)

    # Step 8: Add is_labeled column
    op.add_column("spools", sa.Column("is_labeled", sa.Boolean(), nullable=False,
        server_default="false"))

    # Step 9: Drop deprecated columns and migrated columns from spools
    for col in ("brand", "color", "color_hex", "finish", "diameter", "density",
                "extruder_temp", "bed_temp", "translucent", "glow", "pattern",
                "spool_type", "notes", "material_type_id",
                "purchased_quantity", "spools_remaining"):
        op.drop_column("spools", col)
```

### Pattern 3: RLS — New Tenant-Scoped Table Registration

When a new tenant-scoped table is added after the initial RLS migrations, the correct pattern is to include `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` statements **inline in the same migration that creates the table**. [VERIFIED: codebase — a1b2c3d4e5f6 and cffc14267961/8c3c671816d9 confirm the precedent]

```python
# Source: pattern from 8c3c671816d9_create_rls_policies.py
def upgrade() -> None:
    # ... create table, backfill data ...

    # Enable RLS on new table
    op.execute(sa.text("ALTER TABLE filament_types ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("ALTER TABLE filament_types FORCE ROW LEVEL SECURITY"))

    # Four policies matching the existing pattern
    op.execute(sa.text("""
        CREATE POLICY tenant_isolation_select ON filament_types
        FOR SELECT USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
    op.execute(sa.text("""
        CREATE POLICY tenant_isolation_insert ON filament_types
        FOR INSERT WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
    op.execute(sa.text("""
        CREATE POLICY tenant_isolation_update ON filament_types
        FOR UPDATE USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
    op.execute(sa.text("""
        CREATE POLICY tenant_isolation_delete ON filament_types
        FOR DELETE USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
    """))
```

### Pattern 4: Pydantic Schema Hierarchy

All schemas in the project follow Base/Create/Update/Response with `ConfigDict(from_attributes=True)` on Response. [VERIFIED: codebase — backend/app/schemas/spool.py]

```python
# Source: backend/app/schemas/spool.py (existing pattern to replicate)
class FilamentTypeBase(BaseModel):
    material_type_id: UUID
    brand: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., min_length=1, max_length=50)
    # ... all fields

class FilamentTypeCreate(FilamentTypeBase):
    pass

class FilamentTypeUpdate(BaseModel):
    # All optional
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    # ...

class FilamentTypeResponse(FilamentTypeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    material_type_code: str
    material_type_name: str
    model_config = ConfigDict(from_attributes=True)
```

### Anti-Patterns to Avoid

- **Using ORM models in Alembic migrations:** Migrations import Base metadata but should not import or use ORM model classes for data operations. If the model changes in the future, the old migration breaks. Use `sa.text()` raw SQL only.
- **Using `get_db` instead of `get_tenant_db` on new endpoints:** The existing `spools.py` uses `get_db` (bypassing RLS). All new FilamentType endpoints MUST use `get_tenant_db` / `TenantDB`. This is both a correctness issue and a security issue.
- **Two-step NULL→NOT NULL without server_default:** Adding a `NOT NULL` column without a `server_default` fails on a populated table. Always add nullable first, backfill, then `alter_column(..., nullable=False)`. For boolean columns with server_default, the single-step approach works.
- **Dropping FK-referenced columns before dropping FK constraints:** Drop the FK constraint before dropping `material_type_id` from spools.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation in migration | Custom UUID function | `gen_random_uuid()` (PostgreSQL built-in) | Already used throughout codebase |
| RLS policy SQL | Custom template | Exact string from `8c3c671816d9_create_rls_policies.py` | Policy names must match existing pattern (tenant_isolation_*) for downgrade to work |
| Deduplication in Python | Python-side groupby | `DISTINCT ON (tenant_id, brand, color, material_type_id) ... ORDER BY created_at ASC` | Single SQL statement, runs in the transaction, no Python memory required |
| Schema validation | Manual field checks | Pydantic Field validators with min_length, ge, le | Already validated by Pydantic; FastAPI returns 422 automatically |

**Key insight:** The deduplication and backfill are most safely expressed as two SQL statements — one INSERT (creating FilamentType records from DISTINCT ON) and one UPDATE (setting filament_type_id on each Spool). Doing this in Python would require loading all spools into memory and is unnecessary.

---

## Common Pitfalls

### Pitfall 1: Multiple Alembic Heads

**What goes wrong:** The repository currently has **5 active migration heads**: `a0b1c2d3e4f5`, `h2i3j4k5l6m7`, `s6t7u8v9w0x1`, `y2z3a4b5c6d7`, `k2l3m4n5o6p7`. Running `alembic upgrade head` when there are multiple heads fails.

**Why it happens:** The existing `j1k2l3m4n5o6_merge_heads.py` merged some branches but not all. New migrations added since then created additional divergence.

**How to avoid:** The new migration must declare a `down_revision` tuple that references ALL current heads. Alternatively, create a merge migration first, then chain the new migration off it.

```python
# Option A: merge migration as down_revision
down_revision: Union[str, Sequence[str], None] = (
    "a0b1c2d3e4f5",
    "h2i3j4k5l6m7",
    "s6t7u8v9w0x1",
    "y2z3a4b5c6d7",
    "k2l3m4n5o6p7",
)
```

**Warning signs:** `alembic heads` returns more than one revision ID.

### Pitfall 2: Alembic Migrations Run as Superuser — RLS Bypassed

**What goes wrong:** Migrations run as the PostgreSQL superuser (or the table owner), which bypasses RLS. This means all data operations in `upgrade()` see all rows across all tenants — which is correct for a migration — but you must NOT accidentally rely on `app.current_tenant_id` being set.

**Why it happens:** RLS policies use `current_setting('app.current_tenant_id', true)` but that variable is not set during migrations.

**How to avoid:** Write all migration SQL against the full table without a tenant filter. The deduplication query groups BY `(tenant_id, brand, color, material_type_id)` — this naturally scopes per-tenant without needing the session variable.

**Warning signs:** Unexpectedly small row counts in migration SQL during testing.

### Pitfall 3: `spools_remaining` and `purchased_quantity` Are NOT NULL with Server Default

**What goes wrong:** These columns have `nullable=False` and `server_default`. The downgrade path needs to add them back — but since they no longer have meaningful values, they should be added back as `nullable=True` or with a server_default. The downgrade adds them back NULL-filled per D-08.

**Why it happens:** Can't add a NOT NULL column to a populated table without a default.

**How to avoid:** In `downgrade()`, add both columns back as `nullable=True` (no server_default needed since the purpose is data recovery, not active use).

### Pitfall 4: Export/Import Endpoints Use Stale Field Names

**What goes wrong:** The existing `/export` and `/import` endpoints in `spools.py` reference field names that don't exist on the Spool model: `.diameter_mm`, `.cost_per_kg`, `.location`, `.current_weight_g`, `.initial_weight_g`. These endpoints appear to be stale code from an earlier model design.

**Why it happens:** The spool model was refined after these endpoints were written but the endpoints weren't updated.

**How to avoid:** These endpoints will break after migration removes `brand` etc. from Spool. The plan should include updating or removing the export/import endpoints. If kept, they need to be rewritten to access type-level fields via `spool.filament_type.brand` etc.

**Warning signs:** Running the export endpoint raises `AttributeError: 'Spool' object has no attribute 'diameter_mm'`.

### Pitfall 5: FK Constraint on `production_run_materials.spool_id`

**What goes wrong:** `production_run_materials` has `ForeignKey("spools.id", ondelete="RESTRICT")`. This does NOT block the schema migration (we are not changing `spools.id`), but it means that if someone tried to delete a Spool referenced in a production run, it would fail. No action needed for this migration.

**Why it matters to document:** If the downgrade drops the spools table, this FK would need to be dropped first. The downgrade does NOT drop spools — it only restructures columns — so this is not an issue.

### Pitfall 6: alembic env.py Must Import FilamentType

**What goes wrong:** `backend/alembic/env.py` explicitly imports models for autogenerate support. If `FilamentType` is not added to `env.py`, autogenerate will not detect the new table and future autogenerated migrations will be incorrect.

**How to avoid:** Add `from app.models.filament_type import FilamentType  # noqa: F401` to `env.py`.

### Pitfall 7: `spools.py` API Uses `get_db` Not `get_tenant_db`

**What goes wrong:** All existing Spool endpoints use `Depends(get_db)` instead of `TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]`. This means RLS is **not enforced** on the existing spool endpoints even though `ALTER TABLE spools ENABLE ROW LEVEL SECURITY` was run in the RLS migration.

**Why it matters for this phase:** New FilamentType endpoints must use `TenantDB` from day one. Whether to fix the existing spool endpoints in this phase or defer is a planning decision, but the research must flag it.

**How to avoid:** Import `TenantDB` from `app.auth.dependencies` and use it as the `db` parameter type annotation on new endpoints.

---

## Code Examples

### Verified: `DISTINCT ON` for Deduplication (PostgreSQL-specific)

```sql
-- Source: PostgreSQL documentation — DISTINCT ON is a PostgreSQL extension
-- Selects one row per (tenant_id, brand, color, material_type_id) group,
-- choosing the oldest spool (smallest created_at) to supply shared field values.
SELECT DISTINCT ON (tenant_id, brand, color, material_type_id)
    gen_random_uuid() AS id,
    tenant_id,
    material_type_id,
    brand,
    color,
    color_hex,
    finish,
    COALESCE(diameter, 1.75) AS diameter,
    density,
    extruder_temp,
    bed_temp,
    translucent,
    glow,
    pattern,
    spool_type,
    notes,
    false AS has_sample,
    now() AS created_at,
    now() AS updated_at
FROM spools
ORDER BY tenant_id, brand, color, material_type_id, created_at ASC
```

**Caution:** `DISTINCT ON` fields MUST appear at the front of `ORDER BY`. The `ORDER BY` clause establishes which row is "chosen" per group.

### Verified: Two-Step NOT NULL Column Addition

```python
# Source: Alembic documentation pattern — industry standard for populated tables
# Step 1: Add nullable
op.add_column("spools", sa.Column("filament_type_id", sa.UUID(), nullable=True))

# Step 2: Populate
conn = op.get_bind()
conn.execute(sa.text("""
    UPDATE spools s
    SET filament_type_id = ft.id
    FROM filament_types ft
    WHERE s.tenant_id = ft.tenant_id
      AND s.brand = ft.brand
      AND s.color = ft.color
      AND s.material_type_id = ft.material_type_id
"""))

# Step 3: Make NOT NULL
op.alter_column("spools", "filament_type_id", nullable=False)

# Step 4: Add FK
op.create_foreign_key(
    "fk_spools_filament_type_id",
    "spools", "filament_types",
    ["filament_type_id"], ["id"],
    ondelete="RESTRICT",  # Don't allow deleting a FilamentType that has spools
)
```

### Verified: Test Pattern for FilamentType API

```python
# Source: backend/tests/integration/test_spools_api.py (existing pattern)
class TestFilamentTypesEndpoints:
    @pytest.mark.asyncio
    async def test_create_filament_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_material_type: MaterialType,
    ):
        response = await client.post(
            "/api/v1/filament-types",
            headers=auth_headers,
            json={
                "material_type_id": str(test_material_type.id),
                "brand": "Bambu Lab",
                "color": "Jade White",
                "diameter": 1.75,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["brand"] == "Bambu Lab"
        assert data["has_sample"] is False
```

### Verified: conftest.py Fixture Pattern for FilamentType

```python
# Source: backend/tests/conftest.py (existing test_spool fixture as template)
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
    )
    db_session.add(ft)
    await db_session.commit()
    await db_session.refresh(ft)
    return ft
```

---

## Existing Codebase Inventory

### Current Spool Model Fields

**Moving to FilamentType** (per D-01):
| Field | Type | Notes |
|-------|------|-------|
| `brand` | `String(100)`, NOT NULL | Deduplication key field |
| `color` | `String(50)`, NOT NULL | Deduplication key field |
| `color_hex` | `String(9)`, nullable | |
| `finish` | `String(50)`, nullable | |
| `diameter` | `Numeric(4,2)`, NOT NULL, default 1.75 | NOT in deduplication key |
| `density` | `Numeric(5,3)`, nullable | |
| `extruder_temp` | `Integer`, nullable | |
| `bed_temp` | `Integer`, nullable | |
| `translucent` | `bool`, NOT NULL, default False | |
| `glow` | `bool`, NOT NULL, default False | |
| `pattern` | `String(50)`, nullable | |
| `spool_type` | `String(50)`, nullable | |
| `notes` | `Text`, nullable | |
| `material_type_id` | `UUID`, FK → `material_types.id` | Deduplication key field |

**Staying on Spool** (per D-02):
| Field | Type | Notes |
|-------|------|-------|
| `spool_id` | `String(50)`, NOT NULL | User-friendly ID |
| `initial_weight` | `Numeric(10,2)`, NOT NULL | |
| `current_weight` | `Numeric(10,2)`, NOT NULL | |
| `empty_spool_weight` | `Numeric(10,2)`, nullable | |
| `purchase_date` | `DateTime`, nullable | |
| `purchase_price` | `Numeric(10,2)`, nullable | |
| `supplier` | `String(100)`, nullable | |
| `storage_location` | `String(100)`, nullable | |
| `qr_code_id` | `String(100)`, nullable, unique | |
| `is_active` | `bool`, NOT NULL, default True | |

**Being removed** (per D-07):
| Field | Type | Notes |
|-------|------|-------|
| `purchased_quantity` | `Integer`, NOT NULL, default 1 | |
| `spools_remaining` | `Integer`, NOT NULL, default 1 | |

**Being added** (per D-02, D-05):
| Field | Type | Notes |
|-------|------|-------|
| `filament_type_id` | `UUID`, FK → `filament_types.id`, NOT NULL | New FK |
| `is_labeled` | `bool`, NOT NULL, default False | New field |

### Existing FK Dependencies on `spools`

| Table | Column | On Delete | Impact on Migration |
|-------|--------|-----------|---------------------|
| `production_run_materials` | `spool_id` | RESTRICT | No impact — `spools.id` is not changing |
| `ams_slot_mappings` | `spool_id` | SET NULL | No impact — `spools.id` is not changing |

### Existing API Endpoints on `/api/v1/spools`

| Method | Path | Status After Migration |
|--------|------|----------------------|
| POST | `/` | Must be updated — `brand`, `color` etc. replaced by `filament_type_id` |
| GET | `/` | Must be updated — response now includes nested `filament_type` |
| GET | `/material-types` | No change needed |
| POST | `/material-types` | No change needed |
| GET | `/{spool_id}` | Must be updated — response includes `filament_type` |
| PUT | `/{spool_id}` | Must be updated — schema drops type fields |
| DELETE | `/{spool_id}` | No change needed |
| POST | `/{spool_id}/duplicate` | Must be updated — duplicates filament_type_id not inline fields |
| GET | `/export` | Must be updated OR removed — uses stale field names |
| POST | `/import` | Must be updated OR removed — uses stale field names |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `Column()` style | SQLAlchemy 2.0 `Mapped[type]` with `mapped_column()` | Already current in this codebase | Must use new style; old style works but produces deprecation warnings |
| Alembic `autogenerate` for all migrations | Autogenerate schema DDL, hand-write data backfill | Already current in this codebase | Data operations must be raw SQL in `op.get_bind().execute(sa.text(...))` |

**Deprecated/outdated:**
- `Column()` without type annotation: works but all new models use `Mapped[type] = mapped_column(...)` style per existing codebase convention.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 5 current migration heads (`a0b1c2d3e4f5`, `h2i3j4k5l6m7`, `s6t7u8v9w0x1`, `y2z3a4b5c6d7`, `k2l3m4n5o6p7`) are all applied to production. If some are stale/unapplied branches, the down_revision tuple would be wrong. | Common Pitfalls — Multiple Heads | Migration chain is incorrect; alembic upgrade would fail or create inconsistency |
| A2 | `notes` moves to FilamentType (D-01 lists it). However, notes could be per-spool. Per D-01 it moves to FilamentType. | Standard Stack / field split | If notes are intended as per-spool, the model is wrong |
| A3 | The export/import endpoint bugs (`diameter_mm`, `location`, etc.) are pre-existing and not regressions from this migration. | Common Pitfalls — Export | If these endpoints currently work (perhaps via a different code path), removing them could break integrations |

---

## Open Questions

1. **Migration head strategy**
   - What we know: There are 5 active Alembic heads
   - What's unclear: Are all 5 branches deployed to production, or were some experimental branches never merged?
   - Recommendation: Run `alembic heads` against the actual database to see which revisions are applied. If all 5 are applied, the new migration must merge all 5 in `down_revision`. If some are not applied, a merge migration should be created first.

2. **`get_db` vs `get_tenant_db` on existing spool endpoints**
   - What we know: All existing spool endpoints use `get_db` (no RLS context)
   - What's unclear: Was this intentional (RLS disabled in dev) or a bug?
   - Recommendation: Switch all spool endpoints to `get_tenant_db` / `TenantDB` in this phase as part of the endpoint updates. The existing `test_spools_api.py` tests use dependency overrides so they will continue to work regardless.

3. **Export/import endpoint fate**
   - What we know: These endpoints use stale field names and will break after migration
   - What's unclear: Are they actively used?
   - Recommendation: Remove both endpoints in this phase. If needed, they can be re-implemented in a future phase against the two-tier model.

---

## Environment Availability

Step 2.6: Confirmed no new external dependencies. This phase uses only tools already present in the project (Poetry, PostgreSQL, Python 3.12). No new CLI tools, services, or runtimes are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && poetry run pytest tests/unit/test_filament_type_schemas.py -x` |
| Full suite command | `cd backend && poetry run pytest --cov=app --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | FilamentType model has all required fields | unit | `pytest tests/unit/test_filament_type_schemas.py -x` | Wave 0 |
| DATA-01 | FilamentType CRUD endpoints respond correctly | integration | `pytest tests/integration/test_filament_types_api.py -x` | Wave 0 |
| DATA-02 | Spool model no longer has brand/color/etc.; has filament_type_id | unit | `pytest tests/unit/test_spool_schemas.py -x` | Exists — needs update |
| DATA-02 | Spool endpoints accept filament_type_id in request body | integration | `pytest tests/integration/test_spools_api.py -x` | Exists — needs update |
| DATA-03 | Migration runs without error on seeded test data | integration | Manual / migration test | Wave 0 |
| DATA-04 | FilamentType.has_sample defaults False, toggleable | unit | `pytest tests/unit/test_filament_type_schemas.py::TestFilamentTypeBase::test_has_sample_defaults_false -x` | Wave 0 |
| DATA-05 | Spool.is_labeled defaults False, toggleable | unit | `pytest tests/unit/test_spool_schemas.py::TestSpoolBase::test_is_labeled_defaults_false -x` | Wave 0 (update existing) |

### Sampling Rate

- **Per task commit:** `cd backend && poetry run pytest tests/unit/ -x -q`
- **Per wave merge:** `cd backend && poetry run pytest --cov=app --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_filament_type_schemas.py` — covers DATA-01, DATA-04
- [ ] `tests/integration/test_filament_types_api.py` — covers DATA-01 (CRUD, auth 401, validation 422, not found 404)
- [ ] `tests/conftest.py` — add `test_filament_type` fixture
- [ ] `tests/unit/test_spool_schemas.py` — update existing to test is_labeled (DATA-05) and removal of old fields

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing `CurrentUser` / `CurrentTenant` dependency pattern |
| V3 Session Management | no | No session state introduced |
| V4 Access Control | yes | `tenant_id` on all records + PostgreSQL RLS |
| V5 Input Validation | yes | Pydantic Field validators (min_length, ge, le) |
| V6 Cryptography | no | No new cryptographic operations |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-tenant data access | Information Disclosure | tenant_id FK + RLS policies on `filament_types` (must be added inline in migration) |
| Missing tenant scope on new endpoints | Elevation of Privilege | Use `TenantDB` dependency (not `get_db`) on all FilamentType endpoints |
| NULL brand/color producing unexpected FilamentType merges | Tampering | Fail-fast check in migration upgrade() before any table creation |

---

## Sources

### Primary (HIGH confidence)
- `backend/app/models/spool.py` — Current Spool model, all fields verified
- `backend/app/models/material.py` — MaterialType model, no tenant_id (global table confirmed)
- `backend/app/models/base.py` — UUIDMixin + TimestampMixin confirmed
- `backend/alembic/env.py` — Migration runner setup confirmed
- `backend/alembic/versions/8c3c671816d9_create_rls_policies.py` — RLS policy pattern confirmed
- `backend/alembic/versions/cffc14267961_enable_rls_on_tenant_tables.py` — RLS enablement pattern confirmed
- `backend/alembic/versions/b2c3d4e5f6g7_add_customers.py` — create_table migration pattern confirmed
- `backend/app/auth/dependencies.py` — `get_tenant_db` / `TenantDB` definition confirmed
- `backend/tests/conftest.py` — All test fixtures confirmed
- `backend/app/api/v1/spools.py` — All existing endpoints confirmed; `get_db` vs `get_tenant_db` issue confirmed

### Secondary (MEDIUM confidence)
- PostgreSQL `DISTINCT ON` syntax — standard PostgreSQL extension, confirmed applicable for deduplication pattern
- Two-step NOT NULL column addition — industry standard Alembic pattern for populated tables

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in codebase
- Architecture: HIGH — exact patterns verified from existing migrations and models
- Pitfalls: HIGH — all pitfalls discovered from direct codebase inspection, not assumptions

**Research date:** 2026-05-19
**Valid until:** 2026-06-19 (stable stack, 30-day window)
