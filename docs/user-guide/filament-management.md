# Filament Management

The Inventory page is where you manage your filament spools - your raw materials for 3D printing. Accurate inventory tracking is essential for costing, production planning, and avoiding mid-print stockouts.

---

## Accessing Inventory

Click **Inventory** in the top navigation bar to view all your filament spools.

---

## Spool List View

The inventory page displays your spools in a card or table view with key information:

- **Spool ID** - Unique identifier (e.g., FIL-001)
- **Material** - Type of filament (PLA, PETG, ABS, etc.)
- **Brand** - Manufacturer name
- **Color** - Filament color with visual swatch
- **Weight** - Current weight remaining
- **Remaining %** - Visual indicator of how much is left

### Filtering and Sorting

Use the controls at the top to:
- **Search** - Find spools by ID, brand, color, or material
- **Sort** - Order by spool ID, material, brand, color, or remaining weight
- **Low Stock Only** - Toggle to show only spools below their reorder point

---

## Adding a New Spool

1. Click the **+ Add Spool** button
2. Fill in the spool details:

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Spool ID** | Auto-generated (e.g., FIL-042) or custom | Yes |
| **Material Type** | Select from dropdown (PLA, PETG, ABS, TPU, etc.) | Yes |
| **Brand** | Manufacturer (e.g., Bambu Lab, Polymaker) | Yes |
| **Color** | Color name (e.g., "Matte Black") | Yes |
| **Color Hex** | Optional hex code for accurate display | No |
| **Finish** | Matte, Glossy, Silk, etc. | No |

### Weight Information

| Field | Description | Required |
|-------|-------------|----------|
| **Initial Weight** | Weight when new (typically 1000g) | Yes |
| **Current Weight** | Actual weight now (weigh your spool!) | Yes |
| **Spool Weight** | Weight of empty spool (for calculations) | No |

### Print Settings

| Field | Description | Required |
|-------|-------------|----------|
| **Diameter** | Filament diameter (1.75mm or 2.85mm) | Yes |
| **Density** | Material density for volume calculations | No |
| **Extruder Temp** | Recommended nozzle temperature | No |
| **Bed Temp** | Recommended bed temperature | No |

### Cost Information

| Field | Description | Required |
|-------|-------------|----------|
| **Cost** | Purchase price | No |
| **Supplier** | Where you bought it | No |
| **Purchase Date** | When purchased | No |

### Stock Management

| Field | Description | Required |
|-------|-------------|----------|
| **Reorder Point** | Weight at which to reorder | No |
| **Location** | Storage location (e.g., "Shelf A-3") | No |
| **Notes** | Any additional notes | No |

3. Click **Add Spool** to save

---

## SpoolmanDB Integration

Nozzly integrates with [SpoolmanDB](https://github.com/Donkie/SpoolmanDB), a community database of filament specifications.

### Using SpoolmanDB

1. When adding a spool, click **Import from SpoolmanDB**
2. Search for your filament by brand and color
3. Select the matching entry
4. SpoolmanDB data auto-fills:
   - Material type
   - Brand
   - Color (with hex code)
   - Print temperatures
   - Density

This saves time and ensures accurate specifications.

---

## Updating Spool Weight

After each print or production run, update your spool weights for accurate inventory.

### Quick Weight Update

1. Find the spool in your inventory
2. Click the **Scale** icon (or **Update Weight** button)
3. Enter the new current weight
4. Optionally add a note about why (e.g., "After print run #42")
5. Click **Update**

### Weight Update from Production Runs

When you complete a production run, Nozzly automatically offers to update spool weights based on actual material consumption. This is the most accurate method.

### Tips for Accurate Weighing

- Use a digital kitchen scale (0.1g precision is ideal)
- Weigh the spool with filament loaded (subtract spool weight)
- Update immediately after each print session
- Consider weighing weekly at minimum

---

## Viewing Spool Details

Click on any spool to view its full details:

- Complete specifications
- Purchase history
- Usage history (linked production runs)
- QR code for quick access
- Weight history graph

---

## Editing a Spool

1. Click on the spool to view details
2. Click **Edit**
3. Modify any fields
4. Click **Save**

---

## Duplicating a Spool

When you buy the same filament again:

1. Find the original spool
2. Click the **Copy** icon
3. A new spool is created with the same specs
4. The new spool opens in edit mode
5. Update the weight and any other details
6. Save

This saves time when restocking with identical spools.

---

## Deleting a Spool

1. Click on the spool to view details
2. Click **Delete**
3. Confirm deletion

**Warning**: Deleting a spool is permanent. If the spool has been used in production runs, those records remain but won't link back to the spool.

---

## Low Stock Alerts

### Setting Reorder Points

For each spool, set a reorder point (e.g., 200g). When the current weight drops below this:

- The spool appears in the Dashboard's **Low Stock Alerts**
- The spool is flagged in the inventory list

### Viewing Low Stock

1. Go to **Dashboard** - see the Low Stock Alerts card
2. Or go to **Inventory** and toggle **Low Stock Only**

---

## QR Code Labels

Each spool can have a QR code for quick identification and weight updates.

### Generating QR Codes

1. View the spool details
2. Click **QR Code**
3. Print the label for your spool

### Using QR Codes

Scan a spool's QR code to:
- Jump directly to that spool's page
- Quickly update the weight
- View usage history

*Note: Full QR scanning feature requires PWA installation with camera access.*

---

## Material Types

Nozzly comes with standard material types pre-configured:

| Material | Description |
|----------|-------------|
| **PLA** | Polylactic Acid - easy to print, biodegradable |
| **PETG** | Polyethylene Terephthalate Glycol - strong, flexible |
| **ABS** | Acrylonitrile Butadiene Styrene - durable, heat resistant |
| **TPU** | Thermoplastic Polyurethane - flexible, rubber-like |
| **ASA** | Acrylonitrile Styrene Acrylate - UV resistant |
| **Nylon** | Polyamide - strong, wear resistant |
| **PC** | Polycarbonate - extremely strong |
| **HIPS** | High Impact Polystyrene - support material |
| **PVA** | Polyvinyl Alcohol - water-soluble support |

Custom material types can be added as needed.

---

## Best Practices

### Organization
- Use consistent naming for brands and colors
- Set meaningful storage locations
- Group similar materials together

### Accuracy
- Always weigh spools when adding (don't trust "1kg" labels)
- Update weights after every production run
- Account for spool weight in calculations

### Planning
- Set reorder points based on usage patterns
- Check low stock alerts before starting large runs
- Keep backup spools of frequently used colors

### Cost Tracking
- Record purchase prices accurately
- Include shipping in cost if significant
- Note suppliers for reorder reference

---

*Next: [Products](products.md) - Create sellable products from your prints*
