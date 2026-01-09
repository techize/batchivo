# Production Runs

Production runs track your actual print jobs. By logging what you print and the materials consumed, you gain accurate cost data and can identify efficiency improvements.

---

## Accessing Production Runs

Click **Runs** in the top navigation bar to view all production runs.

---

## Why Track Production Runs?

### Accurate Costing
- Compare estimated vs actual material usage
- Track failed prints and waste
- Calculate true cost per item

### Efficiency Analysis
- Monitor print success rates
- Identify problematic models
- Optimize printer utilization

### Inventory Management
- Automatic spool weight deduction
- Accurate remaining inventory
- Better reorder planning

---

## Production Run List

The runs page shows all your print jobs with:

| Column | Description |
|--------|-------------|
| **Run ID** | Unique identifier (e.g., RUN-042) |
| **Status** | Pending, In Progress, Completed, Failed |
| **Printer** | Which printer was used |
| **Items** | Models being printed |
| **Started** | When the print began |
| **Duration** | Print time |

### Filtering

- **Status** - Filter by run status
- **Date Range** - Show runs within a period
- **Printer** - Filter by printer

---

## Creating a Production Run

Use the step-by-step wizard to create a run:

### Step 1: Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Printer** | Select the printer you're using | Yes |
| **Slicer** | Software used (PrusaSlicer, Cura, etc.) | No |
| **Bed Temperature** | Heated bed temp | No |
| **Nozzle Temperature** | Hotend temp | No |
| **Estimated Print Time** | Hours from slicer | No |
| **Estimated Weights** | Material estimates (see below) | No |
| **Notes** | Any additional notes | No |

#### Weight Estimates

For accurate tracking, enter weight estimates from your slicer:

| Field | Description |
|-------|-------------|
| **Model Weight** | Actual material in the print |
| **Flushed Weight** | Purge/flush material (multi-color) |
| **Tower Weight** | Prime tower material (multi-color) |

For single-color prints, only Model Weight is needed.

### Step 2: Models

Select the models you're printing in this run:

1. Click **+ Add Model**
2. Select a model from your catalog
3. Enter the quantity being printed
4. Repeat for each model in the run

The wizard shows estimated weights and costs as you add models.

### Step 3: Materials

Assign the filament spools you're using:

1. Click **+ Add Material**
2. Select a spool from your inventory
3. Enter the estimated weight to be used
4. Repeat for each spool (multi-color prints use multiple spools)

The wizard warns if a spool doesn't have enough material.

### Step 4: Review

Review all details before creating:

- Total estimated material
- Total estimated cost
- Models and quantities
- Spools assigned

Click **Create Run** to start tracking.

---

## Production Run Detail Page

After creation, the run detail page shows:

### Status Card
- Current status with visual indicator
- Quick action buttons (Start, Complete, Fail)

### Overview
- Printer and slicer info
- Estimated vs actual times
- Material summary

### Items
- List of models being printed
- Quantity per model
- Success/failure counts (after completion)

### Materials
- Spools assigned
- Estimated vs actual weights
- Variance calculations

---

## Run Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Created but not started |
| **In Progress** | Currently printing |
| **Completed** | Successfully finished |
| **Failed** | Print failed (partial or complete) |
| **Cancelled** | Run was cancelled |

### Status Transitions

```
Pending → In Progress → Completed
                     → Failed
        → Cancelled
```

---

## Starting a Run

1. Go to the run detail page
2. Click **Start Run**
3. The status changes to "In Progress"
4. Start time is recorded

You can also edit the start time if you forgot to click Start:
1. When completing, expand the timing section
2. Set the actual start time

---

## Completing a Run

When your print finishes, complete the run to record actual results:

1. Go to the run detail page
2. Click **Complete Run**
3. Fill in the completion form:

### Material Weights

Two entry methods are available:

#### Manual Entry
Enter the actual weight used for each material:
- Good for when you know exact consumption
- Quick if slicer estimates are accurate

#### Weighing Mode
Enter before and after spool weights:
1. Enter weight before print
2. Enter weight after print
3. System calculates consumption

This is more accurate but requires weighing spools.

### Item Results

For each model, enter:

| Field | Description |
|-------|-------------|
| **Successful** | Number of good prints |
| **Failed** | Number of failed prints |

The total should equal the planned quantity.

### Duration

Enter or adjust the actual print duration.

### Submit

Click **Complete Run** to finalize. This:
- Updates spool weights in inventory
- Calculates variance
- Records success/failure data

---

## Failed Runs

If a print fails completely:

1. Go to the run detail page
2. Click **Mark as Failed**
3. Enter material consumed (even partial prints use material)
4. Add failure notes

Failed runs still track material consumption for accurate cost analysis.

---

## Variance Analysis

After completion, Nozzly calculates variance:

### Material Variance

```
Variance = Actual Weight - Estimated Weight
Variance % = (Variance / Estimated) × 100
```

| Variance | Meaning |
|----------|---------|
| **0%** | Perfect estimate |
| **Positive** | Used more than estimated |
| **Negative** | Used less than estimated |

### Why Variance Matters

- **Consistently high**: Slicer estimates may be wrong
- **Consistently low**: You might be over-allocating
- **Variable**: Print failures, adhesion issues, or settings

### Improving Estimates

1. Review variance after each run
2. Adjust model weight estimates if consistently off
3. Factor in prime tower and flush for multi-color
4. Account for first-layer calibration waste

---

## Multi-Plate Runs

For batch printing multiple items:

### Planning Multi-Plate
- Create a single run for all plates
- Set total quantities across all plates
- Assign all spools used

### Tracking Results
- Record total successful/failed across all plates
- Material consumption is for the entire run

### Example

Printing 12 keychains across 3 plates (4 per plate):
- Quantity: 12
- If one fails on plate 2: Successful=11, Failed=1
- Material = total consumed across all plates

---

## Editing a Run

Before completion, you can edit:

1. Go to the run detail page
2. Click **Edit**
3. Modify details
4. Save changes

After completion, use the **Edit Results** option to correct:
- Material weights
- Success/failure counts
- Duration

---

## Cancelling a Run

If you decide not to proceed:

1. Go to the run detail page
2. Click **Cancel Run**
3. Confirm cancellation

Cancelled runs remain in history but don't affect inventory.

---

## Best Practices

### Before Starting
- Record accurate slicer estimates
- Verify spool assignments match loaded spools
- Note any special settings

### During Printing
- Start the run when print begins
- Monitor for failures

### After Printing
- Complete immediately while details are fresh
- Weigh spools for accuracy
- Record all failures, even small defects

### Analysis
- Review variance regularly
- Update model estimates if consistently wrong
- Track printer-specific success rates

---

## Dashboard Integration

The Dashboard shows:

### Active Production
- Currently in-progress runs
- Quick access to run details

### Quick Actions
- **New Run** button for fast creation

### Analytics
- Production trends (if analytics enabled)
- Success rates over time

---

## Common Workflows

### Single Print
1. Create run with one model, quantity 1
2. Start run
3. Complete with actual weight

### Batch Production
1. Create run with model, quantity = batch size
2. Print all items
3. Complete with total materials and success/fail counts

### Multi-Color Print
1. Create run with model
2. Add all spools used (one per color)
3. Track each spool's consumption separately

### Failed Print Recovery
1. Create new run for reprints
2. Reference original run in notes
3. Track additional material used

---

*Next: [Overview](overview.md) - Return to the system overview*
