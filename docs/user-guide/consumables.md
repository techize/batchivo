# Consumables

Consumables are non-filament supplies used in your 3D printing business: magnets, heat-set inserts, screws, packaging materials, adhesives, and more. Tracking these ensures accurate product costing.

---

## Accessing Consumables

Click **Consumables** in the top navigation bar to manage your supplies inventory.

---

## Why Track Consumables?

### Accurate Product Costs
Products often include hardware that adds to costs:
- A phone stand needs 4 rubber feet
- A magnetic box needs 8 magnets
- A kit needs custom packaging

### Inventory Management
Avoid running out of essential supplies:
- Low stock alerts
- Reorder point tracking
- Supplier information at hand

### Purchase History
Track spending on supplies:
- Cost per unit over time
- Supplier comparison
- Budget planning

---

## Consumable List View

The consumables page shows all items with:

| Column | Description |
|--------|-------------|
| **SKU** | Unique identifier (e.g., MAG-3X1) |
| **Name** | Item name |
| **Category** | Type of consumable |
| **Stock** | Current quantity on hand |
| **Cost** | Current cost per unit |
| **Value** | Total stock value |
| **Status** | Active/Low Stock alerts |

### Filtering

- **Search** - Find by SKU or name
- **Category** - Filter by consumable type
- **Low Stock** - Show only items below reorder point

---

## Adding a Consumable

1. Click **+ Add Consumable**
2. Fill in the details:

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **SKU** | Unique code (e.g., MAG-6X3) | Yes |
| **Name** | Descriptive name | Yes |
| **Description** | Detailed description | No |
| **Category** | Select from categories | No |
| **Unit of Measure** | How you count them | Yes |
| **Active** | Currently in use | Yes |

### Categories

| Category | Examples |
|----------|----------|
| **Magnets** | Neodymium magnets (various sizes) |
| **Inserts** | Heat-set inserts, threaded inserts |
| **Hardware** | Screws, nuts, bolts, washers |
| **Finishing** | Sandpaper, paint, primer, sealant |
| **Packaging** | Boxes, bags, labels, tissue paper |
| **Adhesives** | Super glue, epoxy, tape |
| **Other** | Any other supplies |

### Units of Measure

| Unit | Use For |
|------|---------|
| **each** | Individual items (magnets, inserts) |
| **pack** | Pre-packaged quantities |
| **box** | Box quantities |
| **g** | Grams (adhesives, powders) |
| **kg** | Kilograms |
| **ml** | Milliliters (liquids) |
| **L** | Liters |
| **meter** | Length (wire, tape) |
| **foot** | Length (imperial) |

### Stock Information

| Field | Description | Required |
|-------|-------------|----------|
| **Quantity on Hand** | Current stock level | Yes |
| **Reorder Point** | Alert threshold | No |
| **Reorder Quantity** | How many to order | No |
| **Current Cost/Unit** | Latest cost | No |

### Supplier Information

| Field | Description | Required |
|-------|-------------|----------|
| **Preferred Supplier** | Where you buy | No |
| **Supplier SKU** | Vendor's product code | No |
| **Supplier URL** | Link to purchase | No |
| **Lead Time (days)** | Typical delivery time | No |

3. Click **Add Consumable**

---

## Common Consumables

### Magnets
| SKU | Name | Typical Use |
|-----|------|-------------|
| MAG-3X1 | Magnet 3mm x 1mm | Small closures |
| MAG-6X2 | Magnet 6mm x 2mm | Medium closures |
| MAG-6X3 | Magnet 6mm x 3mm | Strong closures |
| MAG-10X3 | Magnet 10mm x 3mm | Large items |

### Heat-Set Inserts
| SKU | Name | Typical Use |
|-----|------|-------------|
| INS-M3X4 | M3 Insert 4mm | Standard threading |
| INS-M3X5 | M3 Insert 5mm | Deeper threading |
| INS-M4X5 | M4 Insert 5mm | Larger screws |

### Hardware
| SKU | Name | Typical Use |
|-----|------|-------------|
| SCR-M3X8 | M3x8mm Screw | General fastening |
| FEET-10 | Rubber Feet 10mm | Anti-slip bases |

---

## Recording Purchases

Track consumable purchases to maintain accurate costs:

1. Go to the consumable detail page
2. Click **Add Purchase**
3. Enter purchase details:

| Field | Description |
|-------|-------------|
| **Quantity Purchased** | How many you bought |
| **Total Cost** | What you paid |
| **Supplier** | Where purchased |
| **Order Reference** | Order/invoice number |
| **Purchase URL** | Link to order |
| **Purchase Date** | When purchased |
| **Notes** | Any notes |

### Cost Per Unit

Batchivo automatically calculates:
```
Cost Per Unit = Total Cost / Quantity Purchased
```

This updates the consumable's current cost per unit.

---

## Recording Usage

Track when consumables are used:

### Usage Types

| Type | Description |
|------|-------------|
| **Production** | Used in production run |
| **Adjustment** | Manual stock adjustment |
| **Waste** | Damaged/defective items |
| **Return** | Returned to supplier (negative) |

### Automatic Usage

When linked to products, usage is tracked automatically through production runs.

### Manual Adjustments

For adjustments not tied to production:
1. Go to consumable detail
2. Click **Adjust Stock**
3. Enter quantity change (positive to add, negative to remove)
4. Select reason
5. Add notes

---

## Low Stock Alerts

### Setting Reorder Points

For each consumable, set:
- **Reorder Point**: Stock level that triggers alert
- **Reorder Quantity**: Suggested order amount

### Viewing Alerts

Low stock items appear:
- With a warning badge in the list
- In the Dashboard alerts (if configured)
- When filtering by "Low Stock"

### Example

Magnet with:
- Reorder Point: 50
- Current Stock: 35

This item shows as low stock until you purchase more.

---

## Using Consumables in Products

### Adding to Product Components

1. Go to product detail page
2. Find Components section
3. Add component with:
   - Consumable reference
   - Quantity per product
   - Cost per unit

### Cost Calculation

Product cost includes:
```
Component Cost = Quantity × Cost Per Unit
```

Summed across all components.

---

## Editing a Consumable

1. Click on the consumable in the list
2. Edit any fields
3. Save changes

---

## Deactivating a Consumable

If you no longer use a consumable:

1. Edit the consumable
2. Toggle **Active** to off
3. Save

Deactivated consumables:
- Don't appear in dropdowns
- Keep historical data
- Can be reactivated

---

## Deleting a Consumable

1. Click on the consumable
2. Click **Delete**
3. Confirm deletion

**Warning**: This removes purchase and usage history.

---

## Best Practices

### SKU Conventions
Use consistent, logical SKUs:
- `MAG-` for magnets
- `INS-` for inserts
- `SCR-` for screws
- Include size: `MAG-6X3` (6mm × 3mm)

### Stock Management
- Set reorder points based on usage
- Account for lead times
- Order before running out
- Bulk buy for better prices

### Cost Accuracy
- Record all purchases
- Update costs when prices change
- Include shipping in total cost

### Supplier Tracking
- Keep supplier URLs current
- Note supplier SKUs for easy reordering
- Track lead times for planning

---

## FIFO Costing

Batchivo uses First-In-First-Out (FIFO) costing:
- Oldest purchases are used first
- Costs match actual purchase prices
- More accurate than average costing

This is handled automatically when you record purchases and usage.

---

*Next: [Designers](designers.md) - Track STL designers*
