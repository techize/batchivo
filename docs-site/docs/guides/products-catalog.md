---
sidebar_position: 2
---

# Product Catalog

Define products with bills of materials and automatic cost calculation.

## Overview

The product catalog lets you:

- Define products with multi-material BOMs
- Calculate material costs automatically
- Track components and assemblies
- Estimate print times
- Set pricing for marketplaces

## Creating a Product

1. Navigate to **Products** → **Catalog**
2. Click **Add Product**
3. Enter product details:
   - Name and description
   - SKU (optional)
   - Category
   - Print settings

## Bill of Materials (BOM)

Each product has a BOM listing all materials used.

### Adding Materials

1. Open product → **Materials** tab
2. Click **Add Material**
3. Select material type (PLA, PETG, etc.)
4. Enter estimated weight in grams
5. Optionally specify required color

### Multi-Material Products

For products using multiple materials:

```
Product: Keychain (multicolor)
├── Material 1: PLA Black - 5g (base)
├── Material 2: PLA White - 2g (text)
└── Purge/Waste: 3g (estimated)
```

### Components

For assembled products:

```
Product: Desk Organizer Set
├── Component: Pen Holder (1x)
├── Component: Phone Stand (1x)
├── Component: Cable Clips (4x)
└── Hardware: M3 screws (8x) - $0.50
```

## Cost Calculation

Batchivo automatically calculates costs:

### Material Cost

```
Material Cost = Σ (material_weight × cost_per_gram)
```

Example:
- PLA Black: 45g × $0.02/g = $0.90
- PLA White: 5g × $0.025/g = $0.125
- **Total Material**: $1.025

### Component Cost

For assembled products:
```
Component Cost = Σ (component_cost × quantity)
```

### Total Cost

```
Total Cost = Material Cost + Component Cost + Other Costs
```

Other costs can include:
- Hardware (screws, magnets, etc.)
- Packaging
- Labor allocation

## Print Settings

Store recommended settings per product:

| Setting | Description |
|---------|-------------|
| Layer Height | 0.2mm, 0.16mm, etc. |
| Infill | Percentage and pattern |
| Supports | None, tree, normal |
| Print Time | Estimated duration |

## Product Variants

Create variants for different:
- Colors
- Sizes
- Materials

Each variant can have its own:
- BOM
- Print settings
- Pricing

## Categories

Organize products into categories:

```
├── Home & Office
│   ├── Desk Accessories
│   └── Cable Management
├── Gaming
│   ├── Controller Stands
│   └── Miniatures
└── Custom Orders
```

## Pricing

### Cost-Plus Pricing

Set markup percentage:
```
Price = Total Cost × (1 + Markup%)
```

### Marketplace Pricing

Set different prices per marketplace:

| Marketplace | Price | Fees | Net |
|-------------|-------|------|-----|
| Etsy | $15.00 | $2.25 | $12.75 |
| eBay | $14.00 | $1.82 | $12.18 |
| Website | $12.00 | $0.00 | $12.00 |

## Import/Export

- **Import**: Upload CSV with product definitions
- **Export**: Download catalog for backup
- **STL Reference**: Link to CAD files (stored separately)
