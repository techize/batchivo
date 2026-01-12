# Database Schema

**Batchivo - Complete Database Schema Documentation**

---

## Overview

Batchivo uses **PostgreSQL 16+** with Row-Level Security (RLS) for multi-tenant data isolation. The schema is designed for:

- **Multi-tenancy**: Every table scoped to `tenant_id`
- **Data integrity**: Foreign keys, constraints, and transactions
- **Performance**: Strategic indexes on common query patterns
- **Auditability**: Timestamps and transaction logs
- **Flexibility**: JSONB columns for extensible metadata

**SQLite Compatibility**: Schema is compatible with SQLite for local development (without RLS features).

---

## Schema Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        TENANTS                              │
│  - Isolated data per business                               │
│  - Settings (JSONB)                                         │
└────────────┬───────────────────────────────────────────────┘
             │
             ├──> USERS (via user_tenants join table)
             │
             ├──> SPOOLS (filament inventory)
             │       └──> MATERIAL_TYPES (reference)
             │       └──> SUPPLIERS
             │       └──> INVENTORY_TRANSACTIONS (audit)
             │
             ├──> PRODUCTS (catalog)
             │       ├──> PRODUCT_MATERIALS (BOM) ──> SPOOLS
             │       ├──> PRODUCT_COMPONENTS (non-filament parts)
             │       └──> PRODUCT_PRICING ──> SALES_CHANNELS
             │
             ├──> ORDERS (sales tracking)
             │       ├──> PRODUCTS
             │       └──> SALES_CHANNELS
             │
             ├──> SALES_CHANNELS (Etsy, eBay, etc.)
             │
             ├──> SUPPLIERS
             │       └──> PURCHASES
             │              └──> PURCHASE_ITEMS ──> SPOOLS
             │
             └──> REORDER_SETTINGS (per material/color/brand)
```

---

## Core Tables

### Extensions

```sql
-- Enable UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for fuzzy text search (optional)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## Multi-Tenant Foundation

### tenants

Central table for tenant management. Every business is a tenant.

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- URL-friendly identifier
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb,  -- Flexible per-tenant config
    is_active BOOLEAN DEFAULT true,

    -- Constraints
    CONSTRAINT slug_format CHECK (slug ~* '^[a-z0-9-]+$')
);

-- Indexes
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_active ON tenants(is_active);

-- Example settings structure:
-- {
--   "branding": {
--     "logo_url": "https://...",
--     "primary_color": "#3B82F6"
--   },
--   "preferences": {
--     "currency": "USD",
--     "weight_unit": "grams",
--     "default_markup": 200
--   },
--   "limits": {
--     "max_users": 5,
--     "max_spools": 1000
--   }
-- }
```

### users

User accounts (synced from Authentik or managed locally).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    authentik_id VARCHAR(255) UNIQUE,  -- Link to Authentik user UUID
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_authentik_id ON users(authentik_id);
```

### user_tenants

Join table for many-to-many relationship between users and tenants.

```sql
CREATE TABLE user_tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',  -- owner, admin, member, viewer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    invited_by UUID REFERENCES users(id),

    -- Constraints
    UNIQUE(user_id, tenant_id),
    CONSTRAINT valid_role CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
);

-- Indexes
CREATE INDEX idx_user_tenants_user ON user_tenants(user_id);
CREATE INDEX idx_user_tenants_tenant ON user_tenants(tenant_id);
```

---

## Inventory Management

### material_types

Reference table for filament types (not tenant-specific).

```sql
CREATE TABLE material_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,  -- PLA, PETG, TPU, ABS, ASA, Nylon, etc.
    properties JSONB DEFAULT '{}'::jsonb,  -- Temp ranges, bed adhesion, etc.

    -- Example properties:
    -- {
    --   "nozzle_temp_min": 200,
    --   "nozzle_temp_max": 220,
    --   "bed_temp": 60,
    --   "density_g_cm3": 1.24,
    --   "characteristics": ["beginner-friendly", "low-warp"]
    -- }
);

-- Seed data examples
INSERT INTO material_types (name) VALUES
    ('PLA'), ('PETG'), ('TPU'), ('ABS'), ('ASA'),
    ('Nylon'), ('PC'), ('PVA'), ('HIPS'), ('Wood PLA');
```

### spools

Filament inventory - core of the system.

```sql
CREATE TABLE spools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identification
    spool_id VARCHAR(50) NOT NULL,  -- User-friendly: FIL-001, PLA-RED-001

    -- Material info
    material_type_id UUID REFERENCES material_types(id),
    brand VARCHAR(100),
    color VARCHAR(100),
    finish_type VARCHAR(50),  -- matte, silk, transparent, glow, marble, etc.

    -- Purchase info
    purchase_date DATE,
    purchase_cost DECIMAL(10,2),
    supplier VARCHAR(255),
    supplier_id UUID REFERENCES suppliers(id),  -- Optional FK

    -- Weight tracking
    initial_weight_g INTEGER NOT NULL,
    current_weight_g INTEGER NOT NULL,

    -- Metadata
    lead_time_days INTEGER,
    storage_location VARCHAR(100),
    notes TEXT,
    qr_code_data TEXT,  -- QR code payload for scanning

    -- Status
    is_active BOOLEAN DEFAULT true,  -- False if depleted/discarded

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, spool_id),
    CONSTRAINT positive_weight CHECK (current_weight_g >= 0),
    CONSTRAINT weight_logic CHECK (current_weight_g <= initial_weight_g)
);

-- Indexes
CREATE INDEX idx_spools_tenant ON spools(tenant_id);
CREATE INDEX idx_spools_material_type ON spools(material_type_id);
CREATE INDEX idx_spools_current_weight ON spools(current_weight_g);  -- For low stock queries
CREATE INDEX idx_spools_active ON spools(is_active);
CREATE INDEX idx_spools_supplier ON spools(supplier_id);

-- RLS Policy
ALTER TABLE spools ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON spools
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### inventory_transactions

Audit trail for all inventory changes.

```sql
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    spool_id UUID NOT NULL REFERENCES spools(id) ON DELETE CASCADE,

    -- Transaction details
    transaction_type VARCHAR(50) NOT NULL,  -- purchase, usage, adjustment, return, disposal
    quantity_grams INTEGER NOT NULL,  -- Positive for additions, negative for usage

    -- Reference to originating action
    reference_type VARCHAR(50),  -- order, purchase, manual
    reference_id UUID,  -- Order ID, Purchase ID, etc.

    -- User who made the change
    user_id UUID REFERENCES users(id),

    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_transaction_type CHECK (transaction_type IN
        ('purchase', 'usage', 'adjustment', 'return', 'disposal'))
);

-- Indexes
CREATE INDEX idx_inventory_transactions_tenant ON inventory_transactions(tenant_id);
CREATE INDEX idx_inventory_transactions_spool ON inventory_transactions(spool_id);
CREATE INDEX idx_inventory_transactions_created ON inventory_transactions(created_at DESC);
CREATE INDEX idx_inventory_transactions_type ON inventory_transactions(transaction_type);

-- RLS Policy
ALTER TABLE inventory_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON inventory_transactions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Product Catalog

### products

Things you print and sell.

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identification
    sku VARCHAR(100) NOT NULL,  -- User-friendly: VASE-001, DRAGON-STATUE
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),

    -- Costing
    labor_hours DECIMAL(5,2) DEFAULT 0,
    labor_rate DECIMAL(10,2),  -- Per hour (can be null to use tenant default)
    include_overhead BOOLEAN DEFAULT false,
    overhead_rate DECIMAL(10,2),  -- Per hour or per product

    -- Metadata
    image_url TEXT,
    external_links JSONB DEFAULT '[]'::jsonb,  -- Thingiverse, MyMiniFactory, etc.
    tags TEXT[],  -- {functional, decorative, gift, etc.}

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, sku)
);

-- Indexes
CREATE INDEX idx_products_tenant ON products(tenant_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_active ON products(is_active);
CREATE INDEX idx_products_tags ON products USING GIN(tags);  -- Array index

-- RLS Policy
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON products
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### product_materials

Bill of Materials (BOM) - links products to spools.

```sql
CREATE TABLE product_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    spool_id UUID NOT NULL REFERENCES spools(id) ON DELETE RESTRICT,  -- Prevent spool deletion if in use

    -- Material usage
    weight_grams INTEGER NOT NULL,  -- Includes print, supports, purge, waste
    material_slot VARCHAR(50),  -- primary, secondary, accent, support, purge

    -- Breakdown (optional)
    print_weight_grams INTEGER,  -- Actual part weight
    support_weight_grams INTEGER,  -- Support material
    purge_waste_grams INTEGER,  -- Purge tower, prime line, etc.

    -- Metadata
    notes TEXT,

    -- Constraints
    UNIQUE(product_id, spool_id, material_slot),
    CONSTRAINT positive_weight CHECK (weight_grams > 0)
);

-- Indexes
CREATE INDEX idx_product_materials_tenant ON product_materials(tenant_id);
CREATE INDEX idx_product_materials_product ON product_materials(product_id);
CREATE INDEX idx_product_materials_spool ON product_materials(spool_id);

-- RLS Policy
ALTER TABLE product_materials ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON product_materials
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### product_components

Non-filament parts (magnets, inserts, screws, etc.).

```sql
CREATE TABLE product_components (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,

    -- Component info
    component_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    supplier VARCHAR(255),
    supplier_link TEXT,

    -- Metadata
    notes TEXT,

    -- Constraints
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT positive_cost CHECK (unit_cost >= 0)
);

-- Indexes
CREATE INDEX idx_product_components_tenant ON product_components(tenant_id);
CREATE INDEX idx_product_components_product ON product_components(product_id);

-- RLS Policy
ALTER TABLE product_components ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON product_components
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Sales & Pricing

### sales_channels

Where you sell (Etsy, eBay, local fairs, etc.).

```sql
CREATE TABLE sales_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Channel info
    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50),  -- etsy, ebay, shopify, local_fair, self_hosted, wholesale

    -- Fee structure
    fee_type VARCHAR(50),  -- percentage, fixed, hybrid
    percentage_fee DECIMAL(5,2),  -- e.g., 10.00 for 10%
    fixed_fee_per_transaction DECIMAL(10,2),
    fixed_monthly_cost DECIMAL(10,2),

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Integration config (API keys, etc.)
    config JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, name),
    CONSTRAINT valid_fee_type CHECK (fee_type IN ('percentage', 'fixed', 'hybrid', 'none'))
);

-- Indexes
CREATE INDEX idx_sales_channels_tenant ON sales_channels(tenant_id);
CREATE INDEX idx_sales_channels_active ON sales_channels(is_active);

-- RLS Policy
ALTER TABLE sales_channels ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON sales_channels
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### product_pricing

Calculated pricing per product per sales channel.

```sql
CREATE TABLE product_pricing (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sales_channel_id UUID NOT NULL REFERENCES sales_channels(id) ON DELETE CASCADE,

    -- Pricing strategy
    target_margin_percent DECIMAL(5,2),  -- e.g., 200.00 for 200% markup

    -- Calculated values (updated by trigger or app logic)
    production_cost DECIMAL(10,2),  -- Material + labor + overhead
    list_price DECIMAL(10,2),  -- What customer pays
    platform_fees DECIMAL(10,2),  -- Calculated from sales channel fees
    net_revenue DECIMAL(10,2),  -- list_price - platform_fees
    profit DECIMAL(10,2),  -- net_revenue - production_cost

    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(product_id, sales_channel_id)
);

-- Indexes
CREATE INDEX idx_product_pricing_tenant ON product_pricing(tenant_id);
CREATE INDEX idx_product_pricing_product ON product_pricing(product_id);
CREATE INDEX idx_product_pricing_channel ON product_pricing(sales_channel_id);

-- RLS Policy
ALTER TABLE product_pricing ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON product_pricing
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### orders

Sales tracking and order management.

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Order identification
    order_number VARCHAR(100) NOT NULL,
    order_date DATE NOT NULL,

    -- Customer info (optional)
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_id UUID,  -- Future: FK to customers table

    -- Product and channel
    sales_channel_id UUID REFERENCES sales_channels(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,

    -- Pricing (captured at order time)
    item_price DECIMAL(10,2) NOT NULL,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    total_sale DECIMAL(10,2) NOT NULL,
    platform_fees DECIMAL(10,2),
    net_revenue DECIMAL(10,2),
    production_cost DECIMAL(10,2),  -- Calculated at order time
    profit DECIMAL(10,2),

    -- Order status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, printing, printed, shipped, complete, cancelled

    -- Fulfillment
    shipped_date DATE,
    tracking_number VARCHAR(100),

    -- Metadata
    notes TEXT,
    external_order_id VARCHAR(255),  -- Platform-specific order ID (Etsy, eBay)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, order_number),
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT valid_status CHECK (status IN
        ('pending', 'printing', 'printed', 'shipped', 'complete', 'cancelled', 'refunded'))
);

-- Indexes
CREATE INDEX idx_orders_tenant ON orders(tenant_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(order_date DESC);
CREATE INDEX idx_orders_product ON orders(product_id);
CREATE INDEX idx_orders_channel ON orders(sales_channel_id);

-- RLS Policy
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON orders
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Purchasing & Suppliers

### suppliers

Material suppliers.

```sql
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Supplier info
    name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(255),

    -- Performance tracking
    average_lead_time_days INTEGER,
    minimum_order DECIMAL(10,2),
    shipping_cost DECIMAL(10,2),

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, name)
);

-- Indexes
CREATE INDEX idx_suppliers_tenant ON suppliers(tenant_id);
CREATE INDEX idx_suppliers_active ON suppliers(is_active);

-- RLS Policy
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON suppliers
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### purchases

Material purchase orders.

```sql
CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Purchase info
    po_number VARCHAR(100),  -- Internal PO number
    supplier_id UUID REFERENCES suppliers(id),
    order_date DATE NOT NULL,
    received_date DATE,

    -- Costs
    subtotal DECIMAL(10,2),
    shipping_cost DECIMAL(10,2),
    tax DECIMAL(10,2),
    total_cost DECIMAL(10,2),

    -- Status
    status VARCHAR(50) DEFAULT 'ordered',  -- ordered, shipped, received, cancelled

    -- Metadata
    notes TEXT,
    tracking_number VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, po_number),
    CONSTRAINT valid_status CHECK (status IN ('ordered', 'shipped', 'received', 'cancelled'))
);

-- Indexes
CREATE INDEX idx_purchases_tenant ON purchases(tenant_id);
CREATE INDEX idx_purchases_supplier ON purchases(supplier_id);
CREATE INDEX idx_purchases_order_date ON purchases(order_date DESC);

-- RLS Policy
ALTER TABLE purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON purchases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### purchase_items

Line items in a purchase order.

```sql
CREATE TABLE purchase_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    purchase_id UUID NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,

    -- Item info
    spool_id UUID REFERENCES spools(id),  -- Linked when spool is created
    material_type_id UUID REFERENCES material_types(id),
    color VARCHAR(100),
    brand VARCHAR(100),

    -- Quantity and cost
    quantity INTEGER NOT NULL,
    weight_per_spool_g INTEGER,  -- e.g., 1000g per spool
    unit_cost DECIMAL(10,2) NOT NULL,
    total_cost DECIMAL(10,2) NOT NULL,

    -- Constraints
    CONSTRAINT positive_quantity CHECK (quantity > 0)
);

-- Indexes
CREATE INDEX idx_purchase_items_tenant ON purchase_items(tenant_id);
CREATE INDEX idx_purchase_items_purchase ON purchase_items(purchase_id);
CREATE INDEX idx_purchase_items_spool ON purchase_items(spool_id);

-- RLS Policy
ALTER TABLE purchase_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON purchase_items
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Reorder Management

### reorder_settings

Automated reorder point calculations per material/color/brand.

```sql
CREATE TABLE reorder_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Material identification
    material_type_id UUID REFERENCES material_types(id),
    color VARCHAR(100),
    brand VARCHAR(100),

    -- Usage tracking
    avg_daily_usage_grams INTEGER,  -- Calculated from transaction history

    -- Reorder logic
    lead_time_days INTEGER NOT NULL,
    safety_stock_days INTEGER DEFAULT 7,  -- Extra buffer days
    reorder_point_grams INTEGER,  -- Calculated: (avg_daily * (lead_time + safety))
    reorder_quantity_grams INTEGER,  -- How much to order

    -- Metadata
    last_calculated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(tenant_id, material_type_id, color, brand)
);

-- Indexes
CREATE INDEX idx_reorder_settings_tenant ON reorder_settings(tenant_id);
CREATE INDEX idx_reorder_settings_material ON reorder_settings(material_type_id);

-- RLS Policy
ALTER TABLE reorder_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON reorder_settings
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Helper Functions & Views

### Calculated Remaining Percentage (View)

```sql
CREATE VIEW spool_inventory_status AS
SELECT
    s.id,
    s.tenant_id,
    s.spool_id,
    s.brand,
    s.color,
    mt.name AS material_type,
    s.initial_weight_g,
    s.current_weight_g,
    s.initial_weight_g - s.current_weight_g AS used_weight_g,
    ROUND((s.current_weight_g::numeric / s.initial_weight_g * 100), 2) AS remaining_percent,
    CASE
        WHEN s.current_weight_g = 0 THEN 'depleted'
        WHEN s.current_weight_g::numeric / s.initial_weight_g <= 0.1 THEN 'critical'
        WHEN s.current_weight_g::numeric / s.initial_weight_g <= 0.25 THEN 'low'
        ELSE 'ok'
    END AS stock_status
FROM spools s
LEFT JOIN material_types mt ON s.material_type_id = mt.id
WHERE s.is_active = true;
```

### Product Cost Calculator (Function)

```sql
CREATE OR REPLACE FUNCTION calculate_product_cost(p_product_id UUID)
RETURNS DECIMAL(10,2) AS $$
DECLARE
    v_material_cost DECIMAL(10,2) := 0;
    v_component_cost DECIMAL(10,2) := 0;
    v_labor_cost DECIMAL(10,2) := 0;
    v_overhead_cost DECIMAL(10,2) := 0;
    v_total_cost DECIMAL(10,2);
BEGIN
    -- Calculate material costs
    SELECT COALESCE(SUM(
        (pm.weight_grams::numeric / s.initial_weight_g) * s.purchase_cost
    ), 0) INTO v_material_cost
    FROM product_materials pm
    JOIN spools s ON pm.spool_id = s.id
    WHERE pm.product_id = p_product_id;

    -- Calculate component costs
    SELECT COALESCE(SUM(quantity * unit_cost), 0) INTO v_component_cost
    FROM product_components
    WHERE product_id = p_product_id;

    -- Calculate labor costs
    SELECT COALESCE(labor_hours * COALESCE(labor_rate, 0), 0) INTO v_labor_cost
    FROM products
    WHERE id = p_product_id;

    -- Calculate overhead (if enabled)
    SELECT CASE
        WHEN include_overhead THEN COALESCE(labor_hours * COALESCE(overhead_rate, 0), 0)
        ELSE 0
    END INTO v_overhead_cost
    FROM products
    WHERE id = p_product_id;

    v_total_cost := v_material_cost + v_component_cost + v_labor_cost + v_overhead_cost;

    RETURN v_total_cost;
END;
$$ LANGUAGE plpgsql;
```

### Update Spool Weight (Function)

Safely update spool weight with transaction logging.

```sql
CREATE OR REPLACE FUNCTION update_spool_weight(
    p_spool_id UUID,
    p_new_weight_g INTEGER,
    p_transaction_type VARCHAR,
    p_reference_type VARCHAR DEFAULT 'manual',
    p_reference_id UUID DEFAULT NULL,
    p_user_id UUID DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_tenant_id UUID;
    v_current_weight INTEGER;
    v_weight_change INTEGER;
BEGIN
    -- Get current weight and tenant
    SELECT current_weight_g, tenant_id INTO v_current_weight, v_tenant_id
    FROM spools
    WHERE id = p_spool_id;

    -- Calculate change
    v_weight_change := p_new_weight_g - v_current_weight;

    -- Update spool
    UPDATE spools
    SET current_weight_g = p_new_weight_g,
        updated_at = NOW()
    WHERE id = p_spool_id;

    -- Log transaction
    INSERT INTO inventory_transactions (
        tenant_id, spool_id, transaction_type, quantity_grams,
        reference_type, reference_id, user_id, notes
    ) VALUES (
        v_tenant_id, p_spool_id, p_transaction_type, v_weight_change,
        p_reference_type, p_reference_id, p_user_id, p_notes
    );

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

---

## Triggers

### Auto-Update Timestamps

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_spools_updated_at BEFORE UPDATE ON spools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_purchases_updated_at BEFORE UPDATE ON purchases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sales_channels_updated_at BEFORE UPDATE ON sales_channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reorder_settings_updated_at BEFORE UPDATE ON reorder_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Data Integrity & Constraints Summary

1. **Tenant Isolation**: Every table has `tenant_id` + RLS policy
2. **Foreign Keys**: Cascade deletes for dependent data, restrict for referenced data
3. **Check Constraints**: Validate data at insert/update (positive weights, valid statuses)
4. **Unique Constraints**: Prevent duplicates (tenant+spool_id, tenant+sku, etc.)
5. **Indexes**: Optimize common queries (tenant lookups, date ranges, status filters)

---

## Migration Strategy

**Using Alembic** (Python migration tool):

```bash
# Create migration
poetry run alembic revision --autogenerate -m "Create initial schema"

# Apply migration
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

---

## Performance Considerations

1. **Partitioning** (future): Partition `inventory_transactions` by date when > 10M rows
2. **Archiving**: Move old orders to archive tables after 2 years
3. **Indexes**: Add covering indexes for complex queries as identified
4. **Connection Pooling**: Use PgBouncer for high-traffic scenarios
5. **Query Optimization**: Use EXPLAIN ANALYZE to identify slow queries

---

## Backup Strategy

1. **Daily**: Automated pg_dump to S3
2. **Hourly**: WAL archiving for point-in-time recovery
3. **Before migrations**: Manual snapshot
4. **Retention**: 30 days of daily backups, 7 days of hourly

---

*Last Updated: 2025-10-29*
*Schema Version: 1.0*
