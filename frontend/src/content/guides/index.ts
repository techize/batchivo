/**
 * User Guide Content
 *
 * All guide content in one place for easy maintenance.
 * Each guide is exported as a raw string for markdown rendering.
 */

export interface Guide {
  slug: string
  title: string
  description: string
  category: 'core' | 'sales' | 'resources' | 'organization'
  order: number
  content: string
}

export const guides: Guide[] = [
  {
    slug: 'overview',
    title: 'Overview',
    description: 'Introduction to Nozzly, key concepts, and navigation',
    category: 'core',
    order: 1,
    content: `# Nozzly User Guide - Overview

Welcome to Nozzly, a comprehensive 3D print business management platform designed to help you track inventory, manage production, and grow your 3D printing business.

---

## What is Nozzly?

Nozzly is an all-in-one solution for 3D printing businesses that need to:

- **Track filament inventory** - Know exactly what materials you have, how much is left, and when to reorder
- **Manage product catalog** - Create products with accurate cost calculations based on materials and components
- **Run production** - Track print jobs, material usage, and production efficiency
- **Process orders** - Handle customer orders with inventory integration
- **Analyze costs** - Understand your true costs and optimize pricing

---

## Key Concepts

### Filament Spools (Inventory)
Your raw materials - the filament you use to print. Each spool is tracked with:
- Material type (PLA, PETG, ABS, TPU, etc.)
- Color, brand, and manufacturer
- Weight remaining (updated after each print)
- Purchase cost for accurate costing

### Models
3D model files that you print. Models define:
- Material requirements (Bill of Materials)
- Print settings (time, weight estimates)
- Multi-plate configurations for batch printing

### Products
Sellable items in your catalog. Products can:
- Be linked to one or more models (prints)
- Include additional components (magnets, inserts)
- Have pricing configured per sales channel
- Calculate costs automatically based on materials + labor + components

### Designers
Track the original designers of STL files you print under license. Useful for:
- Attribution and licensing compliance
- Linking products to their original creators
- Managing designer royalties or credits

### Production Runs
A batch printing session. Production runs track:
- Which products/models you're printing
- Materials consumed (actual vs estimated)
- Time spent and success rate
- Variance analysis for cost accuracy

### Sales Channels
Where you sell (Etsy, eBay, local markets, website). Each channel has:
- Fee structures (percentage, fixed fees)
- Pricing overrides per product
- Order tracking

### Orders
Customer purchases that flow through:
- Pending → Confirmed → Printing → Shipped → Delivered

### Consumables
Non-filament supplies: nozzles, build plates, lubricants, cleaning supplies. Track usage and costs.

### Printers
Your 3D printers. Track:
- Printer specifications
- Usage and maintenance
- Assignment to production runs

---

## Navigation

Nozzly's interface is organized into logical sections accessible from the top navigation bar:

### Dashboard
Your home base showing:
- Quick statistics (inventory value, pending orders, active runs)
- Low stock alerts
- Active production runs
- Quick action buttons

### Catalog Section

| Page | Purpose |
|------|---------|
| **Products** | Manage sellable items with pricing and costs |
| **Models** | 3D model files with material requirements |
| **Designers** | Original creators for licensed STLs |
| **Categories** | Organize products into categories |

### Operations Section

| Page | Purpose |
|------|---------|
| **Runs** | Create and track production runs |
| **Inventory** | Manage filament spools |

### Resources Section

| Page | Purpose |
|------|---------|
| **Printers** | Your 3D printer fleet |
| **Consumables** | Track non-filament supplies |

### Sales Section

| Page | Purpose |
|------|---------|
| **Channels** | Sales platforms (Etsy, eBay, etc.) |
| **Orders** | Customer order processing |

---

## Getting Started

### First Time Setup

1. **Add your printers** - Go to Printers and add your 3D printers
2. **Add filament inventory** - Go to Inventory and add your current spools
3. **Create models** - Add your 3D models with material requirements
4. **Create products** - Build sellable products from your models
5. **Set up sales channels** - Configure where you sell
6. **Start a production run** - Begin tracking your prints!

### Typical Daily Workflow

1. **Check Dashboard** - Review low stock alerts and pending orders
2. **Create Production Run** - Start a batch print session
3. **Complete Run** - Log actual material usage when prints finish
4. **Process Orders** - Ship completed orders
5. **Update Inventory** - Weigh spools if needed

---

## Tips for Success

### Accurate Costing
- Always update spool weights after production runs
- Include all components in product costs (magnets, packaging, etc.)
- Factor in failed prints using variance tracking

### Inventory Management
- Set reorder points for frequently used materials
- Use low stock alerts to avoid running out
- Track material by manufacturer for quality consistency

### Production Efficiency
- Use multi-plate runs for batch printing
- Review variance reports to improve estimates
- Track time spent for accurate labor costing
`,
  },
  {
    slug: 'filament-management',
    title: 'Filament Management',
    description: 'Managing filament spools and inventory',
    category: 'core',
    order: 2,
    content: `# Filament Management

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

3. Click **Add Spool** to save

---

## SpoolmanDB Integration

Nozzly integrates with SpoolmanDB, a community database of filament specifications.

### Using SpoolmanDB

1. When adding a spool, click **Import from SpoolmanDB**
2. Search for your filament by brand and color
3. Select the matching entry
4. SpoolmanDB data auto-fills material type, brand, color, and print temperatures

---

## Updating Spool Weight

After each print or production run, update your spool weights for accurate inventory.

### Quick Weight Update

1. Find the spool in your inventory
2. Click the **Scale** icon (or **Update Weight** button)
3. Enter the new current weight
4. Click **Update**

### Tips for Accurate Weighing

- Use a digital kitchen scale (0.1g precision is ideal)
- Weigh the spool with filament loaded (subtract spool weight)
- Update immediately after each print session

---

## Low Stock Alerts

### Setting Reorder Points

For each spool, set a reorder point (e.g., 200g). When the current weight drops below this:
- The spool appears in the Dashboard's **Low Stock Alerts**
- The spool is flagged in the inventory list

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
`,
  },
  {
    slug: 'products',
    title: 'Products',
    description: 'Creating products, pricing, and cost management',
    category: 'core',
    order: 3,
    content: `# Products

Products are the sellable items in your catalog. A product combines models (3D prints), components (hardware like magnets), packaging, and pricing to create something you can sell to customers.

---

## Accessing Products

Click **Products** in the top navigation bar to view your product catalog.

---

## Product Concepts

### Products vs Models

| Concept | Description | Example |
|---------|-------------|---------|
| **Model** | A 3D file you print | "Dragon Miniature STL" |
| **Product** | A sellable item | "Painted Dragon Miniature" |

A product can include:
- One or more models (prints)
- Additional components (magnets, inserts)
- Packaging costs
- Assembly labor

---

## Creating a Product

1. Click **+ Add Product**
2. Fill in the basic information:

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Product title for your catalog | Yes |
| **SKU** | Auto-generated or custom identifier | Yes |
| **Description** | Detailed product description | No |
| **Category** | Select from your categories | No |
| **Designer** | Original STL designer (for licensed files) | No |
| **Active** | Whether product is available for sale | Yes |

3. Click **Create Product**

---

## Product Detail Page

After creating a product, the detail page lets you configure:

### Cost Summary

At the top, you'll see key metrics:

| Metric | Description |
|--------|-------------|
| **Total Make Cost** | Sum of all costs to produce |
| **Models Cost** | Material + time for prints |
| **Components Cost** | Hardware and parts |
| **Packaging Cost** | Boxes, bags, labels |

---

## Adding Models to a Product

Models are the 3D prints that make up your product.

1. In the product detail page, find the **Models** section
2. Click **+ Add Model**
3. Select a model from your catalog
4. Set the quantity (how many of this model per product)
5. Click **Add**

---

## Adding Components

Components are non-printed parts included with your product.

1. Find the **Components** section
2. Click **+ Add Component**
3. Enter component details:
   - Name (e.g., "6x3mm Magnets")
   - Quantity per product
   - Unit cost

---

## Product Images

Add photos to display your products.

1. Find the **Images** section
2. Click the upload area or drag and drop images
3. Supported formats: JPEG, PNG, WebP (max 10MB)

### Managing Images

- **Set Primary** - Click the star to make an image the main display
- **Rotate** - Click rotate to adjust orientation
- **Preview** - Click the eye icon to see full-size
- **Delete** - Remove unwanted images

---

## Pricing Per Channel

Set different prices for each sales channel.

1. Find the **Pricing** section
2. For each sales channel, set:
   - **List Price** - Your asking price
   - **Sale Price** - Optional discounted price
   - **Active** - Whether to show on this channel

### Automatic Calculations

When you set a price, Nozzly calculates:
- **Platform Fees** - Marketplace fees (e.g., Etsy 6.5%)
- **Payment Fees** - Processing fees
- **Net Revenue** - What you actually receive
- **Profit** - Net revenue minus make cost
- **Margin %** - Profit as percentage of revenue

---

## Cost Breakdown

Understanding your true costs is essential for profitable pricing.

### Cost Components

| Component | Source |
|-----------|--------|
| **Models Cost** | Sum of all model costs (materials + time) |
| **Components Cost** | Sum of all component costs |
| **Packaging Cost** | Packaging materials |
| **Assembly Cost** | Labor to assemble (if set) |

### Formula

\`\`\`
Total Make Cost = Models + Components + Packaging + Assembly
\`\`\`

---

## Best Practices

### Product Setup
- Use clear, descriptive names
- Always calculate accurate costs before pricing
- Include all components, even small ones
- Add quality product images

### Pricing Strategy
- Know your minimum viable price (break-even)
- Compare margins across channels
- Factor in returns and replacements
- Review and adjust prices regularly
`,
  },
  {
    slug: 'production-runs',
    title: 'Production Runs',
    description: 'Tracking print jobs and material usage',
    category: 'core',
    order: 4,
    content: `# Production Runs

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

## Creating a Production Run

Use the step-by-step wizard to create a run:

### Step 1: Basic Information

| Field | Description |
|-------|-------------|
| **Printer** | Select the printer you're using |
| **Slicer** | Software used (PrusaSlicer, Cura, etc.) |
| **Estimated Print Time** | Hours from slicer |
| **Estimated Weights** | Material estimates |

### Step 2: Models

Select the models you're printing:
1. Click **+ Add Model**
2. Select a model from your catalog
3. Enter the quantity being printed

### Step 3: Materials

Assign the filament spools:
1. Click **+ Add Material**
2. Select a spool from your inventory
3. Enter the estimated weight to be used

### Step 4: Review

Review all details and click **Create Run**.

---

## Run Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Created but not started |
| **In Progress** | Currently printing |
| **Completed** | Successfully finished |
| **Failed** | Print failed |
| **Cancelled** | Run was cancelled |

---

## Completing a Run

When your print finishes:

1. Go to the run detail page
2. Click **Complete Run**
3. Fill in actual results:

### Material Weights

Two entry methods:
- **Manual Entry** - Enter actual weight used
- **Weighing Mode** - Enter before/after spool weights

### Item Results

For each model, enter:
- **Successful** - Number of good prints
- **Failed** - Number of failed prints

4. Click **Complete Run**

This automatically:
- Updates spool weights in inventory
- Calculates variance
- Records success/failure data

---

## Variance Analysis

After completion, Nozzly calculates variance:

\`\`\`
Variance = Actual Weight - Estimated Weight
Variance % = (Variance / Estimated) × 100
\`\`\`

| Variance | Meaning |
|----------|---------|
| **0%** | Perfect estimate |
| **Positive** | Used more than estimated |
| **Negative** | Used less than estimated |

---

## Multi-Color Print Material Tracking

Multi-color prints require special handling because material usage includes both the finished model and waste from color changes.

### Understanding the Split

| Component | Where to Enter | Description |
|-----------|----------------|-------------|
| **Model Weight** | Model BOM (per unit) | Filament that ends up in the finished print |
| **Flush/Purge** | Production Run | Waste from color transitions during print |
| **Tower** | Production Run | Purge tower weight (shared per plate) |

### Model BOM (Bill of Materials)

When setting up a model, enter the filament weight for **one unit only**:
- Only the material that ends up in the finished print
- Each color/material as a separate BOM entry
- Do NOT include purge tower or flush waste

**Example: Multi-color Dragon**
- Body (Blue PLA): 45g per unit
- Wings (Gold PLA): 12g per unit
- Total BOM: 57g per unit

### Production Run Materials

When creating a production run:
1. **Model Weight** - Auto-calculated from BOM × quantity
2. **Flush/Purge** - Enter waste from color changes (check your slicer)
3. **Tower** - Enter purge tower weight (typically 10-20g per plate)

**Example: Printing 4 Dragons**
- Model weight: 57g × 4 = 228g (from BOM)
- Flush/Purge: 8g per color change × 3 colors = 24g
- Tower: 15g (one tower shared by all 4 items)
- **Total: 267g**

### Tips for Multi-Color Printing

- **Tower is per-plate**, not per-item (more items = less waste per unit)
- Check your slicer's purge volume settings for accurate flush estimates
- Different slicers calculate waste differently (Bambu Studio, OrcaSlicer, etc.)
- Update your BOM estimates after a few runs to improve accuracy

---

## Best Practices

### Before Starting
- Record accurate slicer estimates
- Verify spool assignments

### After Printing
- Complete immediately while details are fresh
- Weigh spools for accuracy
- Record all failures
`,
  },
  {
    slug: 'orders',
    title: 'Orders',
    description: 'Processing customer orders and fulfillment',
    category: 'sales',
    order: 5,
    content: `# Orders

Orders represent customer purchases. Nozzly helps you track orders from receipt through fulfillment and delivery.

---

## Accessing Orders

Click **Orders** in the top navigation bar to view all customer orders.

---

## Order Statuses

| Status | Description | Color |
|--------|-------------|-------|
| **Pending** | New order, not yet started | Yellow |
| **Processing** | Being prepared/printed | Blue |
| **Shipped** | Sent to customer | Purple |
| **Delivered** | Customer received | Green |
| **Cancelled** | Order cancelled | Red |
| **Refunded** | Payment refunded | Gray |

---

## Processing an Order

### Shipping an Order

When items are ready to ship:

1. Click **Ship Order**
2. Enter shipping details:
   - **Tracking Number** - Carrier tracking number
   - **Tracking URL** - Link to tracking page
3. Click **Confirm**

### Marking as Delivered

When the customer receives their order:

1. Click **Mark Delivered**
2. Confirm the delivery

---

## Adding Internal Notes

Keep private notes about orders:

1. Click **Add Notes**
2. Enter your internal notes
3. Save

Notes are only visible to you, not customers.

---

## Common Workflows

### New Order Received

1. Review order details
2. Check inventory for required items
3. Create production run if items need printing
4. Ship when ready
5. Mark delivered when confirmed

### Rush Order

1. Prioritize in production queue
2. Add internal note about rush status
3. Ship with expedited method
4. Track delivery closely
`,
  },
  {
    slug: 'sales-channels',
    title: 'Sales Channels',
    description: 'Configuring marketplaces and fee structures',
    category: 'sales',
    order: 6,
    content: `# Sales Channels

Sales channels represent where you sell your products - marketplaces like Etsy and eBay, your own website, or in-person at craft fairs.

---

## Accessing Sales Channels

Click **Channels** in the top navigation bar to manage your sales channels.

---

## Why Configure Channels?

### Accurate Profit Calculations
Each channel has different fees. Nozzly calculates:
- Platform fees (percentage cut)
- Payment processing fees
- Monthly/listing costs

### Price Comparison
See profit margins across all your channels.

---

## Creating a Sales Channel

1. Click **+ Add Channel**
2. Fill in the channel details:

### Platform Types

| Type | Description |
|------|-------------|
| **Etsy** | Etsy marketplace |
| **eBay** | eBay marketplace |
| **Amazon** | Amazon marketplace |
| **Shopify** | Shopify store |
| **Online Shop** | Your own website |
| **Fair** | Craft fairs, markets, pop-ups |
| **Other** | Any other sales channel |

### Fee Configuration

| Field | Description | Example |
|-------|-------------|---------|
| **Fee Percentage** | Platform's percentage cut | 6.5% for Etsy |
| **Fee Fixed** | Fixed fee per transaction | £0.20 listing fee |
| **Monthly Cost** | Subscription or booth rental | £25/month |

---

## Common Channel Configurations

### Etsy
- Fee Percentage: 6.5%
- Fee Fixed: £0.20
- Monthly Cost: £0 (or Plus subscription)

### eBay
- Fee Percentage: 12.8%
- Fee Fixed: £0.30

### Craft Fair
- Fee Percentage: 0%
- Monthly Cost: £50-200 (booth fee)

### Own Website
- Fee Percentage: 2.9% (payment processor)
- Fee Fixed: £0.20

---

## How Fees Are Calculated

\`\`\`
Gross Revenue = List Price
Platform Fees = (Price × Fee%) + Fixed Fee
Net Revenue = Gross - Platform Fees
Profit = Net Revenue - Make Cost
Margin % = (Profit / Net Revenue) × 100
\`\`\`
`,
  },
  {
    slug: 'printers',
    title: 'Printers',
    description: 'Managing your 3D printer fleet',
    category: 'resources',
    order: 7,
    content: `# Printers

Track your 3D printer fleet in Nozzly. Recording printer details helps with production run tracking and maintenance planning.

---

## Accessing Printers

Click **Printers** in the top navigation bar to view your printer fleet.

---

## Adding a Printer

1. Click **+ Add Printer**
2. Fill in the printer details:

### Basic Information

| Field | Description |
|-------|-------------|
| **Name** | Your name for this printer |
| **Manufacturer** | Brand name |
| **Model** | Model number/name |
| **Serial Number** | For warranty/tracking |

### Build Volume

| Field | Description |
|-------|-------------|
| **Bed Size X** | Width in mm |
| **Bed Size Y** | Depth in mm |
| **Bed Size Z** | Height in mm |

### Print Settings

| Field | Description |
|-------|-------------|
| **Nozzle Diameter** | Default nozzle size (mm) |
| **Default Bed Temp** | Typical bed temperature |
| **Default Nozzle Temp** | Typical hotend temperature |

---

## Common Printer Configurations

### Bambu Lab X1 Carbon
- Bed Size: 256 × 256 × 256 mm
- Nozzle: 0.4 mm

### Prusa MK4
- Bed Size: 250 × 210 × 220 mm
- Nozzle: 0.4 mm

---

## Maintenance Tracking

Use the Notes field to track:
- Last maintenance date
- Nozzle changes
- Belt tensions
- Firmware versions

---

## Best Practices

### Naming Convention
Use consistent, clear names:
- "Bambu X1 - Primary"
- "Prusa MK4 - #2"
`,
  },
  {
    slug: 'consumables',
    title: 'Consumables',
    description: 'Tracking non-filament supplies',
    category: 'resources',
    order: 8,
    content: `# Consumables

Consumables are non-filament supplies used in your 3D printing business: magnets, heat-set inserts, screws, packaging materials, and more.

---

## Accessing Consumables

Click **Consumables** in the top navigation bar to manage your supplies inventory.

---

## Why Track Consumables?

### Accurate Product Costs
Products often include hardware that adds to costs:
- A phone stand needs rubber feet
- A magnetic box needs magnets
- A kit needs custom packaging

### Inventory Management
Avoid running out of essential supplies with low stock alerts.

---

## Adding a Consumable

1. Click **+ Add Consumable**
2. Fill in the details:

### Categories

| Category | Examples |
|----------|----------|
| **Magnets** | Neodymium magnets (various sizes) |
| **Inserts** | Heat-set inserts, threaded inserts |
| **Hardware** | Screws, nuts, bolts, washers |
| **Finishing** | Sandpaper, paint, primer |
| **Packaging** | Boxes, bags, labels |
| **Adhesives** | Super glue, epoxy, tape |

### Units of Measure

| Unit | Use For |
|------|---------|
| **each** | Individual items (magnets, inserts) |
| **pack** | Pre-packaged quantities |
| **g** | Grams (adhesives, powders) |
| **ml** | Milliliters (liquids) |

---

## Recording Purchases

Track consumable purchases:

1. Go to the consumable detail page
2. Click **Add Purchase**
3. Enter: Quantity, Total Cost, Supplier, Date

---

## Low Stock Alerts

Set reorder points for each consumable. When stock drops below:
- Warning badge appears in the list
- Item shows in Dashboard alerts

---

## Best Practices

### SKU Conventions
- \`MAG-\` for magnets
- \`INS-\` for inserts
- Include size: \`MAG-6X3\` (6mm × 3mm)

### Cost Accuracy
- Record all purchases
- Include shipping in total cost
`,
  },
  {
    slug: 'designers',
    title: 'Designers',
    description: 'Tracking STL designers and licensing',
    category: 'organization',
    order: 9,
    content: `# Designers

Designers are the original creators of STL files you print under license. Tracking designers helps with attribution and licensing compliance.

---

## Accessing Designers

Click **Designers** in the top navigation bar to manage your designer database.

---

## Why Track Designers?

### Licensing Compliance
Many STL files are sold with commercial licenses:
- Track which products use which designer's work
- Document licensing arrangements

### Membership Management
Many designers offer subscription services:
- Track membership costs
- Monitor renewal dates

### Attribution
Give credit where it's due:
- Link products to creators
- Support the design community

---

## Adding a Designer

1. Click **+ Add Designer**
2. Fill in the designer details:

| Field | Description |
|-------|-------------|
| **Name** | Designer or studio name |
| **Website URL** | Main website |
| **Social Links** | Patreon, MyMiniFactory, etc. |
| **Membership Cost** | Monthly/yearly cost |
| **Renewal Date** | When next payment due |

---

## Linking Products to Designers

When creating or editing a product:
1. Select the designer from dropdown
2. Save

---

## Popular Designer Platforms

### Patreon
Many designers offer STL files through Patreon tiers.

### MyMiniFactory Tribes
Subscription-based access to designer catalogs.

---

## Best Practices

- Add designers when you first use their work
- Keep renewal dates accurate
- Note license terms in Notes field
`,
  },
  {
    slug: 'categories',
    title: 'Categories',
    description: 'Organizing products into categories',
    category: 'organization',
    order: 10,
    content: `# Categories

Categories help organize your products into logical groups for easier management and customer browsing.

---

## Accessing Categories

Click **Categories** in the top navigation bar to manage product categories.

---

## Creating a Category

1. Click **+ Add Category**
2. Fill in the category details:

| Field | Description |
|-------|-------------|
| **Name** | Category name |
| **Slug** | URL identifier (auto-generated) |
| **Description** | Category description |
| **Image URL** | Category banner/image |
| **Display Order** | Sort order (lower = first) |
| **Parent Category** | For hierarchy |

---

## Hierarchical Categories

Categories can be nested:

\`\`\`
Gaming Accessories
├── Dice Towers
├── Card Holders
└── Miniature Storage

Home & Office
├── Desk Organizers
└── Phone Stands
\`\`\`

---

## Display Order

Control how categories appear:
- Lower numbers appear first
- Same number sorts alphabetically

---

## Example Categories for 3D Print Business

### By Product Type
- Miniatures
- Terrain
- Functional Prints
- Art & Decor

### By Use Case
- Gaming
- Home Office
- Kitchen

### By Theme
- Fantasy
- Sci-Fi
- Modern

---

## Best Practices

### Naming
- Use clear, customer-friendly names
- Keep names concise

### Structure
- Match your customers' mental model
- Don't create empty categories
- Keep depth to 2-3 levels maximum
`,
  },
]

export const guidesByCategory = {
  core: guides.filter(g => g.category === 'core').sort((a, b) => a.order - b.order),
  sales: guides.filter(g => g.category === 'sales').sort((a, b) => a.order - b.order),
  resources: guides.filter(g => g.category === 'resources').sort((a, b) => a.order - b.order),
  organization: guides.filter(g => g.category === 'organization').sort((a, b) => a.order - b.order),
}

export function getGuideBySlug(slug: string): Guide | undefined {
  return guides.find(g => g.slug === slug)
}
