---
sidebar_position: 3
---

# Production Runs

Track print jobs from start to finish with accurate material usage.

## Overview

Production runs track:

- What you're printing (products and quantities)
- Which spools you're using
- Estimated vs actual material usage
- Print success/failure rates
- Quality ratings

## Creating a Production Run

1. Navigate to **Production** → **New Run**
2. Add products to print
3. Select spools to use
4. Record spool weights before printing
5. Start the print

## Workflow

### 1. Setup

```
┌─────────────────────────────────────┐
│         Create Production Run        │
│                                     │
│  Printer: Bambu P1S                 │
│  Estimated Time: 4h 30m             │
│  Estimated Filament: 150g           │
└─────────────────────────────────────┘
```

### 2. Add Products

Select products from your catalog:

| Product | Quantity | Est. Material |
|---------|----------|---------------|
| Phone Stand | 3 | 45g each |
| Cable Clip | 10 | 5g each |
| **Total** | 13 items | 185g |

### 3. Assign Spools

Select which spools to use:

| Spool | Material | Weight Before |
|-------|----------|---------------|
| PLA-001 | PLA Black | 850g |
| PLA-002 | PLA White | 420g |

### 4. Print & Record

After printing completes:

1. Weigh spools again
2. Count successful prints
3. Rate quality
4. Complete the run

### 5. Results

```
Production Run #42 - Completed
─────────────────────────────
Products:
  Phone Stand: 3/3 successful
  Cable Clip: 9/10 successful (1 failed)

Material Usage:
  Estimated: 185g
  Actual: 192g (+7g / +3.8%)

Quality: ★★★★☆ (4/5)
Notes: Minor stringing on cable clips
```

## Multi-Product Beds

Batchivo supports batch printing (multiple products in one print):

```
Build Plate Layout:
┌─────────────────────┐
│  ○ ○ ○   □ □ □ □   │
│  ○ ○ ○   □ □ □ □   │
│          □ □       │
└─────────────────────┘
  3x Phone Stands  10x Cable Clips
```

## Multi-Color Prints

Track purge/waste for multi-color:

| Material | Actual Use | Purge | Total |
|----------|------------|-------|-------|
| PLA Black | 45g | 8g | 53g |
| PLA White | 12g | 5g | 17g |

## Spool Weighing

For accurate tracking:

1. **Before Print**: Weigh spool on scale
2. **After Print**: Weigh spool again
3. **Actual Usage**: Before - After

### Tips

- Use a kitchen scale (0.1g precision ideal)
- Include spool in weighing (consistency)
- Record empty spool weights per brand

## Variance Analysis

Compare estimated vs actual:

```
Variance Report
───────────────
Material Variance: +7g (+3.8%)
  - Supports: +3g
  - Purge/Tower: +5g
  - Savings: -1g (efficient pathing)

Cost Variance: +$0.16
```

Use variance data to:
- Improve BOM estimates
- Identify waste patterns
- Optimize print settings

## Quality Tracking

Rate each run 1-5 stars:

| Rating | Meaning |
|--------|---------|
| ★☆☆☆☆ | Failed/unusable |
| ★★☆☆☆ | Major defects |
| ★★★☆☆ | Minor defects |
| ★★★★☆ | Good quality |
| ★★★★★ | Perfect |

## Reprints

When prints fail:

1. Mark items as failed in run
2. Create new run for reprints
3. Link to original run
4. Track reprint rate over time

## Statistics

View production statistics:

- Total runs completed
- Success rate
- Average variance
- Most printed products
- Busiest printers
