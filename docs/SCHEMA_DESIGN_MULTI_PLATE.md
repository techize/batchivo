# Database Schema Design: Multi-Plate Production Runs

**Date**: 2025-12-15
**Feature**: Multi-plate production runs with printer-specific configurations

## Overview

This design extends the production run system to support:
1. Multiple printers with different capabilities
2. Printer-specific model configurations (prints_per_plate, print_time, etc.)
3. Multi-plate production runs (one run = many plates)
4. Product-based production (track what sellable product is being made)

## New Tables

### 1. printers

Stores printer definitions (Bambu A1 Mini, A1, P2S, etc.)

```sql
CREATE TABLE printers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Printer identification
    name VARCHAR(100) NOT NULL,  -- "Bambu A1 Mini", "Bambu A1", "Bambu P2S"
    manufacturer VARCHAR(100),    -- "Bambu Lab"
    model VARCHAR(100),           -- "A1 Mini", "A1", "P2S"

    -- Physical characteristics
    bed_size_x_mm INTEGER,        -- 180 (A1 Mini), 256 (A1/P2S)
    bed_size_y_mm INTEGER,        -- 180 (A1 Mini), 256 (A1/P2S)
    bed_size_z_mm INTEGER,        -- 180 (A1 Mini), 256 (A1/P2S)
    nozzle_diameter_mm DECIMAL(3,2) DEFAULT 0.4,

    -- Default settings
    default_bed_temp INTEGER,     -- Default bed temperature
    default_nozzle_temp INTEGER,  -- Default nozzle temperature

    -- Capabilities (JSONB for future extensibility)
    capabilities JSONB DEFAULT '{}',
    -- Example: { "ams": true, "max_speed": 500, "materials": ["PLA", "PETG", "ABS"] }

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_printer_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX idx_printers_tenant ON printers(tenant_id);
CREATE INDEX idx_printers_active ON printers(is_active);

COMMENT ON TABLE printers IS '3D printers available for production runs';
```

**Seed Data**:
```sql
INSERT INTO printers (tenant_id, name, manufacturer, model, bed_size_x_mm, bed_size_y_mm, bed_size_z_mm, default_bed_temp, default_nozzle_temp, capabilities)
VALUES
    ('<tenant_id>', 'Bambu A1 Mini', 'Bambu Lab', 'A1 Mini', 180, 180, 180, 60, 220, '{"ams": true, "materials": ["PLA", "PETG", "TPU"]}'),
    ('<tenant_id>', 'Bambu A1', 'Bambu Lab', 'A1', 256, 256, 256, 60, 220, '{"ams": true, "materials": ["PLA", "PETG", "TPU", "ABS"]}');
```

### 2. model_printer_configs

Stores printer-specific configurations for each model (how many fit on A1 Mini vs A1, print times, etc.)

```sql
CREATE TABLE model_printer_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    printer_id UUID NOT NULL REFERENCES printers(id) ON DELETE CASCADE,

    -- Printing configuration
    prints_per_plate INTEGER NOT NULL DEFAULT 1,
    -- How many of this model fit on one plate for this printer

    print_time_minutes INTEGER,
    -- Total print time for full plate (all prints_per_plate items)

    -- Material usage per single item (not per plate)
    material_weight_grams DECIMAL(10,2),
    -- Weight for ONE item (multiply by prints_per_plate for full plate)

    -- Slicer settings
    bed_temperature INTEGER,
    nozzle_temperature INTEGER,
    layer_height DECIMAL(3,2),      -- e.g., 0.2mm
    infill_percentage INTEGER,      -- 15, 20, etc.
    supports BOOLEAN DEFAULT FALSE,
    brim BOOLEAN DEFAULT FALSE,

    -- Additional settings (JSONB for flexibility)
    slicer_settings JSONB DEFAULT '{}',
    -- Example: { "speed": 250, "retraction": 0.8, "z_hop": 0.2 }

    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uq_model_printer UNIQUE (model_id, printer_id),
    CONSTRAINT check_prints_per_plate_positive CHECK (prints_per_plate > 0)
);

CREATE INDEX idx_model_printer_configs_model ON model_printer_configs(model_id);
CREATE INDEX idx_model_printer_configs_printer ON model_printer_configs(printer_id);

COMMENT ON TABLE model_printer_configs IS 'Printer-specific configuration for each model (prints per plate, times, settings)';
COMMENT ON COLUMN model_printer_configs.material_weight_grams IS 'Material weight for ONE item (not full plate)';
COMMENT ON COLUMN model_printer_configs.print_time_minutes IS 'Print time for full plate with prints_per_plate items';
```

### 3. production_run_plates

Individual print plates within a production run (one run can have many plates)

```sql
CREATE TABLE production_run_plates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    production_run_id UUID NOT NULL REFERENCES production_runs(id) ON DELETE CASCADE,

    -- Plate identification
    plate_number INTEGER NOT NULL,  -- 1, 2, 3... for ordering
    plate_name VARCHAR(200) NOT NULL,  -- "Dragon Bodies (A1 Mini)", "Terrarium Wall 1/6"

    -- What's being printed
    model_id UUID NOT NULL REFERENCES models(id) ON DELETE RESTRICT,
    printer_id UUID NOT NULL REFERENCES printers(id) ON DELETE RESTRICT,

    -- Quantity for this plate
    quantity INTEGER NOT NULL DEFAULT 1,
    -- How many times this plate needs to be printed
    -- Example: 2× Dragon plates to get 6 dragons (3 per plate × 2 runs)

    -- Printer configuration snapshot (captured at creation)
    prints_per_plate INTEGER NOT NULL,
    print_time_minutes INTEGER,
    estimated_material_weight_grams DECIMAL(10,2),

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending', 'printing', 'complete', 'failed', 'cancelled'

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Actual results (filled in after completion)
    actual_print_time_minutes INTEGER,
    actual_material_weight_grams DECIMAL(10,2),
    successful_prints INTEGER DEFAULT 0,
    failed_prints INTEGER DEFAULT 0,

    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_plate_number_positive CHECK (plate_number > 0),
    CONSTRAINT check_quantity_positive CHECK (quantity > 0),
    CONSTRAINT check_status_valid CHECK (status IN ('pending', 'printing', 'complete', 'failed', 'cancelled')),
    CONSTRAINT check_completed_after_started CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);

CREATE INDEX idx_production_run_plates_run ON production_run_plates(production_run_id);
CREATE INDEX idx_production_run_plates_model ON production_run_plates(model_id);
CREATE INDEX idx_production_run_plates_printer ON production_run_plates(printer_id);
CREATE INDEX idx_production_run_plates_status ON production_run_plates(status);
CREATE INDEX idx_production_run_plates_plate_number ON production_run_plates(production_run_id, plate_number);

COMMENT ON TABLE production_run_plates IS 'Individual print plates within a multi-plate production run';
COMMENT ON COLUMN production_run_plates.quantity IS 'How many times this plate configuration needs to be printed';
COMMENT ON COLUMN production_run_plates.prints_per_plate IS 'How many items per single plate (e.g., 3 dragons per plate)';
```

## Modified Tables

### production_runs

Add fields for printer and product tracking:

```sql
ALTER TABLE production_runs
    ADD COLUMN printer_id UUID REFERENCES printers(id) ON DELETE SET NULL,
    ADD COLUMN product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    ADD COLUMN total_plates INTEGER DEFAULT 0,
    ADD COLUMN completed_plates INTEGER DEFAULT 0;

CREATE INDEX idx_production_runs_printer ON production_runs(printer_id);
CREATE INDEX idx_production_runs_product ON production_runs(product_id);

COMMENT ON COLUMN production_runs.printer_id IS 'Primary printer used for this run (can vary per plate)';
COMMENT ON COLUMN production_runs.product_id IS 'Product being produced (if making sellable product)';
COMMENT ON COLUMN production_runs.total_plates IS 'Total number of plates in this run';
COMMENT ON COLUMN production_runs.completed_plates IS 'Number of plates completed';
```

### models

Move `prints_per_plate` to `model_printer_configs` (it's now printer-specific):

```sql
-- Keep prints_per_plate on models as default/fallback
-- But prefer model_printer_configs when available
COMMENT ON COLUMN models.prints_per_plate IS 'Default prints per plate (override with model_printer_configs for specific printers)';
```

## Relationships

```
printers (1) ─────────── (N) model_printer_configs
models (1) ──────────────── (N) model_printer_configs

printers (1) ─────────── (N) production_run_plates
models (1) ──────────────── (N) production_run_plates
production_runs (1) ─────── (N) production_run_plates

printers (1) ─────────── (N) production_runs
products (1) ────────────── (N) production_runs
```

## Migration Order

1. **Create printers table** (no dependencies)
2. **Seed default printers** (Bambu A1 Mini, A1)
3. **Create model_printer_configs** (depends on printers, models)
4. **Modify production_runs** (add printer_id, product_id)
5. **Create production_run_plates** (depends on printers, models, production_runs)

## Backward Compatibility

- Existing `production_runs` will have `printer_id=NULL` and `product_id=NULL`
- Existing `production_run_items` still work (per-model tracking)
- New multi-plate runs will use `production_run_plates` for plate-level tracking
- System supports both old (item-based) and new (plate-based) approaches

## Example Data Flow

### Creating a Multi-Plate Run for "Small Terrarium Set"

**Step 1: User selects**
- Product: "Small Terrarium Set"
- Printer: "Bambu A1 Mini"
- Quantity: 5 sets

**Step 2: System calculates required plates**
```python
# Query model_printer_configs for each model in product
dragon_config = get_config(model_id="dragon", printer_id="A1 Mini")
# prints_per_plate=3, print_time_minutes=45, material_weight_grams=30

# Calculate: Need 5 dragons, 3 per plate = ceil(5/3) = 2 plates
plates = [
    {
        "model_id": "dragon",
        "printer_id": "A1 Mini",
        "quantity": 2,  # 2 plates
        "prints_per_plate": 3,
        "print_time_minutes": 45,
        "estimated_material_weight_grams": 90  # 30g × 3
    },
    # ... repeat for all models
]
```

**Step 3: Create production run**
```sql
INSERT INTO production_runs (tenant_id, printer_id, product_id, total_plates, ...)
VALUES ('<tenant>', 'A1 Mini', 'Small Terrarium Set', 37, ...);

INSERT INTO production_run_plates (production_run_id, plate_number, model_id, printer_id, quantity, ...)
VALUES ('<run_id>', 1, '<dragon_model>', 'A1 Mini', 2, ...),
       ('<run_id>', 2, '<tongue_model>', 'A1 Mini', 1, ...),
       ...;
```

**Step 4: Track plate completion**
```sql
-- Mark plate 1 as complete
UPDATE production_run_plates
SET status = 'complete',
    completed_at = NOW(),
    actual_print_time_minutes = 43,
    successful_prints = 6,
    failed_prints = 0
WHERE id = '<plate_1_id>';

-- Update run progress
UPDATE production_runs
SET completed_plates = completed_plates + 1
WHERE id = '<run_id>';
```

**Step 5: Detect run completion**
```python
# When completed_plates == total_plates
if run.completed_plates == run.total_plates:
    run.status = 'ready_for_assembly'
    # Prompt user to mark as assembled → increment product.units_in_stock
```

## UI Considerations

### Wizard Flow
1. **Select Product + Printer + Quantity**
2. **Review calculated plates** (with material check)
3. **Adjust if needed** (swap spools, change quantities)
4. **Create run** (all plates at once)

### Run Tracking UI
- Progress bar: "15/37 plates complete (40.5%)"
- Plate list with status indicators
- "Mark Plate Complete" button (opens modal for actual times/weights)
- "Complete Run" button (appears when all plates done)

### Printer Management UI
- CRUD for printers
- Configure model printer configs (link model + printer + settings)
- Bulk import configs from slicer profiles (future)

## Open Questions

1. **Should we auto-create model_printer_configs?**
   - Option A: User must manually configure each model+printer combo
   - Option B: Use model defaults (prints_per_plate, print_time) as fallback
   - **Recommended**: Option B - fallback to model defaults if no config exists

2. **Plate scheduling?**
   - Should system suggest "next plate to print"?
   - Not in Phase 1, but add `priority` field to plates for future

3. **Material allocation per plate?**
   - Currently tracked at run level (production_run_materials)
   - Should we track per-plate? (complex, defer to later phase)
   - **Recommended**: Keep at run level for now, calculate from plates

4. **Templates?**
   - Store plate configurations for reuse?
   - **Deferred to Phase 2** - focus on multi-plate runs first

## Testing Strategy

### Unit Tests
- [ ] Test printer CRUD operations
- [ ] Test model_printer_configs CRUD
- [ ] Test plate calculation logic (5 items, 3 per plate = 2 plates)
- [ ] Test run completion detection (all plates done)

### Integration Tests
- [ ] Create multi-plate run end-to-end
- [ ] Mark plates complete sequentially
- [ ] Verify run status updates correctly
- [ ] Test backward compatibility (old runs still work)

### Edge Cases
- [ ] No printer config exists (fallback to model defaults)
- [ ] Zero prints_per_plate (should error)
- [ ] Marking plate complete twice (idempotent)
- [ ] Deleting printer with active runs (should fail)

---

**Status**: Draft for review
**Next Steps**: Create Alembic migrations
