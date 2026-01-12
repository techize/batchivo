# Print Business Management System - Design Document

## Executive Summary

This document proposes enhancements to Batchivo to support complete print business management, including:
- **Product Sets & Collections** - Group parts into sellable sets
- **Consumables Inventory** - Track magnets, inserts, hardware
- **Comprehensive Costing** - Per-part, per-set, true COGS
- **Pricing Engine** - Marketplace fees, profit margins, break-even analysis
- **Batch Production Planning** - Multi-set production workflows

---

## Research Summary

### Industry Solutions Reviewed

| Solution | Strengths | Limitations |
|----------|-----------|-------------|
| [PrintFarmHQ](https://printfarmhq.io/) | True COGS (materials + depreciation + labor + licenses), profit margin tracking | Beta, print-farm focused |
| [Katana MRP](https://katanamrp.com/bill-of-materials-software/) | Multi-level BOMs, real-time cost updates, ERP integration | Complex, enterprise-priced |
| [AutoFarm3D](https://www.3dque.com/autofarm3d) | Order management, filament tracking, batch routing | Hardware-specific |
| [Prusa Price Calculator](https://blog.prusa3d.com/3d-printing-price-calculator_38905/) | G-code upload, automatic estimates | Single prints only |
| [SimplyPrint](https://simplyprint.io/print-farms) | Multi-material mapping, fleet management | Subscription per printer |
| [MRPeasy](https://www.mrpeasy.com/manufacturing-software-3d-printers/) | Full ERP, inventory, production planning | Overkill for small business |

### Key Learnings

1. **True COGS must include**: Materials, consumables, machine depreciation, electricity, labor, software licenses, failure rate buffer
2. **Multi-color printing waste** is significant: 125g model can use 600g filament with purge/prime tower ([Tom's Hardware](https://www.tomshardware.com/3d-printing/best-multicolor-3d-printers))
3. **Batch production** is the norm: Print farms batch identical items for efficiency
4. **Cost per gram varies**: Common filament ~£0.02/g, specialty can be 10x higher ([Omni Calculator](https://www.omnicalculator.com/other/3d-printing))

---

## Current Batchivo State (v1.18)

### Existing Models

```
Spool                    Product                  ProductionRun
├── brand                ├── sku                  ├── run_number
├── color                ├── name                 ├── started_at
├── material_type_id     ├── category             ├── estimated_print_time
├── current_weight       ├── labor_hours          ├── estimated_filament_grams
├── purchase_price       ├── materials[] ──────────┤── items[] ────────────┐
└── color_hex            ├── components[]         ├── materials[]          │
                         └── print_time_minutes   └── status               │
                                                                           │
ProductMaterial                ProductComponent              ProductionRunItem
├── product_id                 ├── product_id                ├── product_id ◄──┘
├── spool_id                   ├── component_name            ├── quantity
├── weight_grams               ├── quantity                  ├── successful_quantity
└── cost_per_gram              ├── unit_cost                 └── estimated_costs
                               └── supplier
```

### What's Missing for Red Fox Set Example

| Need | Current State | Gap |
|------|---------------|-----|
| **Product Sets** | Products are flat | Need parent/child or set structure |
| **Consumable Inventory** | Ad-hoc per-product | Need tracked inventory with purchases |
| **Multi-color BOM** | Spool link exists | Works, needs UI for multi-material |
| **Set Costing** | Per-product only | Need rollup across set items |
| **Pricing Engine** | None | Need marketplace fees, margins |
| **Batch Planning** | Single runs only | Need batch grouping |

---

## Proposed Data Model

### Phase 1: Consumables Inventory

Track magnets, inserts, screws, paint, etc. as inventory items.

```sql
-- Consumable types (e.g., "Magnet 3mm x 1mm")
CREATE TABLE consumable_types (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),

    -- Identification
    sku VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),  -- magnets, inserts, hardware, finishing

    -- Unit info
    unit_of_measure VARCHAR(20) DEFAULT 'each',  -- each, ml, g, pack

    -- Current pricing (updated from latest purchase)
    current_cost_per_unit NUMERIC(10,4),

    -- Stock management
    quantity_on_hand INTEGER DEFAULT 0,
    reorder_point INTEGER,
    reorder_quantity INTEGER,

    -- Supplier info
    preferred_supplier VARCHAR(200),
    supplier_sku VARCHAR(100),
    typical_lead_days INTEGER,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(tenant_id, sku)
);

-- Consumable purchases (batch buys)
CREATE TABLE consumable_purchases (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    consumable_type_id UUID REFERENCES consumable_types(id),

    -- Purchase details
    quantity_purchased INTEGER NOT NULL,
    total_cost NUMERIC(10,2) NOT NULL,
    cost_per_unit NUMERIC(10,4) GENERATED ALWAYS AS (total_cost / quantity_purchased) STORED,

    -- Source
    supplier VARCHAR(200),
    order_reference VARCHAR(100),
    purchase_date DATE,

    -- Tracking
    quantity_remaining INTEGER,  -- For FIFO costing

    notes TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Usage log (for audit trail)
CREATE TABLE consumable_usage (
    id UUID PRIMARY KEY,
    consumable_type_id UUID REFERENCES consumable_types(id),

    -- What used it
    production_run_id UUID REFERENCES production_runs(id),
    product_id UUID REFERENCES products(id),

    -- Usage
    quantity_used INTEGER NOT NULL,
    cost_at_use NUMERIC(10,4),  -- Snapshot for historical accuracy

    usage_date TIMESTAMPTZ,
    notes TEXT
);
```

### Phase 2: Product Sets & Collections

Enable grouping products into sellable sets.

```sql
-- Product hierarchy (self-referential for sets)
ALTER TABLE products ADD COLUMN parent_product_id UUID REFERENCES products(id);
ALTER TABLE products ADD COLUMN is_set BOOLEAN DEFAULT false;
ALTER TABLE products ADD COLUMN set_quantity INTEGER DEFAULT 1;  -- How many of this in parent set

-- OR separate ProductSet table (cleaner but more joins)
CREATE TABLE product_sets (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),

    sku VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    image_url VARCHAR(500),

    -- Costing overrides
    labor_hours_override NUMERIC(10,2),
    overhead_percentage_override NUMERIC(5,2),

    -- Pricing
    base_price NUMERIC(10,2),  -- Suggested price before channel fees

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,

    UNIQUE(tenant_id, sku)
);

CREATE TABLE product_set_items (
    id UUID PRIMARY KEY,
    product_set_id UUID REFERENCES product_sets(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),

    quantity INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER DEFAULT 0,

    -- Optional notes (e.g., "any color" or "must match")
    notes TEXT
);
```

**Recommendation**: Use the `product_sets` approach for cleaner separation. A "Red Fox Set" is a `product_set` containing multiple `products`.

### Phase 3: Enhanced ProductComponent

Link components to consumable inventory for auto-costing.

```sql
ALTER TABLE product_components ADD COLUMN consumable_type_id UUID REFERENCES consumable_types(id);

-- When consumable_type_id is set:
--   - unit_cost auto-updates from consumable_types.current_cost_per_unit
--   - Usage deducts from consumable_types.quantity_on_hand
-- When NULL:
--   - Behaves as before (manual unit_cost)
```

### Phase 4: Sales Channels & Pricing

```sql
-- Sales channels (Etsy, eBay, local markets, etc.)
CREATE TABLE sales_channels (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),

    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50),  -- online_marketplace, local_market, direct, wholesale

    -- Fee structure
    transaction_fee_percentage NUMERIC(5,2) DEFAULT 0,  -- e.g., 6.5% Etsy
    transaction_fee_fixed NUMERIC(10,2) DEFAULT 0,      -- e.g., £0.20 per item
    payment_processing_percentage NUMERIC(5,2) DEFAULT 0,  -- e.g., 4% + VAT
    payment_processing_fixed NUMERIC(10,2) DEFAULT 0,
    listing_fee NUMERIC(10,2) DEFAULT 0,  -- e.g., £0.16 per listing

    -- Recurring costs
    monthly_subscription NUMERIC(10,2) DEFAULT 0,
    annual_subscription NUMERIC(10,2) DEFAULT 0,

    -- Shipping
    typical_shipping_cost NUMERIC(10,2),
    offers_free_shipping BOOLEAN DEFAULT false,

    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Product pricing per channel
CREATE TABLE product_pricing (
    id UUID PRIMARY KEY,

    -- Can price either a product OR a set
    product_id UUID REFERENCES products(id),
    product_set_id UUID REFERENCES product_sets(id),

    sales_channel_id UUID REFERENCES sales_channels(id),

    -- Pricing
    list_price NUMERIC(10,2) NOT NULL,

    -- Calculated fields (can be computed or cached)
    calculated_cogs NUMERIC(10,2),
    calculated_fees NUMERIC(10,2),
    calculated_profit NUMERIC(10,2),
    profit_margin_percentage NUMERIC(5,2),

    -- Override COGS if needed
    cogs_override NUMERIC(10,2),

    last_calculated_at TIMESTAMPTZ,
    notes TEXT,

    CONSTRAINT one_product_type CHECK (
        (product_id IS NOT NULL AND product_set_id IS NULL) OR
        (product_id IS NULL AND product_set_id IS NOT NULL)
    )
);
```

### Phase 5: Batch Production

Group production runs for multi-set manufacturing.

```sql
CREATE TABLE production_batches (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),

    -- What we're making
    batch_name VARCHAR(200) NOT NULL,
    product_id UUID REFERENCES products(id),
    product_set_id UUID REFERENCES product_sets(id),

    target_quantity INTEGER NOT NULL,  -- How many sets/products

    -- Status
    status VARCHAR(20) DEFAULT 'planning',  -- planning, in_progress, completed, cancelled

    -- Timing
    planned_start_date DATE,
    actual_start_date TIMESTAMPTZ,
    actual_end_date TIMESTAMPTZ,

    -- Totals (calculated from runs)
    total_print_time_hours NUMERIC(10,2),
    total_material_cost NUMERIC(10,2),
    total_component_cost NUMERIC(10,2),
    total_labor_cost NUMERIC(10,2),

    successful_quantity INTEGER DEFAULT 0,
    failed_quantity INTEGER DEFAULT 0,

    notes TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Link production runs to batches
ALTER TABLE production_runs ADD COLUMN production_batch_id UUID REFERENCES production_batches(id);
```

---

## Red Fox Set Example - How It Would Work

### 1. Setup Consumables

```
ConsumableType:
├── MAG-3X1: "Magnet 3mm x 1mm" @ £0.05/each (from 100-pack @ £5)
└── MAG-6X2: "Magnet 6mm x 2mm" @ £0.08/each (from 50-pack @ £4)
```

### 2. Create Products (Individual Parts)

| SKU | Name | Materials | Components | Print Time | Est. Cost |
|-----|------|-----------|------------|------------|-----------|
| FOX-001 | Red Fox Creature | Orange 15g, Brown1 8g, Brown2 5g, Beige 3g | 4× MAG-3X1 | 3h 20min | £1.82 |
| FOX-002 | Walnut in Shell | Brown1 4g | 1× MAG-3X1 | 25min | £0.21 |
| FOX-003 | Tree Snow Base | White 12g | - | 1h 10min | £0.36 |
| FOX-004 | Snow Cap | White 2g | - | 8min | £0.06 |
| FOX-005 | Tree | Wood Oak 18g | - | 1h 45min | £0.54 |
| FOX-006 | Hazelnut | Brown1 3g, Brown2 2g | 1× MAG-3X1 | 20min | £0.20 |
| FOX-007 | Acorn Top | Brown1 2g | 1× MAG-6X2 | 12min | £0.14 |
| FOX-008 | Acorn Bottom | Brown2 2g | - | 10min | £0.06 |

### 3. Create Product Set

```
ProductSet: "Red Fox Complete Set" (SKU: FOX-SET-001)
├── 1× FOX-001 (Fox Creature)      = £1.82
├── 5× FOX-002 (Walnut in Shell)   = £1.05
├── 1× FOX-003 (Tree Snow Base)    = £0.36
├── 8× FOX-004 (Snow Cap)          = £0.48
├── 1× FOX-005 (Tree)              = £0.54
├── 5× FOX-006 (Hazelnut)          = £1.00
├── 5× FOX-007 (Acorn Top)         = £0.70
├── 5× FOX-008 (Acorn Bottom)      = £0.30
                                   ─────────
                      Material+Component: £6.25
                      + Labor (8 hrs @ £12/hr): £96.00
                      + Overhead (10%): £10.23
                                   ─────────
                            Total COGS: £112.48 (for 3 sets)
                            Per Set: £37.49
```

### 4. Plan Production Batch

```
ProductionBatch: "Red Fox December Batch"
├── Target: 3 sets
├── Total Plates: 14
│
├── Run 1: 3× Fox Creature (Plate 1-3 single)
├── Run 2: 15× Walnut (3 plates, 5 per plate)
├── Run 3: 3× Tree Snow Base
├── Run 4: 24× Snow Cap (3 plates, 8 per plate)
├── Run 5: 3× Tree
├── Run 6: 15× Hazelnut (3 plates, 5 per plate)
├── Run 7: 15× Acorn Top (3 plates)
├── Run 8: 15× Acorn Bottom (3 plates)
│
└── Total Print Time: ~24 hours
```

### 5. Price for Etsy

```
SalesChannel: "Etsy UK"
├── Transaction Fee: 6.5%
├── Payment Processing: 4% + £0.20
├── Listing Fee: £0.16
└── VAT on fees: 20%

ProductPricing:
├── Set COGS: £37.49
├── List Price: £54.99
├── Etsy Fees: ~£6.80
├── Profit: £10.70
└── Margin: 19.5%
```

---

## Cost Calculation Engine

### True COGS Formula

```
COGS = Material Cost
     + Consumable Cost
     + Labor Cost
     + Machine Depreciation
     + Electricity Cost
     + Software License Allocation
     + Failure Rate Buffer
     + Overhead
```

### Per-Component Calculations

| Cost Type | Formula |
|-----------|---------|
| **Material** | `Σ(weight_grams × cost_per_gram)` including purge waste |
| **Consumable** | `Σ(quantity × cost_per_unit)` |
| **Labor** | `labor_hours × hourly_rate` (tenant setting or override) |
| **Depreciation** | `(printer_cost / expected_hours) × print_hours` |
| **Electricity** | `print_hours × printer_wattage × electricity_rate` |
| **Failure Buffer** | `subtotal × failure_rate_percentage` (default 10%) |
| **Overhead** | `subtotal × overhead_percentage` |

### Multi-Color Waste Handling

For AMS/MMU prints, track separately:
- **Model weight**: Actual filament in the print
- **Purge weight**: Color change waste
- **Prime tower weight**: Support structure for color changes

```
Total Material Cost = Σ(model_weight + purge_weight + prime_tower_weight) × cost_per_gram
```

---

## UI/UX Design Concepts

### 1. Product Set Builder

```
┌─────────────────────────────────────────────────────────────────┐
│ Red Fox Complete Set                                    [Save] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Set Items                                          Add Item ▼  │
│  ┌─────────────────────────────────────────────────────────────┐
│  │ 🦊 Red Fox Creature      ×1    £1.82   [Edit] [Remove]      │
│  │ 🥜 Walnut in Shell       ×5    £1.05   [Edit] [Remove]      │
│  │ 🌲 Tree                  ×1    £0.54   [Edit] [Remove]      │
│  │ ...                                                          │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  Cost Summary                                                   │
│  ├── Materials:     £3.18                                       │
│  ├── Consumables:   £1.23                                       │
│  ├── Labor:         £12.00 (1.0 hrs)                            │
│  ├── Overhead:      £1.64 (10%)                                 │
│  └── Total COGS:    £18.05                                      │
│                                                                 │
│  Pricing                                      [Calculate ▼]     │
│  ├── Suggested Price (30% margin): £25.79                       │
│  ├── Etsy (after fees):            £20.15 profit                │
│  └── eBay (after fees):            £19.82 profit                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Batch Production Planner

```
┌─────────────────────────────────────────────────────────────────┐
│ New Production Batch                                   [Create] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  What to Make: [Red Fox Complete Set ▼]                         │
│  Quantity:     [3] sets                                         │
│                                                                 │
│  Production Plan (auto-generated)                               │
│  ┌─────────────────────────────────────────────────────────────┐
│  │ Plate  │ Item              │ Qty │ Time   │ Filaments       │
│  ├────────┼───────────────────┼─────┼────────┼─────────────────│
│  │ 1-3    │ Fox Creature      │ 3   │ 10h    │ Orange, 2×Brown │
│  │ 4      │ Walnut            │ 15  │ 1h15m  │ Brown1          │
│  │ 5      │ Tree Snow Base    │ 3   │ 3h30m  │ White           │
│  │ ...    │ ...               │     │        │                 │
│  └────────┼───────────────────┼─────┼────────┼─────────────────┘
│           │                   │     │        │                 │
│  Totals:  │ 14 plates         │     │ 24h    │ Est. £18.90     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Consumables Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│ Consumables Inventory                            [Add Purchase] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⚠️ Low Stock Alerts                                            │
│  ├── Magnet 3×1mm: 23 remaining (reorder at 50)                 │
│  └── Heat Insert M3: 8 remaining (reorder at 20)                │
│                                                                 │
│  All Items                                        [Filter ▼]    │
│  ┌───────────────┬──────────┬──────────┬───────────┬──────────┐ │
│  │ Item          │ In Stock │ Cost/ea  │ Last Buy  │ Actions  │ │
│  ├───────────────┼──────────┼──────────┼───────────┼──────────┤ │
│  │ 🧲 Magnet 3×1 │ 23       │ £0.05    │ 2024-11-15│ [+]      │ │
│  │ 🧲 Magnet 6×2 │ 42       │ £0.08    │ 2024-10-20│ [+]      │ │
│  │ 🔩 Insert M3  │ 8        │ £0.12    │ 2024-09-01│ [+]      │ │
│  └───────────────┴──────────┴──────────┴───────────┴──────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Consumables Inventory (Foundation)
**Effort**: Medium | **Value**: High

- [ ] `ConsumableType` model and CRUD API
- [ ] `ConsumablePurchase` model and CRUD API
- [ ] Stock level tracking (quantity_on_hand)
- [ ] Link `ProductComponent` to `ConsumableType`
- [ ] Auto-cost calculation from consumable
- [ ] Low stock alerts
- [ ] Frontend: Consumables list, add purchase dialog

### Phase 2: Product Sets
**Effort**: Medium | **Value**: High

- [ ] `ProductSet` and `ProductSetItem` models
- [ ] Set CRUD API with nested items
- [ ] Cost rollup calculation (sum of parts × quantities)
- [ ] Frontend: Set builder UI
- [ ] Frontend: Set cost breakdown view

### Phase 3: Pricing Engine
**Effort**: Medium | **Value**: High

- [ ] `SalesChannel` model with fee structures
- [ ] `ProductPricing` model
- [ ] Fee calculation service
- [ ] Profit margin calculations
- [ ] Frontend: Channel setup
- [ ] Frontend: Pricing calculator
- [ ] Frontend: Side-by-side channel comparison

### Phase 4: Enhanced Costing
**Effort**: Low-Medium | **Value**: Medium

- [ ] Tenant settings for labor rate, overhead %, depreciation
- [ ] Electricity cost calculation
- [ ] Failure rate buffer
- [ ] True COGS calculator service
- [ ] Historical cost tracking
- [ ] Frontend: Cost breakdown drill-down

### Phase 5: Batch Production
**Effort**: High | **Value**: Medium

- [ ] `ProductionBatch` model
- [ ] Batch creation from set + quantity
- [ ] Auto-generate production runs from batch
- [ ] Batch progress tracking
- [ ] Frontend: Batch planner
- [ ] Frontend: Production dashboard

### Phase 6: Advanced Features
**Effort**: Various | **Value**: Various

- [ ] G-code parser for automatic estimates
- [ ] Multi-color waste calculator
- [ ] Supplier management
- [ ] Purchase order generation
- [ ] Reorder automation
- [ ] Analytics dashboard

---

## Additional Feature Ideas

### From Research

1. **Machine Depreciation Tracking** - Per-printer costs amortized over print hours
2. **Software License Allocation** - Divide Bambu Handy, slicer costs across prints
3. **Quality Rating System** - Track print quality for variance analysis
4. **Seasonal Pricing** - Adjust prices for holidays, sales events
5. **Bundle Discounts** - Automatic discounts for multi-set purchases

### Unique to Batchivo

1. **Recipe System** - Same product, different color schemes (e.g., "Arctic Fox" vs "Red Fox")
2. **Production Templates** - Save common plate configurations for reuse
3. **Smart Scheduling** - Suggest optimal print order based on filament changes
4. **Waste Optimization** - Recommend combining prints to reduce color changes
5. **Profitability Heatmap** - Visual view of most/least profitable products

---

## Technical Considerations

### Cost Calculation Service

```python
class CostingService:
    def calculate_product_cogs(self, product: Product) -> ProductCOGS:
        """Calculate true COGS for a product."""
        material_cost = self._calculate_material_cost(product)
        consumable_cost = self._calculate_consumable_cost(product)
        labor_cost = self._calculate_labor_cost(product)
        depreciation = self._calculate_depreciation(product)
        electricity = self._calculate_electricity(product)

        subtotal = sum([material_cost, consumable_cost, labor_cost,
                       depreciation, electricity])

        failure_buffer = subtotal * self.tenant.failure_rate
        overhead = subtotal * (product.overhead_percentage or self.tenant.overhead_percentage)

        return ProductCOGS(
            material=material_cost,
            consumable=consumable_cost,
            labor=labor_cost,
            depreciation=depreciation,
            electricity=electricity,
            failure_buffer=failure_buffer,
            overhead=overhead,
            total=subtotal + failure_buffer + overhead
        )

    def calculate_set_cogs(self, product_set: ProductSet) -> SetCOGS:
        """Calculate COGS for a product set."""
        item_costs = []
        for item in product_set.items:
            product_cogs = self.calculate_product_cogs(item.product)
            item_costs.append(ItemCOGS(
                product=item.product,
                quantity=item.quantity,
                unit_cost=product_cogs.total,
                total_cost=product_cogs.total * item.quantity
            ))

        return SetCOGS(
            items=item_costs,
            total=sum(ic.total_cost for ic in item_costs)
        )
```

### Fee Calculation Service

```python
class PricingService:
    def calculate_channel_fees(
        self,
        channel: SalesChannel,
        list_price: Decimal
    ) -> ChannelFees:
        """Calculate all fees for a sales channel."""
        transaction_fee = (list_price * channel.transaction_fee_percentage / 100) + channel.transaction_fee_fixed
        payment_fee = (list_price * channel.payment_processing_percentage / 100) + channel.payment_processing_fixed

        total_fees = transaction_fee + payment_fee + channel.listing_fee

        # Add VAT on fees if applicable
        if channel.vat_on_fees:
            total_fees *= Decimal("1.20")

        return ChannelFees(
            transaction=transaction_fee,
            payment=payment_fee,
            listing=channel.listing_fee,
            total=total_fees
        )

    def calculate_profit(
        self,
        list_price: Decimal,
        cogs: Decimal,
        channel: SalesChannel
    ) -> ProfitAnalysis:
        """Calculate profit for a price point."""
        fees = self.calculate_channel_fees(channel, list_price)
        profit = list_price - cogs - fees.total
        margin = (profit / list_price) * 100 if list_price > 0 else 0

        return ProfitAnalysis(
            list_price=list_price,
            cogs=cogs,
            fees=fees.total,
            profit=profit,
            margin=margin,
            break_even_price=cogs + fees.total
        )
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to add new product | < 5 minutes |
| Time to calculate set COGS | Instant (< 1 second) |
| Accuracy of cost estimates | Within 10% of actual |
| Time to plan production batch | < 10 minutes |
| User can answer "What's my profit?" | In 2 clicks |

---

## Next Steps

1. **Validate this design** - Review with user, adjust as needed
2. **Prioritize phases** - Confirm Phase 1 (Consumables) is the right start
3. **Detail Phase 1** - Create technical specs for consumables module
4. **Begin implementation** - Start with backend models and API

---

## Sources

- [PrintFarmHQ](https://printfarmhq.io/) - Print farm management with COGS tracking
- [Katana MRP](https://katanamrp.com/bill-of-materials-software/) - BOM and inventory management
- [AutoFarm3D](https://www.3dque.com/autofarm3d) - Print farm workflow management
- [Prusa Price Calculator](https://blog.prusa3d.com/3d-printing-price-calculator_38905/) - 3D printing cost estimation
- [SimplyPrint](https://simplyprint.io/print-farms) - Fleet management and material tracking
- [Omni Calculator](https://www.omnicalculator.com/other/3d-printing) - 3D printing cost breakdown
- [Tom's Hardware - Multicolor Printers](https://www.tomshardware.com/3d-printing/best-multicolor-3d-printers) - AMS/MMU waste analysis

---

*Document Version: 1.0*
*Created: 2024-12-05*
*Author: Batchivo Development Team*
