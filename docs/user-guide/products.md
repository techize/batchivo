# Products

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

### Product Types

**Simple Product**
A single item, usually one model with optional components.
- Example: A printed phone stand

**Bundle**
Multiple products sold together.
- Example: "Starter Pack" containing 3 different items

---

## Product List View

The products page shows all your items with:

- **Name** - Product title
- **SKU** - Stock keeping unit (e.g., PRD-001)
- **Category** - Product category
- **Make Cost** - Total cost to produce
- **Status** - Active/Inactive
- **Image** - Primary product image

### Filtering and Search

- **Search** - Find by name or SKU
- **Category** - Filter by product category
- **Status** - Show active, inactive, or all

---

## Creating a Product

1. Click **+ Add Product**
2. Fill in the basic information:

### Basic Information

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
| **Best Channel** | Sales channel with highest margin |

### Suggested Pricing

Batchivo calculates suggested retail prices:

| Method | Formula | Use Case |
|--------|---------|----------|
| **2.5x Markup** | Cost × 2.5 | Standard craft pricing |
| **40% Margin** | Cost ÷ 0.60 | Target profit margin |
| **3x Premium** | Cost × 3.0 | Premium/specialty items |

---

## Adding Models to a Product

Models are the 3D prints that make up your product.

1. In the product detail page, find the **Models** section
2. Click **+ Add Model**
3. Select a model from your catalog
4. Set the quantity (how many of this model per product)
5. Click **Add**

### Model Cost Calculation

Each model contributes to the product cost based on:
- Material cost (filament used × price per gram)
- Time cost (print time × hourly rate, if configured)
- Failure rate allowance

---

## Adding Components

Components are non-printed parts included with your product.

1. Find the **Components** section
2. Click **+ Add Component**
3. Enter component details:

| Field | Description |
|-------|-------------|
| **Name** | Component name (e.g., "6x3mm Magnets") |
| **Quantity** | How many per product |
| **Unit Cost** | Cost per piece |

### Common Components

- Magnets (various sizes)
- Heat-set inserts
- Screws and hardware
- Rubber feet
- LED lights
- Batteries

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

### Image Tips

- Use good lighting for product photos
- Show the product from multiple angles
- Include scale reference if helpful
- Compress large images before upload

---

## Pricing Per Channel

Set different prices for each sales channel.

1. Find the **Pricing** section
2. For each sales channel:

| Field | Description |
|-------|-------------|
| **List Price** | Your asking price |
| **Sale Price** | Optional discounted price |
| **Active** | Whether to show on this channel |

### Automatic Calculations

When you set a price, Batchivo calculates:

| Metric | Description |
|--------|-------------|
| **Platform Fees** | Marketplace fees (e.g., Etsy 6.5%) |
| **Payment Fees** | Processing fees (e.g., 3% + $0.25) |
| **Net Revenue** | What you actually receive |
| **Profit** | Net revenue minus make cost |
| **Margin %** | Profit as percentage of revenue |

### Comparing Channels

The pricing table lets you compare profitability across channels:

| Channel | List Price | Fees | Net | Profit | Margin |
|---------|------------|------|-----|--------|--------|
| Etsy | $25.00 | $3.50 | $21.50 | $11.50 | 53% |
| Website | $24.00 | $1.00 | $23.00 | $13.00 | 57% |
| Market | $22.00 | $0.00 | $22.00 | $12.00 | 55% |

---

## Creating Bundles

Bundles combine multiple products into a package deal.

1. Create a new product for the bundle
2. In the **Child Products** section, add existing products
3. Set bundle pricing (usually discounted vs. buying separately)

### Bundle Cost Calculation

Bundle cost = Sum of all included product costs

---

## Editing Products

1. Go to the product detail page
2. Click **Edit** in the header
3. Modify any basic fields
4. Click **Save**

To modify models, components, or pricing, use the inline editors in each section.

---

## Deleting Products

1. Go to the product detail page
2. Click **Delete**
3. Confirm deletion

**Warning**: Deleting a product removes it from your catalog. Historical orders referencing this product retain their data.

---

## Categories

Organize products into categories for easier management.

### Managing Categories

1. Go to **Categories** in the navigation
2. View, add, edit, or delete categories

### Using Categories

- Filter products by category
- Organize your shop display
- Generate category-based reports

---

## Designers

Track original designers for licensed STL files.

### Why Track Designers?

- Attribution and licensing compliance
- Royalty tracking (if applicable)
- Link products to their creators
- Support the design community

### Managing Designers

1. Go to **Designers** in the navigation
2. Add designers with:
   - Name
   - Website/social links
   - Notes

### Linking Products to Designers

When creating or editing a product, select the designer from the dropdown.

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
| **Child Products** | Costs of bundled products |

### Formula

```
Total Make Cost = Models + Components + Packaging + Assembly + Child Products
```

### Improving Accuracy

- Keep spool weights updated for accurate material costs
- Track failed prints in production runs
- Include ALL components (even cheap ones add up)
- Don't forget packaging costs

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

### Organization
- Use categories consistently
- Keep SKUs organized
- Archive inactive products instead of deleting

### Cost Management
- Review model costs when material prices change
- Bulk-purchase components for better pricing
- Track actual vs. estimated costs via production runs

---

*Next: [Production Runs](production-runs.md) - Track your print jobs*
