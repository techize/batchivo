---
sidebar_position: 4
---

# Costing & Pricing

Calculate accurate costs and optimize pricing for profitability.

## Cost Components

### Material Cost

Automatically calculated from BOM:

```
Material Cost = Σ (weight_grams × cost_per_gram)
```

Example:
- PLA (50g × $0.020/g) = $1.00
- PETG (20g × $0.025/g) = $0.50
- **Total**: $1.50

### Labor Cost

Optional labor allocation:

```
Labor Cost = Print Time × Hourly Rate × Labor Factor
```

Example:
- Print Time: 2 hours
- Hourly Rate: $15
- Labor Factor: 0.1 (10% active time)
- **Labor Cost**: $3.00

### Overhead

Fixed costs per print:

- Electricity
- Printer depreciation
- Maintenance
- Workspace

### Component Cost

Non-printed items:

| Item | Unit Cost | Qty | Total |
|------|-----------|-----|-------|
| M3 Screws | $0.05 | 4 | $0.20 |
| Magnets | $0.15 | 2 | $0.30 |

## Total Cost

```
Total Cost = Material + Labor + Overhead + Components
```

Example breakdown:
```
Product: Desk Organizer
─────────────────────────
Materials:     $2.50
Labor:         $1.50
Overhead:      $0.50
Components:    $0.30
─────────────────────────
TOTAL COST:    $4.80
```

## Pricing Strategies

### Cost-Plus Pricing

Set a markup percentage:

```
Price = Cost × (1 + Markup%)
```

| Markup | Cost | Price |
|--------|------|-------|
| 50% | $4.80 | $7.20 |
| 100% | $4.80 | $9.60 |
| 200% | $4.80 | $14.40 |

### Value-Based Pricing

Price based on perceived value:

- Unique designs: Higher markup
- Commodity items: Lower markup
- Custom orders: Premium pricing

### Competitive Pricing

Research similar products:

```
Your Cost: $4.80
Competitor A: $12.00
Competitor B: $15.00
Your Price: $10.00 (profitable + competitive)
```

## Marketplace Fees

Account for platform fees:

| Platform | Fee Structure |
|----------|---------------|
| Etsy | 6.5% transaction + $0.20 listing |
| eBay | 12.9% final value |
| Amazon | 15% referral |
| Own Site | Payment processing only (~3%) |

### Net Profit Calculation

```
Net Profit = Sale Price - Cost - Platform Fees - Shipping
```

Example:
```
Etsy Sale: $12.00
─────────────────
Cost:         -$4.80
Etsy Fee:     -$0.98
Listing:      -$0.20
Processing:   -$0.45
─────────────────
NET PROFIT:   $5.57 (46% margin)
```

## Shipping

### Options

1. **Free Shipping** - Build into price
2. **Calculated** - Pass cost to buyer
3. **Flat Rate** - Average cost across orders

### Packaging Costs

Don't forget:
- Boxes/mailers
- Bubble wrap/padding
- Labels
- Tape

## Bulk Pricing

Offer discounts for quantities:

| Quantity | Discount | Price Each |
|----------|----------|------------|
| 1 | 0% | $10.00 |
| 5+ | 10% | $9.00 |
| 10+ | 20% | $8.00 |
| 25+ | 30% | $7.00 |

## Profit Reports

Analyze profitability:

### By Product

| Product | Sales | Revenue | Cost | Profit | Margin |
|---------|-------|---------|------|--------|--------|
| Phone Stand | 50 | $500 | $200 | $300 | 60% |
| Cable Clips | 200 | $400 | $100 | $300 | 75% |

### By Material

Track which materials are most profitable:

| Material | Usage | Cost | Revenue | ROI |
|----------|-------|------|---------|-----|
| PLA Black | 2kg | $40 | $150 | 275% |
| PETG Clear | 500g | $15 | $60 | 300% |

## Cost Optimization

### Reduce Material Cost

- Buy in bulk
- Find cheaper suppliers
- Optimize print settings (less infill)
- Reduce supports

### Reduce Time

- Faster print speeds
- Batch similar products
- Optimize bed layout
- Reduce setup time

### Reduce Waste

- Track and minimize purge
- Improve first-layer success
- Better print profiles
