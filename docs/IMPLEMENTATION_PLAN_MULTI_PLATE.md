# Implementation Plan: Multi-Plate Production Runs

**Feature**: Multi-plate production runs with printer-specific configurations
**Date Started**: 2025-12-15
**Target**: Phase 1 - Core functionality for real production workflow
**Status**: 🟡 In Progress - Session 1 complete (SQLAlchemy models + unit tests), Session 2 pending (Pydantic schemas + unit tests)

---

## Table of Contents

1. [Overview](#overview)
2. [Current State](#current-state)
3. [Architecture Decisions](#architecture-decisions)
4. [Implementation Phases](#implementation-phases)
5. [Session Checkpoints](#session-checkpoints)
6. [Testing Strategy](#testing-strategy)
7. [Rollback Plan](#rollback-plan)

---

## Overview

### Problem Statement

Current production run system doesn't match real-world workflow:
- Products require multiple print plates (e.g., Bearded Dragon Terrarium = 37 plates)
- Different printers have different capabilities (A1 Mini vs A1 vs P2S)
- No way to track progress across multi-plate runs
- Tedious to create 37 separate runs for one product batch

### Solution

Implement multi-plate production runs:
1. **Printers table** - Track available printers with capabilities
2. **Printer configs per model** - Model prints differently on different printers
3. **Multi-plate runs** - One production run contains many plates
4. **Plate progress tracking** - Mark plates complete, auto-detect run completion
5. **Product-based production** - Create run for "5× Terrarium Sets" → system calculates plates

### User Workflow (Target)

```
User: "Create production run for 5× Small Terrarium Sets on A1 Mini"

System calculates:
- Dragon Bodies: 2 plates (3 per plate × 2 = 6, need 5)
- Dragon Tongues: 1 plate (6 per plate, need 5)
- Terrarium walls 1-6: 6 plates each × 5 sets = 30 plates
- Rock formation: 5 plates
- Flowers: 2 plates (4 per plate × 2, need 5)
- Pink flowers: 1 plate
- Babies & eggs: 1 plate
Total: 37 plates

Creates run with all 37 plates
User prints plates, marks complete as they finish
When all 37 done → system prompts to increment Product inventory
```

---

## Current State

### ✅ Completed (2025-12-15)

1. **Schema Design**
   - File: `docs/SCHEMA_DESIGN_MULTI_PLATE.md`
   - Comprehensive design with examples and rationale

2. **Database Migrations**
   - Migration 1: `43cc1df327c1_add_printers_table.py` ✅ Applied
   - Migration 2: `c7503ada4f0b_add_model_printer_configs_table.py` ✅ Applied
   - Migration 3: `e8b435cc2b4a_update_production_runs_printer_product.py` ✅ Applied
   - Migration 4: `ede22cd894be_add_production_run_plates_table.py` ✅ Applied

3. **Schema Verification**
   - All migrations successfully applied to database
   - Tables created: `printers`, `model_printer_configs`, `production_run_plates`
   - `production_runs` updated with: `printer_id`, `product_id`, `total_plates`, `completed_plates`

4. **SQLAlchemy Models (Session 1)** ✅
   - Created `backend/app/models/printer.py` - Printer model with all fields and relationships
   - Created `backend/app/models/model_printer_config.py` - ModelPrinterConfig with computed properties
   - Created `backend/app/models/production_run_plate.py` - ProductionRunPlate with status tracking
   - Updated `backend/app/models/production_run.py` - Added printer_id, product_id, total_plates, completed_plates, plates relationship, computed properties
   - Updated `backend/app/models/model.py` - Added printer_configs and production_run_plates relationships
   - Updated `backend/app/models/product.py` - Added production_runs relationship
   - Updated `backend/app/models/tenant.py` - Added printers relationship
   - Updated `backend/app/models/__init__.py` - Exports for all new models
   - All imports verified, all relationships tested, computed properties working

5. **Unit Tests (Session 1)** ✅
   - Created `tests/unit/test_printer_model.py` - 13 tests for Printer model (creation, constraints, relationships, capabilities)
   - Created `tests/unit/test_model_printer_config_model.py` - 18 tests for ModelPrinterConfig (creation, constraints, relationships, computed properties)
   - Created `tests/unit/test_production_run_plate_model.py` - 24 tests for ProductionRunPlate (creation, constraints, status transitions, computed properties)
   - Created `tests/unit/test_production_run_multi_plate.py` - 21 tests for ProductionRun multi-plate features (fields, relationships, computed properties, legacy vs multi-plate mode)
   - Added test fixtures to `tests/conftest.py` (test_printer, test_model_printer_config, test_model_with_prints_per_plate)
   - Total: 76 new tests, all passing
   - Full test suite: 221 passed, 7 skipped

### 🔄 In Progress

None (awaiting next session)

### ⏳ Pending

- Session 2: Pydantic Schemas + Unit Tests
- Session 3: Service Layer + Unit Tests
- Session 4: Printer & Config APIs + Integration Tests
- Session 5: Production Run Plate APIs + Integration Tests
- Session 6-9: Frontend Integration + Component Tests
- Session 10: E2E Testing & Polish

---

## Architecture Decisions

### Decision 1: UUIDs without server_default

**Decision**: Use `sa.UUID()` without `server_default=uuid_generate_v4()`
**Rationale**: Avoid dependency on `uuid-ossp` PostgreSQL extension. SQLAlchemy/Python generates UUIDs client-side.
**Impact**: Models must use `default=uuid.uuid4` in Python code
**Files affected**: All new SQLAlchemy models

### Decision 2: Plate-level vs Run-level Material Tracking

**Decision**: Keep material tracking at run level (`production_run_materials`), not per-plate
**Rationale**: Simplicity for Phase 1. User typically uses same spools across all plates.
**Future**: Add per-plate materials if needed in Phase 2
**Trade-off**: Less granular tracking, but 80% use case covered

### Decision 3: Backward Compatibility

**Decision**: Keep existing `production_run_items` system intact
**Rationale**: Old runs still work, no migration of historical data needed
**Implementation**: `production_run_plates` is optional, system detects which to use
**Pattern**: `if run.total_plates > 0: use plate-based else: use item-based`

### Decision 4: Printer Config Fallback

**Decision**: If no `model_printer_config` exists, fall back to `Model.prints_per_plate` and other defaults
**Rationale**: Not all models configured for all printers upfront
**Implementation**: Service layer tries to fetch config, uses model defaults if missing
**User experience**: System still works, suggests creating config for better accuracy

### Decision 5: Status Flow

**Production Run Statuses**:
- `pending` → `in_progress` → `completed` / `failed` / `cancelled`

**Plate Statuses**:
- `pending` → `printing` → `complete` / `failed` / `cancelled`

**Auto-completion**: When `completed_plates == total_plates`, run status → `ready_for_assembly`

---

## Implementation Phases

## Phase 1: Backend Foundation (Sessions 1-3)

### Session 1: SQLAlchemy Models + Unit Tests (2-3 hours) ✅ COMPLETE

**Goal**: Create Python models for new database tables with comprehensive unit tests

**Approach**: Test-driven development - create models, then write comprehensive unit tests to verify all functionality before moving to next session.

**Tasks**:

1. **Create Printer model** (`backend/app/models/printer.py`)
   ```python
   # Reference pattern: backend/app/models/model.py
   # Must include:
   # - UUID primary key with default=uuid.uuid4
   # - tenant_id FK with CASCADE delete
   # - All fields from migration
   # - Relationships: model_printer_configs, production_runs, production_run_plates
   # - __repr__ method
   # - Add to __init__.py imports
   ```

2. **Create ModelPrinterConfig model** (`backend/app/models/model_printer_config.py`)
   ```python
   # Reference pattern: backend/app/models/model_material.py (join table)
   # Must include:
   # - Relationships to Model and Printer
   # - JSONB field for slicer_settings
   # - Unique constraint on (model_id, printer_id)
   # - Add to __init__.py imports
   ```

3. **Create ProductionRunPlate model** (`backend/app/models/production_run_plate.py`)
   ```python
   # Reference pattern: backend/app/models/production_run.py
   # Must include:
   # - Status enum constraint
   # - Relationships to ProductionRun, Model, Printer
   # - Computed property for progress percentage
   # - Add to __init__.py imports
   ```

4. **Update ProductionRun model** (`backend/app/models/production_run.py`)
   ```python
   # Add fields:
   # - printer_id: Mapped[Optional[uuid.UUID]]
   # - product_id: Mapped[Optional[uuid.UUID]]
   # - total_plates: Mapped[int]
   # - completed_plates: Mapped[int]
   #
   # Add relationships:
   # - printer: Mapped[Optional["Printer"]]
   # - product: Mapped[Optional["Product"]]
   # - plates: Mapped[list["ProductionRunPlate"]]
   #
   # Add computed property:
   # @property
   # def is_multi_plate(self) -> bool:
   #     return self.total_plates > 0
   ```

5. **Update Model model** (`backend/app/models/model.py`)
   ```python
   # Add relationship:
   # printer_configs: Mapped[list["ModelPrinterConfig"]]
   ```

6. **Test imports**
   ```bash
   cd backend
   poetry run python -c "from app.models import Printer, ModelPrinterConfig, ProductionRunPlate; print('✓ All models import successfully')"
   ```

7. **Write comprehensive unit tests**
   ```bash
   # Create test files covering:
   # - Model creation (basic and all fields)
   # - Default values
   # - Computed properties
   # - Constraints (unique, check, FK)
   # - Relationships (bidirectional)
   # - Cascade deletes
   # - Legacy vs multi-plate mode detection

   poetry run pytest tests/unit/test_printer_model.py -v
   poetry run pytest tests/unit/test_model_printer_config_model.py -v
   poetry run pytest tests/unit/test_production_run_plate_model.py -v
   poetry run pytest tests/unit/test_production_run_multi_plate.py -v
   ```

8. **Verify full test suite passes**
   ```bash
   poetry run pytest tests/ -v
   # All tests must pass before session is complete
   ```

**Acceptance Criteria**:
- [x] All 3 new models created
- [x] All relationships defined bidirectionally
- [x] Models import without errors
- [x] Models match migration schemas exactly
- [x] Docstrings explain purpose and relationships
- [x] Unit tests for all new models (>95% coverage of new code)
- [x] Unit tests for updated models (multi-plate features)
- [x] All tests pass (no regressions)

**Files to Create**:
- `backend/app/models/printer.py`
- `backend/app/models/model_printer_config.py`
- `backend/app/models/production_run_plate.py`
- `backend/tests/unit/test_printer_model.py`
- `backend/tests/unit/test_model_printer_config_model.py`
- `backend/tests/unit/test_production_run_plate_model.py`
- `backend/tests/unit/test_production_run_multi_plate.py`

**Files to Modify**:
- `backend/app/models/production_run.py`
- `backend/app/models/model.py`
- `backend/app/models/__init__.py`
- `backend/tests/conftest.py` (add test fixtures)

**Common Pitfalls**:
- Forgetting `lazy="selectin"` on relationships (causes N+1 queries)
- Missing `__table_args__` with comments
- Incorrect CASCADE settings on foreign keys
- Not adding new models to `__init__.py`

---

### Session 2: Pydantic Schemas + Unit Tests (2-3 hours)

**Goal**: Create request/response schemas for API endpoints with comprehensive unit tests

**Approach**: Create schemas, then write unit tests verifying serialization, validation, and computed fields before moving to next session.

**Tasks**:

1. **Create Printer schemas** (`backend/app/schemas/printer.py`)
   ```python
   # Reference pattern: backend/app/schemas/model.py
   # Schemas needed:
   # - PrinterBase (common fields)
   # - PrinterCreate (for POST)
   # - PrinterUpdate (for PATCH, all optional)
   # - PrinterResponse (for GET, includes id, timestamps)
   # - PrinterListResponse (pagination wrapper)
   # - PrinterSummary (lightweight for dropdowns)
   ```

2. **Create ModelPrinterConfig schemas** (`backend/app/schemas/model_printer_config.py`)
   ```python
   # Schemas needed:
   # - ModelPrinterConfigBase
   # - ModelPrinterConfigCreate
   # - ModelPrinterConfigUpdate
   # - ModelPrinterConfigResponse (includes nested ModelSummary, PrinterSummary)
   # - ModelPrinterConfigListResponse
   ```

3. **Create ProductionRunPlate schemas** (`backend/app/schemas/production_run_plate.py`)
   ```python
   # Schemas needed:
   # - ProductionRunPlateBase
   # - ProductionRunPlateCreate
   # - ProductionRunPlateUpdate (for marking complete)
   # - ProductionRunPlateResponse (includes nested ModelSummary, PrinterSummary)
   # - Computed fields: progress_percentage, is_complete
   ```

4. **Update ProductionRun schemas** (`backend/app/schemas/production_run.py`)
   ```python
   # Modify ProductionRunCreate:
   # - Add optional printer_id: Optional[UUID]
   # - Add optional product_id: Optional[UUID]
   # - Add optional plates: list[ProductionRunPlateCreate]
   #
   # Modify ProductionRunResponse:
   # - Add printer_id, product_id, total_plates, completed_plates
   # - Add computed: plates_progress_percentage, is_multi_plate
   #
   # Modify ProductionRunDetailResponse:
   # - Add plates: list[ProductionRunPlateResponse]
   # - Show plates if is_multi_plate, else show items
   ```

5. **Add printer fields to Model schemas** (`backend/app/schemas/model.py`)
   ```python
   # Modify ModelResponse:
   # - Add optional printer_configs: list[ModelPrinterConfigResponse]
   ```

6. **Write comprehensive unit tests**
   ```bash
   # Create test files covering:
   # - Schema instantiation and validation
   # - Field validators (enums, constraints)
   # - Serialization from ORM models (from_attributes)
   # - Nested relationship serialization
   # - Computed fields
   # - Invalid data handling (422 errors)

   poetry run pytest tests/unit/test_printer_schemas.py -v
   poetry run pytest tests/unit/test_model_printer_config_schemas.py -v
   poetry run pytest tests/unit/test_production_run_plate_schemas.py -v
   ```

7. **Verify full test suite passes**
   ```bash
   poetry run pytest tests/ -v
   # All tests must pass before session is complete
   ```

**Acceptance Criteria**:
- [ ] All schemas validate correctly
- [ ] Nested relationships serialize properly
- [ ] Computed fields return expected values
- [ ] ConfigDict(from_attributes=True) on all response schemas
- [ ] Field validators for enums and constraints
- [ ] Unit tests for all new schemas
- [ ] All tests pass (no regressions)

**Files to Create**:
- `backend/app/schemas/printer.py`
- `backend/app/schemas/model_printer_config.py`
- `backend/app/schemas/production_run_plate.py`
- `backend/tests/unit/test_printer_schemas.py`
- `backend/tests/unit/test_model_printer_config_schemas.py`
- `backend/tests/unit/test_production_run_plate_schemas.py`

**Files to Modify**:
- `backend/app/schemas/production_run.py`
- `backend/app/schemas/model.py`
- `backend/app/schemas/__init__.py`

**Common Pitfalls**:
- Forgetting `ConfigDict(from_attributes=True)`
- Circular import issues (use `TYPE_CHECKING` and forward refs)
- Not validating Decimal fields properly
- Missing `@computed_field` decorator on properties

---

### Session 3: Service Layer + Unit Tests (3-4 hours)

**Goal**: Implement business logic for printers and printer configs with comprehensive unit tests

**Approach**: Create services, then write unit tests for all methods including edge cases (empty results, invalid IDs, fallback logic) before moving to next session.

**Tasks**:

1. **Create PrinterService** (`backend/app/services/printer.py`)
   ```python
   # Reference pattern: backend/app/services/model.py
   # Methods needed:
   # - async def list_printers(skip, limit, is_active_only) -> list[Printer]
   # - async def get_printer(printer_id) -> Printer
   # - async def create_printer(data: PrinterCreate) -> Printer
   # - async def update_printer(printer_id, data: PrinterUpdate) -> Printer
   # - async def delete_printer(printer_id) -> None (check for dependencies first)
   # - async def get_by_name(name) -> Optional[Printer] (for unique check)
   ```

2. **Create ModelPrinterConfigService** (`backend/app/services/model_printer_config.py`)
   ```python
   # Methods needed:
   # - async def get_config(model_id, printer_id) -> Optional[ModelPrinterConfig]
   # - async def get_config_or_defaults(model_id, printer_id) -> dict
   #   # Falls back to Model.prints_per_plate, etc. if no config
   # - async def list_configs_for_model(model_id) -> list[ModelPrinterConfig]
   # - async def list_configs_for_printer(printer_id) -> list[ModelPrinterConfig]
   # - async def create_config(data: ModelPrinterConfigCreate) -> ModelPrinterConfig
   # - async def update_config(config_id, data: ModelPrinterConfigUpdate) -> ModelPrinterConfig
   # - async def delete_config(config_id) -> None
   # - async def bulk_create_from_slicer_profile(file_data) -> list[ModelPrinterConfig]
   #   # Future: parse 3MF/profile files
   ```

3. **Update ProductionRunService** (`backend/app/services/production_run.py`)
   ```python
   # Add new method:
   # async def create_multi_plate_run(
   #     product_id: UUID,
   #     printer_id: UUID,
   #     quantity: int,
   #     **kwargs
   # ) -> ProductionRun:
   #     """
   #     Create production run for N units of a product.
   #     Calculates all required plates based on:
   #     - Product.product_models (what models are in product)
   #     - ModelPrinterConfig (prints per plate for each model on this printer)
   #     - Quantity requested
   #
   #     Algorithm:
   #     1. Get all models in product
   #     2. For each model:
   #        a. Get printer config (or use defaults)
   #        b. Calculate: ceil(quantity * model_quantity / prints_per_plate)
   #        c. Create ProductionRunPlate entries
   #     3. Set total_plates on run
   #     4. Calculate total materials needed
   #     5. Return run
   #     """
   #
   # Modify existing create_production_run:
   # - Accept optional plates: list[ProductionRunPlateCreate]
   # - If plates provided, create them
   # - Set total_plates = len(plates)
   #
   # Add new method:
   # async def mark_plate_complete(
   #     plate_id: UUID,
   #     actual_time: Optional[int],
   #     actual_weight: Optional[Decimal],
   #     successful_prints: int,
   #     failed_prints: int
   # ) -> ProductionRunPlate:
   #     """
   #     Mark plate complete and update run progress.
   #     Auto-detect if run is complete (all plates done).
   #     """
   #     # Update plate status = 'complete'
   #     # Increment run.completed_plates
   #     # Check if completed_plates == total_plates
   #     # If yes: run.status = 'ready_for_assembly'
   #     # Return updated plate
   ```

4. **Add calculation helper** (`backend/app/services/production_run_calculator.py`)
   ```python
   # Utility functions:
   # - def calculate_plates_needed(model_quantity: int, prints_per_plate: int) -> int
   # - def calculate_material_per_plate(model_materials, prints_per_plate) -> Decimal
   # - def estimate_total_print_time(plates: list[ProductionRunPlate]) -> int
   # - def check_material_availability(plates, spools) -> dict[str, bool]
   #   # Returns which materials have enough inventory
   ```

5. **Write comprehensive unit tests**
   ```bash
   # Create test files covering:
   # - CRUD operations (create, read, update, delete)
   # - Fallback logic (config → model defaults)
   # - Plate calculation math (edge cases: 0, 1, max)
   # - Status transitions and auto-completion
   # - Error handling (not found, duplicate, FK violation)
   # - Calculator functions

   poetry run pytest tests/unit/test_printer_service.py -v
   poetry run pytest tests/unit/test_model_printer_config_service.py -v
   poetry run pytest tests/unit/test_production_run_service_multi_plate.py -v
   poetry run pytest tests/unit/test_production_run_calculator.py -v
   ```

6. **Verify full test suite passes**
   ```bash
   poetry run pytest tests/ -v
   # All tests must pass before session is complete
   ```

**Acceptance Criteria**:
- [ ] PrinterService CRUD operations work
- [ ] ModelPrinterConfigService returns defaults if no config exists
- [ ] ProductionRunService.create_multi_plate_run calculates plates correctly
- [ ] mark_plate_complete updates run progress
- [ ] Auto-detection of run completion works
- [ ] Unit tests for all service methods
- [ ] Unit tests for calculator functions
- [ ] All tests pass (no regressions)

**Files to Create**:
- `backend/app/services/printer.py`
- `backend/app/services/model_printer_config.py`
- `backend/app/services/production_run_calculator.py`
- `backend/tests/unit/test_printer_service.py`
- `backend/tests/unit/test_model_printer_config_service.py`
- `backend/tests/unit/test_production_run_service_multi_plate.py`
- `backend/tests/unit/test_production_run_calculator.py`

**Files to Modify**:
- `backend/app/services/production_run.py`
- `backend/app/services/__init__.py`

**Common Pitfalls**:
- Not checking for FK dependencies before delete
- Forgetting to flush session before returning created objects
- Incorrect ceil() math for plate calculation
- Not handling edge case: quantity = 0
- Race conditions in mark_plate_complete (use SELECT FOR UPDATE)

---

## Phase 2: API Endpoints (Sessions 4-5)

### Session 4: Printer & Config APIs + Integration Tests (2-3 hours)

**Goal**: Create REST API endpoints for printers and configs with comprehensive integration tests

**Approach**: Create endpoints, then write integration tests verifying HTTP responses, status codes, validation errors, and tenant isolation before moving to next session.

**Tasks**:

1. **Create Printer endpoints** (`backend/app/api/v1/printers.py`)
   ```python
   # Reference pattern: backend/app/api/v1/models.py
   # Endpoints:
   # GET    /api/v1/printers          - List printers (with pagination, filters)
   # GET    /api/v1/printers/{id}     - Get single printer
   # POST   /api/v1/printers          - Create printer
   # PATCH  /api/v1/printers/{id}     - Update printer
   # DELETE /api/v1/printers/{id}     - Delete printer (check dependencies)
   #
   # Query params for list:
   # - skip, limit (pagination)
   # - is_active (filter)
   # - manufacturer (filter)
   ```

2. **Create ModelPrinterConfig endpoints** (`backend/app/api/v1/model_printer_configs.py`)
   ```python
   # Endpoints:
   # GET    /api/v1/models/{model_id}/printer-configs          - List configs for model
   # GET    /api/v1/printers/{printer_id}/model-configs        - List configs for printer
   # GET    /api/v1/models/{model_id}/printer-configs/{printer_id}  - Get specific config (or defaults)
   # POST   /api/v1/model-printer-configs                      - Create config
   # PATCH  /api/v1/model-printer-configs/{id}                 - Update config
   # DELETE /api/v1/model-printer-configs/{id}                 - Delete config
   ```

3. **Update main router** (`backend/app/main.py`)
   ```python
   # Add new routers:
   from app.api.v1 import printers, model_printer_configs

   app.include_router(printers.router, prefix="/api/v1", tags=["printers"])
   app.include_router(model_printer_configs.router, prefix="/api/v1", tags=["model-printer-configs"])
   ```

4. **Add OpenAPI tags** (`backend/app/main.py`)
   ```python
   # Add to tags_metadata:
   {
       "name": "printers",
       "description": "Manage 3D printers and their capabilities"
   },
   {
       "name": "model-printer-configs",
       "description": "Manage printer-specific model configurations"
   }
   ```

5. **Write comprehensive integration tests**
   ```bash
   # Create test files covering:
   # - All HTTP methods (GET, POST, PATCH, DELETE)
   # - Correct status codes (200, 201, 204, 400, 404, 409, 422)
   # - Pagination and filtering
   # - Tenant isolation (can't access other tenant's data)
   # - Validation errors (malformed data)
   # - Edge cases (empty list, invalid UUID, duplicate names)

   poetry run pytest tests/integration/test_printers_api.py -v
   poetry run pytest tests/integration/test_model_printer_configs_api.py -v
   ```

6. **Verify full test suite passes**
   ```bash
   poetry run pytest tests/ -v
   # All tests must pass before session is complete
   ```

**Acceptance Criteria**:
- [ ] All endpoints return correct status codes
- [ ] Pagination works
- [ ] Filters work
- [ ] Tenant isolation enforced (can't access other tenant's printers)
- [ ] Validation errors return 422 with details
- [ ] OpenAPI docs updated
- [ ] Integration tests for all endpoints
- [ ] All tests pass (no regressions)

**Files to Create**:
- `backend/app/api/v1/printers.py`
- `backend/app/api/v1/model_printer_configs.py`
- `backend/tests/integration/test_printers_api.py`
- `backend/tests/integration/test_model_printer_configs_api.py`

**Files to Modify**:
- `backend/app/main.py`

**Common Pitfalls**:
- Forgetting `Depends(get_current_tenant)` on all endpoints
- Not using `status_code=201` for POST endpoints
- Missing error handling for 404/409/422
- Not testing edge cases (empty list, invalid UUID, etc.)

---

### Session 5: Production Run Plate APIs + Integration Tests (2-3 hours)

**Goal**: Extend production run API for multi-plate support with comprehensive integration tests

**Approach**: Extend existing endpoints and add new ones, then write integration tests covering the full workflow (create run, mark plates complete, auto-completion) before moving to next session.

**Tasks**:

1. **Add plate management endpoints** (`backend/app/api/v1/production_runs.py`)
   ```python
   # New endpoints:
   # GET    /api/v1/production-runs/{run_id}/plates           - List plates for run
   # GET    /api/v1/production-runs/{run_id}/plates/{plate_id} - Get single plate
   # PATCH  /api/v1/production-runs/{run_id}/plates/{plate_id} - Update plate (mark complete)
   # POST   /api/v1/production-runs/calculate-plates          - Calculate plates for product
   #        Request: { product_id, printer_id, quantity }
   #        Response: { plates: [...], total_print_time, materials_needed }
   ```

2. **Extend create endpoint** (`backend/app/api/v1/production_runs.py`)
   ```python
   # Modify POST /api/v1/production-runs:
   # - Accept new fields: printer_id, product_id, plates[]
   # - If plates provided: use create_multi_plate_run service
   # - Else: use existing create_production_run service
   # - Return ProductionRunDetailResponse (includes plates if multi-plate)
   ```

3. **Add production defaults endpoint** (`backend/app/api/v1/models.py`)
   ```python
   # New endpoint:
   # GET /api/v1/models/{model_id}/production-defaults?printer_id={printer_id}
   # Returns:
   # {
   #   "prints_per_plate": 3,
   #   "print_time_minutes": 45,
   #   "material_weight_grams": 30,
   #   "source": "config" | "model_defaults"
   # }
   # Used by frontend wizard to show defaults
   ```

4. **Write comprehensive integration tests**
   ```bash
   # Create test files covering:
   # - Create multi-plate run (with plates array)
   # - List and get individual plates
   # - Mark plates complete (status transitions)
   # - Auto-completion detection (all plates done → run complete)
   # - Calculate plates endpoint
   # - Production defaults endpoint (with and without printer config)

   poetry run pytest tests/integration/test_production_run_plates_api.py -v
   poetry run pytest tests/integration/test_production_run_create_multi_plate.py -v
   ```

5. **Verify full test suite passes**
   ```bash
   poetry run pytest tests/ -v
   # All tests must pass before session is complete
   ```

**Acceptance Criteria**:
- [ ] Can create multi-plate run from API
- [ ] Can mark individual plates complete
- [ ] Run status updates when all plates complete
- [ ] Calculate endpoint returns accurate plate breakdown
- [ ] Material availability check works
- [ ] Integration tests for all new/modified endpoints
- [ ] All tests pass (no regressions)

**Files to Modify**:
- `backend/app/api/v1/production_runs.py`
- `backend/app/api/v1/models.py`

**Files to Create**:
- `backend/tests/integration/test_production_run_plates_api.py`
- `backend/tests/integration/test_production_run_create_multi_plate.py`

---

## Phase 3: Frontend Integration (Sessions 6-9)

### Session 6: Printer Management UI + Component Tests (2-3 hours)

**Goal**: Create UI for managing printers with component tests

**Approach**: Create components, then write component tests verifying rendering, user interactions, and API integration before moving to next session.

**Tasks**:

1. **Create printer API client** (`frontend/src/lib/api/printers.ts`)
   ```typescript
   // Reference pattern: frontend/src/lib/api/models.ts
   // Functions needed:
   // - listPrinters(params?)
   // - getPrinter(id)
   // - createPrinter(data)
   // - updatePrinter(id, data)
   // - deletePrinter(id)
   ```

2. **Create printer types** (`frontend/src/types/printer.ts`)
   ```typescript
   export interface Printer {
     id: string
     tenant_id: string
     name: string
     manufacturer?: string
     model?: string
     bed_size_x_mm?: number
     bed_size_y_mm?: number
     bed_size_z_mm?: number
     nozzle_diameter_mm?: number
     default_bed_temp?: number
     default_nozzle_temp?: number
     capabilities?: Record<string, any>
     is_active: boolean
     notes?: string
     created_at: string
     updated_at: string
   }

   export interface PrinterCreate { /* ... */ }
   export interface PrinterUpdate { /* ... */ }
   ```

3. **Create printer list page** (`frontend/src/pages/PrintersPage.tsx`)
   ```typescript
   // Reference pattern: frontend/src/pages/ModelsPage.tsx
   // Features:
   // - Table with printer list
   // - "Add Printer" button → opens dialog
   // - Edit/Delete buttons per row
   // - Filter by active/inactive
   // - Search by name
   ```

4. **Create printer dialog** (`frontend/src/components/printers/PrinterDialog.tsx`)
   ```typescript
   // Form fields:
   // - Name (required)
   // - Manufacturer
   // - Model
   // - Bed size (X, Y, Z)
   // - Nozzle diameter (default 0.4)
   // - Default temps (bed, nozzle)
   // - Active toggle
   // - Notes
   ```

5. **Add to navigation** (`frontend/src/components/layout/Sidebar.tsx`)
   ```typescript
   // Add "Printers" link under Settings section
   ```

**Acceptance Criteria**:
- [ ] Can list all printers
- [ ] Can create new printer
- [ ] Can edit existing printer
- [ ] Can delete printer (with confirmation)
- [ ] Form validation works
- [ ] Loading states displayed
- [ ] Error messages shown

**Files to Create**:
- `frontend/src/lib/api/printers.ts`
- `frontend/src/types/printer.ts`
- `frontend/src/pages/PrintersPage.tsx`
- `frontend/src/components/printers/PrinterDialog.tsx`

**Files to Modify**:
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/routes/index.tsx` (add printer route)

---

### Session 7: Model Printer Config UI + Component Tests (2-3 hours)

**Goal**: Allow configuring printer-specific settings for models with component tests

**Approach**: Create components, then write component tests verifying rendering, form validation, and API integration before moving to next session.

**Tasks**:

1. **Create config API client** (`frontend/src/lib/api/model-printer-configs.ts`)
   ```typescript
   // Functions needed:
   // - getConfigsForModel(modelId)
   // - getConfigForPrinter(modelId, printerId)
   // - createConfig(data)
   // - updateConfig(id, data)
   // - deleteConfig(id)
   ```

2. **Add config section to Model detail page** (`frontend/src/pages/ModelDetailPage.tsx`)
   ```typescript
   // New tab: "Printer Configs"
   // Shows table of configured printers:
   // Printer | Prints/Plate | Print Time | Material Weight | Actions
   // A1 Mini | 3           | 45 min    | 30g            | Edit Delete
   // A1      | 4           | 50 min    | 35g            | Edit Delete
   //
   // "Add Printer Config" button
   ```

3. **Create config dialog** (`frontend/src/components/models/ModelPrinterConfigDialog.tsx`)
   ```typescript
   // Form fields:
   // - Printer (dropdown, can't edit if updating)
   // - Prints per plate
   // - Print time (minutes)
   // - Material weight (grams per item)
   // - Bed temperature
   // - Nozzle temperature
   // - Layer height
   // - Infill percentage
   // - Supports (yes/no)
   // - Brim (yes/no)
   // - Notes
   ```

4. **Add quick-fill button** (`frontend/src/components/models/ModelPrinterConfigDialog.tsx`)
   ```typescript
   // "Copy from Model Defaults" button
   // Pre-fills form with Model.prints_per_plate, etc.
   ```

**Acceptance Criteria**:
- [ ] Can view all configs for a model
- [ ] Can add new config for printer
- [ ] Can edit existing config
- [ ] Can delete config
- [ ] Quick-fill from model defaults works
- [ ] Form validates inputs

**Files to Create**:
- `frontend/src/lib/api/model-printer-configs.ts`
- `frontend/src/types/model-printer-config.ts`
- `frontend/src/components/models/ModelPrinterConfigDialog.tsx`

**Files to Modify**:
- `frontend/src/pages/ModelDetailPage.tsx`

---

### Session 8: Update Production Run Wizard - Part 1 + Component Tests (3-4 hours)

**Goal**: Extend wizard to support printer selection and plate calculation with component tests

**Approach**: Create components, then write component tests verifying wizard flow, calculations, and form state before moving to next session.

**Tasks**:

1. **Add printer selection to Step 1** (`frontend/src/components/production-runs/CreateRunWizard.tsx`)
   ```typescript
   // Before quantities, add:
   // - Product dropdown (optional - for product-based runs)
   // - Printer dropdown (required - fetches from /api/v1/printers)
   // - Quantity input (if product selected)
   // - "Calculate Plates" button (if product + printer + quantity)
   ```

2. **Create plate calculator** (`frontend/src/lib/production-run-calculator.ts`)
   ```typescript
   // Client-side calculator:
   // - Takes product, printer, quantity
   // - Calls /api/v1/production-runs/calculate-plates
   // - Returns list of plates with estimates
   // - Checks material availability
   ```

3. **Add Step 1.5: Review Calculated Plates** (`frontend/src/components/production-runs/CreateRunWizard.tsx`)
   ```typescript
   // Show after clicking "Calculate Plates":
   // Table:
   // Plate | Model | Qty | Prints/Plate | Print Time | Material | Status
   // 1     | Dragon| 2   | 3            | 45 min × 2 | 180g PLA | ✓ Available
   // 2     | Tongue| 1   | 6            | 20 min     | 30g Pink | ✓ Available
   // ...
   //
   // Summary:
   // Total Plates: 37
   // Total Print Time: ~48 hours
   // Materials Needed: [list with availability status]
   //
   // [Adjust Plates] [Cancel] [Continue →]
   ```

4. **Handle two creation modes**
   ```typescript
   // Mode A: Product-based (new)
   // - User selects product + printer + quantity
   // - System calculates plates
   // - User reviews and creates
   // - Backend uses create_multi_plate_run()
   //
   // Mode B: Manual (existing)
   // - User manually adds items and materials
   // - Works as before
   // - Backend uses create_production_run()
   ```

5. **Update form state** (`frontend/src/components/production-runs/CreateRunWizard.tsx`)
   ```typescript
   // Add to WizardFormData:
   interface WizardFormData {
     // ... existing fields ...

     // New fields:
     printer_id?: string
     product_id?: string
     product_quantity?: number
     creation_mode: 'product' | 'manual'
     plates: ProductionRunPlateCreate[]
   }
   ```

**Acceptance Criteria**:
- [ ] Can select printer from dropdown
- [ ] Can select product from dropdown
- [ ] Calculate plates button works
- [ ] Plate breakdown displays correctly
- [ ] Material availability check shows status
- [ ] Can proceed with calculated plates
- [ ] Can still use manual mode (backward compatible)

**Files to Modify**:
- `frontend/src/components/production-runs/CreateRunWizard.tsx`

**Files to Create**:
- `frontend/src/lib/production-run-calculator.ts`
- `frontend/src/components/production-runs/PlateBreakdownTable.tsx`

**Common Pitfalls**:
- Not handling case where no printer configs exist (should show warning)
- Forgetting to recalculate when user changes quantity
- Not showing loading state during calculation
- Material availability check calling wrong spools endpoint

---

### Session 9: Update Production Run Wizard - Part 2 + Component Tests (2-3 hours)

**Goal**: Complete wizard integration and plate tracking UI with component tests

**Approach**: Complete implementation and write component tests verifying submission, plate tracking, and progress display before moving to final session.

**Tasks**:

1. **Update submission logic** (`frontend/src/components/production-runs/CreateRunWizard.tsx`)
   ```typescript
   const handleSubmit = async () => {
     if (formData.creation_mode === 'product') {
       // Submit with printer_id, product_id, plates[]
       await createProductionRun({
         printer_id: formData.printer_id,
         product_id: formData.product_id,
         plates: formData.plates,
         // ... other fields
       })
     } else {
       // Submit with items[] and materials[] (existing flow)
       await createProductionRun({
         items: formData.items,
         materials: formData.materials,
         // ... other fields
       })
     }
   }
   ```

2. **Update run detail page** (`frontend/src/pages/ProductionRunDetailPage.tsx`)
   ```typescript
   // Detect if multi-plate run:
   const isMultiPlate = run.total_plates > 0

   // Show plates tab if multi-plate:
   if (isMultiPlate) {
     return <ProductionRunPlatesView run={run} />
   } else {
     return <ProductionRunItemsView run={run} />  // existing
   }
   ```

3. **Create plates view** (`frontend/src/components/production-runs/ProductionRunPlatesView.tsx`)
   ```typescript
   // Shows:
   // - Progress bar: "15/37 plates complete (40.5%)"
   // - Table of plates:
   //   ✓ Plate 1: Dragon Bodies × 2 (Complete - 1.5h actual)
   //   ✓ Plate 2: Dragon Tongues (Complete - 18m actual)
   //   🖨 Plate 3: Terrarium Wall 1/6 (3/5 complete) [Printing...]
   //   ⏸ Plate 4: Terrarium Wall 2/6 (Pending)
   // - "Mark Plate Complete" button (opens modal)
   // - "Complete Run" button (appears when all plates done)
   ```

4. **Create mark complete modal** (`frontend/src/components/production-runs/MarkPlateCompleteDialog.tsx`)
   ```typescript
   // Form:
   // - Plate name (readonly)
   // - Actual print time (minutes)
   // - Actual material weight (grams)
   // - Successful prints (number)
   // - Failed prints (number)
   // - Notes (optional)
   // - [Cancel] [Mark Complete]
   ```

5. **Show completion prompt** (`frontend/src/components/production-runs/ProductionRunPlatesView.tsx`)
   ```typescript
   // When run.status === 'ready_for_assembly':
   // Show banner:
   // 🎉 All 37 plates complete! Ready to assemble 5× Small Terrarium Sets?
   //
   // Stats:
   // - Actual Time: 46.5 hours (vs 48h estimated)
   // - Material Used: 1,230g (vs 1,250g estimated)
   // - Failed Prints: 2 (reprinted)
   //
   // [Mark as Assembled] → Increments Product.units_in_stock
   ```

**Acceptance Criteria**:
- [ ] Product-based runs submit correctly
- [ ] Plate progress displays accurately
- [ ] Can mark individual plates complete
- [ ] Run auto-completes when all plates done
- [ ] Assembly completion flow works
- [ ] Product inventory increments correctly
- [ ] Backward compatible with item-based runs

**Files to Modify**:
- `frontend/src/components/production-runs/CreateRunWizard.tsx`
- `frontend/src/pages/ProductionRunDetailPage.tsx`

**Files to Create**:
- `frontend/src/components/production-runs/ProductionRunPlatesView.tsx`
- `frontend/src/components/production-runs/MarkPlateCompleteDialog.tsx`
- `frontend/src/components/production-runs/PlateProgressBar.tsx`

---

## Phase 4: E2E Testing & Polish (Session 10)

### Session 10: E2E Testing, Seed Data & Documentation (3-4 hours)

**Goal**: End-to-end manual testing, seed data, and documentation

**Note**: Unit tests and integration tests should already be complete from Sessions 1-9. This session focuses on E2E validation and polish.

**Tasks**:

1. **Verify test coverage**
   ```bash
   cd backend
   poetry run pytest --cov=app --cov-report=term-missing

   cd ../frontend
   npm run test

   # Target: >80% coverage for new code
   ```

2. **Manual E2E test scenarios**
   ```bash
   # Test Scenario 1: Create printer
   # - Navigate to /printers
   # - Click "Add Printer"
   # - Fill form: "Bambu A1 Mini", 180×180×180 bed
   # - Save
   # - Verify appears in list

   # Test Scenario 2: Configure model for printer
   # - Navigate to model detail page
   # - Click "Printer Configs" tab
   # - Click "Add Config"
   # - Select "Bambu A1 Mini"
   # - Set prints_per_plate = 3, time = 45min
   # - Save
   # - Verify appears in table

   # Test Scenario 3: Create multi-plate run
   # - Navigate to /production-runs/new
   # - Select product: "Small Terrarium Set"
   # - Select printer: "Bambu A1 Mini"
   # - Enter quantity: 5
   # - Click "Calculate Plates"
   # - Verify 37 plates displayed
   # - Click "Create Run"
   # - Verify run created with 37 plates

   # Test Scenario 4: Track plate progress
   # - Open run detail page
   # - Click "Mark Plate 1 Complete"
   # - Enter actual time: 43 minutes
   # - Mark complete
   # - Verify progress bar updates (1/37)
   # - Repeat for all 37 plates
   # - Verify run status changes to "ready_for_assembly"
   # - Click "Mark as Assembled"
   # - Verify Product inventory increments by 5
   ```

3. **Create seed data migration** (`backend/alembic/versions/[hash]_seed_printers.py`)
   ```python
   def upgrade() -> None:
       # Insert default printers for each tenant
       # Bambu A1 Mini (180x180x180)
       # Bambu A1 (256x256x256)
       # Note: Only seed for existing tenants, use SQL query to get tenant IDs
   ```

4. **Add API documentation** (`docs/API.md`)
   ```markdown
   ## Printers
   ### List Printers - GET /api/v1/printers
   ### Create Printer - POST /api/v1/printers
   ... (document all endpoints)

   ## Model Printer Configs
   ... (document all endpoints)

   ## Production Run Plates
   ... (document all endpoints)
   ```

5. **Update user docs** (`docs/USER_GUIDE.md`)
   ```markdown
   ## Managing Printers
   ### Adding a Printer
   1. Navigate to Settings → Printers
   2. Click "Add Printer"
   3. Fill in details...

   ### Configuring Models for Printers
   1. Open model detail page
   2. Click "Printer Configs" tab
   3. ...

   ## Creating Multi-Plate Production Runs
   ...
   ```

**Acceptance Criteria**:
- [ ] Test coverage > 80% for new code
- [ ] All E2E scenarios pass manually
- [ ] Seed data migration works
- [ ] API documentation complete
- [ ] User guide updated
- [ ] No regression in existing features

**Files to Create**:
- `backend/alembic/versions/[hash]_seed_printers.py`
- `docs/API.md` (update)
- `docs/USER_GUIDE.md` (update)

**Files to Modify**:
- `docs/API.md`
- `README.md`
- Various components (tooltips)

---

## Session Checkpoints

After each session, update this section with progress:

### Session 1 (Date: 2025-12-15 ~14:00 GMT)
- **Completed**:
  - Created `Printer` model with all fields, relationships, and computed properties
  - Created `ModelPrinterConfig` model with printer-specific settings
  - Created `ProductionRunPlate` model with status tracking and progress calculations
  - Updated `ProductionRun` model with new fields and multi-plate support
  - Updated `Model`, `Product`, `Tenant` models with new relationships
  - Updated `__init__.py` with all exports
  - Verified all imports and relationships work correctly
  - Tested computed properties (is_multi_plate, plates_progress_percentage, etc.)
- **Blockers**: None
- **Next**: Session 2 - Pydantic Schemas (PrinterBase, PrinterCreate, PrinterUpdate, PrinterResponse, etc.)

### Session 2 (Date: ______)
- **Completed**:
- **Blockers**:
- **Next**:

... (continue for all sessions)

---

## Testing Strategy

### Unit Tests (70% of tests)

**What to test**:
- Service methods (business logic)
- Schemas (validation)
- Calculations (plate math, material estimates)

**Pattern**:
```python
# backend/tests/unit/test_printer_service.py
async def test_create_printer(db_session, test_tenant):
    """Test printer creation with valid data."""
    service = PrinterService(db_session, test_tenant)

    data = PrinterCreate(name="Bambu A1 Mini", ...)
    printer = await service.create_printer(data)

    assert printer.id is not None
    assert printer.name == "Bambu A1 Mini"
    assert printer.tenant_id == test_tenant.id
```

### Integration Tests (25% of tests)

**What to test**:
- API endpoints (request → response)
- Database interactions
- Multi-step flows

**Pattern**:
```python
# backend/tests/integration/test_printers_api.py
async def test_create_printer_endpoint(client, test_tenant):
    """Test POST /api/v1/printers endpoint."""
    response = await client.post("/api/v1/printers", json={
        "name": "Bambu A1 Mini",
        "bed_size_x_mm": 180,
        ...
    })

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bambu A1 Mini"
```

### E2E Tests (5% of tests)

**What to test**:
- Critical user journeys
- Multi-page flows

**Tools**:
- Playwright (if time permits)
- Manual testing checklist (minimum)

---

## Rollback Plan

### If Need to Rollback

**Database rollback**:
```bash
cd backend
poetry run alembic downgrade -1  # Roll back one migration
poetry run alembic downgrade r5s6t7u8v9w0  # Roll back to before printers
```

**Code rollback**:
```bash
git log --oneline
git revert <commit-hash>
```

### Partial Rollback Strategy

If only one part is broken:
- Can disable feature via feature flag (add later)
- Can hide UI but keep backend working
- Can keep new tables but not use them (minimal impact)

### Data Safety

- All migrations have `downgrade()` implemented
- Foreign keys use `SET NULL` (not CASCADE) where appropriate
- Old production run system still works (backward compatible)
- No data loss on rollback

---

## Key Files Reference

### Backend

- Models: `backend/app/models/`
  - `printer.py` - NEW
  - `model_printer_config.py` - NEW
  - `production_run_plate.py` - NEW
  - `production_run.py` - MODIFIED
  - `model.py` - MODIFIED

- Schemas: `backend/app/schemas/`
  - `printer.py` - NEW
  - `model_printer_config.py` - NEW
  - `production_run_plate.py` - NEW
  - `production_run.py` - MODIFIED

- Services: `backend/app/services/`
  - `printer.py` - NEW
  - `model_printer_config.py` - NEW
  - `production_run_calculator.py` - NEW
  - `production_run.py` - MODIFIED

- API: `backend/app/api/v1/`
  - `printers.py` - NEW
  - `model_printer_configs.py` - NEW
  - `production_runs.py` - MODIFIED
  - `models.py` - MODIFIED

### Frontend

- API Clients: `frontend/src/lib/api/`
  - `printers.ts` - NEW
  - `model-printer-configs.ts` - NEW
  - `production-runs.ts` - MODIFIED

- Types: `frontend/src/types/`
  - `printer.ts` - NEW
  - `model-printer-config.ts` - NEW
  - `production-run.ts` - MODIFIED

- Pages: `frontend/src/pages/`
  - `PrintersPage.tsx` - NEW
  - `ProductionRunDetailPage.tsx` - MODIFIED

- Components: `frontend/src/components/`
  - `printers/PrinterDialog.tsx` - NEW
  - `models/ModelPrinterConfigDialog.tsx` - NEW
  - `production-runs/CreateRunWizard.tsx` - MODIFIED
  - `production-runs/ProductionRunPlatesView.tsx` - NEW
  - `production-runs/MarkPlateCompleteDialog.tsx` - NEW

---

## Success Criteria

Feature is complete when:

- [ ] User can manage printers (CRUD)
- [ ] User can configure models for specific printers
- [ ] User can create product-based multi-plate runs
- [ ] User can track plate-by-plate progress
- [ ] System auto-detects run completion
- [ ] Product inventory updates on assembly
- [ ] All tests pass (>80% coverage)
- [ ] Documentation complete
- [ ] No regressions in existing features
- [ ] Performance acceptable (<500ms endpoints)

---

## Notes / Lessons Learned

(Add notes here as implementation progresses)

---

**Last Updated**: 2025-12-15 14:00 GMT
**Next Session**: Session 2 - Pydantic Schemas
**Current Phase**: Phase 1, Session 1 complete ✅
