---
sidebar_position: 1
---

# Inventory Management

Track your filament spools and materials with Batchivo.

## Overview

Batchivo's inventory system lets you:

- Track individual spools with unique identifiers
- Monitor remaining filament weight
- Track purchase history and costs
- Get low-stock alerts
- Analyze material usage over time

## Managing Spools

### Creating a Spool

1. Navigate to **Inventory** → **Spools**
2. Click **Add Spool**
3. Fill in the details:
   - **Material Type**: PLA, PETG, ABS, TPU, etc.
   - **Brand**: Manufacturer name
   - **Color**: Color name and hex code
   - **Weight**: Net weight in grams
   - **Purchase Price**: Cost per spool
   - **Supplier**: Where purchased

### Spool Properties

| Property | Description |
|----------|-------------|
| Material Type | PLA, PETG, ABS, TPU, ASA, Nylon, PC, etc. |
| Brand | Manufacturer (Polymaker, Prusament, etc.) |
| Color | Color name and optional hex code |
| Finish | Matte, Glossy, Silk, etc. |
| Diameter | 1.75mm or 2.85mm |
| Net Weight | Filament weight in grams |
| Spool Weight | Empty spool weight (for weighing) |
| Purchase Price | Cost per spool |
| Cost per Gram | Automatically calculated |

### Weight Tracking

Batchivo supports two methods:

1. **Manual Entry**: Update remaining weight directly
2. **Spool Weighing**: Weigh full spool, subtract empty spool weight

For accurate tracking, record your empty spool weights by brand.

## Material Types

### Supported Materials

- **PLA** - Polylactic Acid
- **PETG** - Polyethylene Terephthalate Glycol
- **ABS** - Acrylonitrile Butadiene Styrene
- **TPU** - Thermoplastic Polyurethane
- **ASA** - Acrylonitrile Styrene Acrylate
- **Nylon** - Polyamide
- **PC** - Polycarbonate
- **HIPS** - High Impact Polystyrene
- **PVA** - Polyvinyl Alcohol (support)
- **Custom** - Define your own

### Material Properties

Each material type can have:
- Print temperature range
- Bed temperature range
- Density (for weight calculations)
- Notes and tips

## Suppliers

Track where you purchase materials:

- Company name
- Website
- Contact info
- Notes (shipping times, quality, etc.)

## Low Stock Alerts

Configure alerts when spool weight drops below threshold:

1. Go to **Settings** → **Notifications**
2. Set **Low Stock Threshold** (default: 100g)
3. Enable email or in-app notifications

## Cost Tracking

Batchivo calculates:

- **Cost per gram** from purchase price
- **Total inventory value**
- **Material cost per product** (in Product costing)
- **Usage cost per production run**

## Searching and Filtering

Find spools by:
- Material type
- Brand
- Color
- Status (in stock, low, empty)
- Supplier

## Bulk Operations

- **Import**: Upload CSV of spools
- **Export**: Download inventory list
- **Archive**: Move empty spools to archive
