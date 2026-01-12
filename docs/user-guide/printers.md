# Printers

Track your 3D printer fleet in Batchivo. Recording printer details helps with production run tracking, maintenance planning, and understanding your capacity.

---

## Accessing Printers

Click **Printers** in the top navigation bar to view your printer fleet.

---

## Printer List View

The printers page displays all your printers with:

| Column | Description |
|--------|-------------|
| **Name** | Printer name/nickname |
| **Manufacturer** | Brand (Bambu Lab, Prusa, etc.) |
| **Model** | Printer model |
| **Bed Size** | Print volume |
| **Nozzle** | Nozzle diameter |
| **Status** | Active/Inactive |

---

## Adding a Printer

1. Click **+ Add Printer**
2. Fill in the printer details:

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Your name for this printer | Yes |
| **Manufacturer** | Brand name | No |
| **Model** | Model number/name | No |
| **Serial Number** | For warranty/tracking | No |
| **Active** | Currently in use | Yes |

### Build Volume

| Field | Description | Required |
|-------|-------------|----------|
| **Bed Size X** | Width in mm | No |
| **Bed Size Y** | Depth in mm | No |
| **Bed Size Z** | Height in mm | No |

### Print Settings

| Field | Description | Required |
|-------|-------------|----------|
| **Nozzle Diameter** | Default nozzle size (mm) | No |
| **Default Bed Temp** | Typical bed temperature | No |
| **Default Nozzle Temp** | Typical hotend temperature | No |

### Notes

Add any additional notes about the printer:
- Maintenance history
- Special configurations
- Known quirks

3. Click **Add Printer**

---

## Common Printer Configurations

### Bambu Lab X1 Carbon
| Setting | Value |
|---------|-------|
| Manufacturer | Bambu Lab |
| Model | X1 Carbon |
| Bed Size | 256 × 256 × 256 mm |
| Nozzle | 0.4 mm |

### Bambu Lab P1S
| Setting | Value |
|---------|-------|
| Manufacturer | Bambu Lab |
| Model | P1S |
| Bed Size | 256 × 256 × 256 mm |
| Nozzle | 0.4 mm |

### Prusa MK4
| Setting | Value |
|---------|-------|
| Manufacturer | Prusa Research |
| Model | MK4 |
| Bed Size | 250 × 210 × 220 mm |
| Nozzle | 0.4 mm |

### Creality Ender 3
| Setting | Value |
|---------|-------|
| Manufacturer | Creality |
| Model | Ender 3 V2 |
| Bed Size | 220 × 220 × 250 mm |
| Nozzle | 0.4 mm |

---

## Editing a Printer

1. Click on the printer in the list
2. Click **Edit**
3. Modify details
4. Click **Save**

---

## Deactivating a Printer

If a printer is temporarily offline or retired:

1. Edit the printer
2. Toggle **Active** to off
3. Save

Deactivated printers:
- Don't appear in production run printer selection
- Keep historical data intact
- Can be reactivated anytime

---

## Deleting a Printer

1. Click on the printer
2. Click **Delete**
3. Confirm deletion

**Warning**: Deleting a printer removes it permanently. Historical production runs keep their printer reference as text.

---

## Using Printers in Production Runs

### Selecting a Printer

When creating a production run:
1. Select the printer from the dropdown
2. Default temperatures pre-fill from printer settings

### Printer-Specific Analysis

Track which printers:
- Have higher success rates
- Use more/less material than estimates
- Handle specific materials better

---

## Multiple Nozzle Sizes

If you swap nozzles frequently:

### Option 1: Update Printer
Edit the printer's nozzle diameter when you swap.

### Option 2: Multiple Entries
Create separate printer entries:
- "X1 Carbon - 0.4mm"
- "X1 Carbon - 0.6mm"

---

## Maintenance Tracking

Use the Notes field to track:
- Last maintenance date
- Nozzle changes
- Belt tensions
- Firmware versions
- Issues encountered

### Example Notes
```
2025-01-15: Replaced nozzle, cleaned hotend
2025-02-01: Tensioned X belt
2025-02-15: Updated to firmware v1.8.0
```

---

## Best Practices

### Naming Convention
Use consistent, clear names:
- "Bambu X1 - Primary"
- "Prusa MK4 - #2"
- "Ender 3 - Prototypes"

### Keep Details Current
- Update nozzle size when changed
- Mark inactive when down for maintenance
- Note any modifications

### Production Planning
- Know each printer's capabilities
- Match prints to appropriate printers
- Track utilization across fleet

---

*Next: [Consumables](consumables.md) - Track non-filament supplies*
