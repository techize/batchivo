# Production Run System Design

## Overview

The Production Run system bridges the gap between Products (recipe/definition) and Orders (sales). It captures actual manufacturing data including filament usage, waste, batch printing, and variance analysis.

## Use Cases

1. **Single Item Print**: Print 1 dragon figurine
2. **Batch Print**: Print 5 dragons on one bed
3. **Multi-Product Print**: Print 2 dragons + 3 keychains on one bed
4. **Multi-Color Prints**: Track filament per color, including purge/waste
5. **Variance Analysis**: Compare estimated vs actual filament usage
6. **Production History**: Track which spools were used when
7. **Quality Tracking**: Note failures, reprints, quality issues

## Database Schema

### Table: `production_runs`

Master record for each print job (one bed load).

```sql
CREATE TABLE production_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identification
    run_number VARCHAR(50) NOT NULL,  -- Format: {tenant_short}-YYYYMMDD-NNN
    -- Example: "ABC-20250113-001"

    -- Timing
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_hours DECIMAL(6,2),  -- Calculated or manual entry

    -- Slicer Data (from .gcode analysis or manual entry)
    estimated_print_time_hours DECIMAL(6,2),
    -- Split filament tracking (model/flushed/tower)
    estimated_model_weight_grams DECIMAL(10,2),   -- Pure model material
    estimated_flushed_grams DECIMAL(10,2),        -- Color change flushing
    estimated_tower_grams DECIMAL(10,2),          -- Purge tower material
    estimated_total_weight_grams DECIMAL(10,2),   -- Computed: sum of above

    -- Actual Usage (from spool weighing or manual entry)
    actual_model_weight_grams DECIMAL(10,2),
    actual_flushed_grams DECIMAL(10,2),
    actual_tower_grams DECIMAL(10,2),
    actual_total_weight_grams DECIMAL(10,2),      -- Computed: sum of above

    -- Waste tracking (for failed prints)
    waste_filament_grams DECIMAL(10,2),  -- Total waste from failures
    waste_reason TEXT,                   -- Why waste occurred

    -- Metadata
    slicer_software VARCHAR(100),  -- "PrusaSlicer 2.7.0", "OrcaSlicer", etc.
    printer_name VARCHAR(100),     -- "Prusa MK4", "Bambu X1C", etc.
    bed_temperature INT,
    nozzle_temperature INT,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    -- Status values: 'in_progress', 'completed', 'failed', 'cancelled'

    -- Quality & Failure Tracking
    quality_rating INT CHECK (quality_rating >= 1 AND quality_rating <= 5),
    quality_notes TEXT,

    -- Failed print reference (if this is a reprint)
    original_run_id UUID REFERENCES production_runs(id) ON DELETE SET NULL,
    is_reprint BOOLEAN DEFAULT FALSE,

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_status CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled')),
    CONSTRAINT unique_run_number_per_tenant UNIQUE (tenant_id, run_number)
);

CREATE INDEX idx_production_runs_tenant ON production_runs(tenant_id);
CREATE INDEX idx_production_runs_started ON production_runs(started_at DESC);
CREATE INDEX idx_production_runs_status ON production_runs(status);
CREATE INDEX idx_production_runs_original ON production_runs(original_run_id) WHERE original_run_id IS NOT NULL;
```

### Table: `production_run_items`

Individual items printed in a run (supports batch printing).

```sql
CREATE TABLE production_run_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_run_id UUID NOT NULL REFERENCES production_runs(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,

    -- Quantity
    quantity INT NOT NULL CHECK (quantity > 0),
    successful_quantity INT NOT NULL DEFAULT 0,  -- How many came out good
    failed_quantity INT NOT NULL DEFAULT 0,      -- How many failed

    -- Position tracking (for multi-product beds)
    bed_position VARCHAR(50),  -- e.g., "Front-Left", "A1", "Position 1"

    -- Estimated costs (from product BOM at time of print)
    estimated_material_cost DECIMAL(10,2),
    estimated_component_cost DECIMAL(10,2),
    estimated_labor_cost DECIMAL(10,2),
    estimated_total_cost DECIMAL(10,2),

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_production_run_items_run ON production_run_items(production_run_id);
CREATE INDEX idx_production_run_items_product ON production_run_items(product_id);
```

### Table: `production_run_materials`

Actual filament usage per color/spool in this run.

```sql
CREATE TABLE production_run_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_run_id UUID NOT NULL REFERENCES production_runs(id) ON DELETE CASCADE,
    spool_id UUID NOT NULL REFERENCES spools(id) ON DELETE RESTRICT,

    -- Split slicer estimates (from .gcode) - per spool
    estimated_model_weight_grams DECIMAL(10,2) NOT NULL,   -- Model material from this spool
    estimated_flushed_grams DECIMAL(10,2) DEFAULT 0,       -- Flushing waste from this spool
    estimated_tower_grams DECIMAL(10,2) DEFAULT 0,         -- Tower material from this spool

    -- Spool weighing (before/after print)
    spool_weight_before_grams DECIMAL(10,2),  -- Spool weight before print
    spool_weight_after_grams DECIMAL(10,2),   -- Spool weight after print

    -- Actual usage - split by type (from spool weights or manual entry)
    actual_model_weight_grams DECIMAL(10,2),
    actual_flushed_grams DECIMAL(10,2),
    actual_tower_grams DECIMAL(10,2),

    -- Computed totals (application layer calculates these)
    -- estimated_total_weight = estimated_model + estimated_flushed + estimated_tower
    -- actual_total_weight = actual_model + actual_flushed + actual_tower (or from spool weighing)
    -- actual_weight_from_weighing = spool_weight_before - spool_weight_after

    -- Variance (computed in application layer)
    -- variance_grams = actual_total_weight - estimated_total_weight
    -- variance_percentage = (variance_grams / estimated_total_weight) * 100

    -- Cost tracking (captured at time of use)
    cost_per_gram DECIMAL(10,4) NOT NULL,
    -- total_cost computed in application layer: actual_total_weight * cost_per_gram

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_production_run_materials_run ON production_run_materials(production_run_id);
CREATE INDEX idx_production_run_materials_spool ON production_run_materials(spool_id);
```

## Relationships

```
production_runs
  ├── 1:N production_run_items (multiple products on one bed)
  │     └── N:1 products (each item references a product)
  └── 1:N production_run_materials (multiple colors/spools)
        └── N:1 spools (each material references a spool)

inventory_transactions
  └── References production_run_id (for tracking which run used material)
```

## Workflow

### 1. Create Product (Existing)
- Define the product recipe
- Add BOM with **estimated** filament per color
- Add components (magnets, etc.)

### 2. Prepare Print (New - Production Run)

**Option A: Manual Entry**
```
User Input:
- Select product(s) to print
- Enter quantity per product
- Select spool(s) to use
- Enter slicer estimates (or upload .gcode for auto-parse)
  - Total filament per color
  - Purge/waste per color change
  - Print time estimate
```

**Option B: .gcode Upload** (Future enhancement)
```
- Upload .gcode file
- System parses:
  - Filament usage per extruder
  - Purge tower waste
  - Print time
  - Temperatures
- Auto-populate production run
```

### 3. During Print
- Production run status = 'in_progress'
- Optional: Update with progress notes

### 4. After Print (Complete Run)

**User completes the run:**
```
- Weigh each spool (before/after) or enter actual usage
- Enter actual purge/waste
- Mark successful vs failed items
- Optional: Add quality rating, notes
- Status → 'completed'
```

**System actions:**
```
1. Calculate variance (actual vs estimated)
2. Create inventory_transactions for each spool
3. Deduct actual filament from spool inventory
4. Update product cost history
5. Flag if variance > threshold (e.g., ±10%)
```

### 5. Link to Order (When Sold)

When creating an Order:
```
- Select product
- System shows available inventory from production runs
- Link order to specific production run items
- Track which run produced the sold item
```

## UI Components

### 1. Production Run List
- Table view of all runs
- Filters: Status, Date range, Product, Spool
- Columns: Run #, Date, Products, Status, Variance, Actions

### 2. Create Production Run Form
```
Step 1: Basic Info
  - Run number (auto-generated)
  - Start date/time
  - Printer name
  - Slicer software

Step 2: Items to Print
  - Add product(s)
  - Quantity per product
  - Bed position (optional)

Step 3: Materials
  - Select spools for each color
  - Enter slicer estimates
    - Filament per color
    - Purge per color change
  - Auto-calculate total

Step 4: Additional Details (Optional)
  - Estimated print time
  - Bed/nozzle temps
  - Notes
```

### 3. Complete Production Run Form
```
- Enter actual filament usage per spool
- Enter actual purge/waste
- Mark successful/failed quantities
- Quality rating
- Add completion notes
- Review variance report
```

### 4. Production Run Detail Page
```
Sections:
- Run Overview (status, timing, printer)
- Items Printed (product, quantity, success rate)
- Material Usage
  - Table: Spool | Estimated | Actual | Variance
  - Variance highlights (red if >10% over, green if under)
- Cost Breakdown
  - Estimated vs Actual costs
- History/Notes
```

### 5. Variance Analysis Dashboard
```
- Chart: Estimated vs Actual over time
- Product-level variance patterns
- Spool-level consistency
- Recommendations for BOM updates
```

## API Endpoints

### Production Runs
```
POST   /api/v1/production-runs              Create new run
GET    /api/v1/production-runs              List runs (with filters)
GET    /api/v1/production-runs/{id}         Get run details
PUT    /api/v1/production-runs/{id}         Update run
POST   /api/v1/production-runs/{id}/complete  Complete run (finalize)
DELETE /api/v1/production-runs/{id}         Delete run
```

### Production Run Items
```
POST   /api/v1/production-runs/{id}/items   Add item to run
PUT    /api/v1/production-runs/{id}/items/{item_id}  Update item
DELETE /api/v1/production-runs/{id}/items/{item_id}  Remove item
```

### Production Run Materials
```
POST   /api/v1/production-runs/{id}/materials  Add material
PUT    /api/v1/production-runs/{id}/materials/{mat_id}  Update material
DELETE /api/v1/production-runs/{id}/materials/{mat_id}  Remove material
```

### Analytics
```
GET /api/v1/production-runs/variance-report  Variance analysis
GET /api/v1/products/{id}/production-history  Production history for product
GET /api/v1/spools/{id}/production-usage      Which runs used this spool
```

## Inventory Integration

When a production run is **completed**:

1. Create `inventory_transactions` records:
```sql
INSERT INTO inventory_transactions (
    spool_id,
    transaction_type,
    weight_change_grams,
    reference_type,
    reference_id,
    notes
) VALUES (
    spool_id,
    'usage',
    -actual_weight_grams,  -- Negative = deduction
    'production_run',
    production_run_id,
    'Production run RUN-2025-001'
);
```

2. Update spool `current_weight`:
```sql
UPDATE spools
SET current_weight = current_weight - actual_weight_grams,
    updated_at = NOW()
WHERE id = spool_id;
```

## Analytics & Reports

### Variance Tracking
```sql
-- Products with high variance (±10%)
SELECT
    p.sku,
    p.name,
    AVG(prm.variance_percentage) as avg_variance_pct,
    COUNT(pr.id) as run_count
FROM production_runs pr
JOIN production_run_materials prm ON pr.id = prm.production_run_id
JOIN production_run_items pri ON pr.id = pri.production_run_id
JOIN products p ON pri.product_id = p.id
WHERE pr.status = 'completed'
GROUP BY p.id, p.sku, p.name
HAVING ABS(AVG(prm.variance_percentage)) > 10
ORDER BY avg_variance_pct DESC;
```

### Production Efficiency
```sql
-- Success rate by product
SELECT
    p.sku,
    p.name,
    SUM(pri.successful_quantity) as total_success,
    SUM(pri.failed_quantity) as total_failed,
    ROUND(
        SUM(pri.successful_quantity)::DECIMAL /
        NULLIF(SUM(pri.quantity), 0) * 100,
        2
    ) as success_rate_pct
FROM production_run_items pri
JOIN products p ON pri.product_id = p.id
GROUP BY p.id, p.sku, p.name
ORDER BY success_rate_pct ASC;
```

### Cost Accuracy
```sql
-- Compare estimated vs actual costs
SELECT
    pr.run_number,
    pr.started_at,
    SUM(pri.estimated_total_cost) as estimated_cost,
    SUM(prm.total_cost) as actual_material_cost,
    SUM(prm.total_cost) - SUM(pri.estimated_total_cost) as cost_variance
FROM production_runs pr
JOIN production_run_items pri ON pr.id = pri.production_run_id
JOIN production_run_materials prm ON pr.id = prm.production_run_id
WHERE pr.status = 'completed'
GROUP BY pr.id, pr.run_number, pr.started_at
ORDER BY pr.started_at DESC;
```

## Future Enhancements

### Phase 1 (Immediate) - COMPLETE ✅
- [x] Database schema with split filament tracking (model/flushed/tower)
- [x] Backend API endpoints (CRUD, complete, cancel/fail)
- [x] Basic UI for creating runs (4-step wizard)
- [x] Production run detail page with variance display
- [x] Production run list page with filtering
- [x] Cancel/Fail workflow with failure reasons

### Phase 2 (In Progress)
- [ ] Complete run form (weight entry, quality rating)
- [ ] Edit production run form
- [ ] Variance visualization charts (Recharts)
- [ ] Production history in product pages
- [ ] Production usage in spool pages

### Phase 3 (Soon)
- [ ] .gcode parser for auto-population
- [ ] Variance alerts/notifications
- [ ] Recommend BOM updates based on variance
- [ ] Batch operations (complete multiple runs)

### Phase 4 (Later)
- [ ] Printer integration (OctoPrint, Bambu Connect)
- [ ] Real-time print monitoring
- [ ] Auto-detect failures
- [ ] Photo uploads for quality tracking
- [ ] Machine learning for better estimates

## Migration Strategy

For existing products:
1. Products with BOM remain as "estimated" recipes
2. New production runs capture actual usage
3. After N runs (e.g., 5), system can recommend BOM updates
4. Option to bulk-update BOM from production run averages

## Design Decisions (Confirmed)

1. **Run numbering**: Auto-generate format: `{tenant_short_id}-{ISO_date}-{day_count}`
   - Example: `ABC-20250113-001` (first run of day), `ABC-20250113-002` (second run)
   - Zero-based day count for multiple runs per day

2. **Weight tracking**: Flexible approach
   - "Use Estimate" button copies slicer data to actual
   - Can manually enter before/after spool weights
   - System calculates actual usage from weight difference

3. **Purge tracking**: Dual tracking
   - Per-spool purge amounts (detailed)
   - Total run purge (summary)

4. **Failed items**: New production run for reprints
   - Original run tracks failure reason and waste
   - Separate run for reprint attempts
   - Links to original run for history

5. **Quality rating**: Simple 1-5 stars
   - Star rating for overall quality
   - Optional notes field for details
   - Future: Expand to detailed criteria if needed

---

**Status**: Design confirmed, implementing
**Priority**: High - Core feature for production management
**Complexity**: Medium - Requires new tables, API, UI components
**Dependencies**: Products, Spools, Inventory Transactions (all exist)
