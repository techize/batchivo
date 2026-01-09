# Categories

Categories help organize your products into logical groups. Use them to structure your catalog for easier management and customer browsing.

---

## Accessing Categories

Click **Categories** in the top navigation bar to manage product categories.

---

## Why Use Categories?

### Product Organization
Group related products together:
- Find products quickly
- Filter by category
- Manage related items

### Shop Display
If using the shop frontend:
- Customers browse by category
- Category pages group related items
- Navigation reflects your structure

### Reporting
Analyze performance by category:
- Sales by category
- Inventory by category
- Profitability analysis

---

## Category List View

The categories page shows all categories with:

| Column | Description |
|--------|-------------|
| **Name** | Category name |
| **Slug** | URL-friendly identifier |
| **Products** | Number of products in category |
| **Order** | Display order |
| **Status** | Active/Inactive |

---

## Creating a Category

1. Click **+ Add Category**
2. Fill in the category details:

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Category name | Yes |
| **Slug** | URL identifier (auto-generated) | No |
| **Description** | Category description | No |
| **Active** | Show in listings | Yes |

### Display Settings

| Field | Description | Required |
|-------|-------------|----------|
| **Image URL** | Category banner/image | No |
| **Display Order** | Sort order (lower = first) | No |
| **Parent Category** | For hierarchy | No |

3. Click **Add Category**

---

## Hierarchical Categories

Categories can be nested for complex catalogs:

### Example Structure

```
Gaming Accessories
├── Dice Towers
├── Card Holders
└── Miniature Storage

Home & Office
├── Desk Organizers
├── Phone Stands
└── Cable Management

Gifts
├── Custom Items
└── Gift Sets
```

### Creating Nested Categories

1. Create parent category first (e.g., "Gaming Accessories")
2. Create child category
3. Select parent from "Parent Category" dropdown
4. Save

### Best Practices for Hierarchy

- Keep depth to 2-3 levels maximum
- Use clear, descriptive names
- Don't over-categorize small catalogs

---

## Display Order

Control how categories appear in lists:

- **Lower numbers** appear first
- **Same number** sorts alphabetically
- **Unset** appears after numbered items

### Example

| Category | Display Order | Result |
|----------|---------------|--------|
| Featured | 1 | First |
| Popular | 2 | Second |
| New Arrivals | 3 | Third |
| Accessories | 10 | Fourth |
| Other | 99 | Last |

---

## Assigning Products to Categories

### When Creating/Editing Products

1. Go to product form
2. Select category from dropdown
3. Save product

### Bulk Assignment

Currently, assign categories one product at a time. For bulk operations:
1. Filter products needing categorization
2. Edit each product
3. Set category
4. Save

---

## Example Categories for 3D Print Business

### By Product Type
- Miniatures
- Terrain
- Props
- Functional Prints
- Art & Decor

### By Use Case
- Gaming
- Home Office
- Kitchen
- Garden
- Tech Accessories

### By Theme
- Fantasy
- Sci-Fi
- Modern
- Vintage
- Holiday

### By Price Point
- Under £10
- £10-25
- £25-50
- Premium (£50+)

---

## Editing a Category

1. Click on the category in the list
2. Modify any fields
3. Save changes

---

## Reordering Categories

1. Edit each category
2. Update Display Order numbers
3. Save

Categories re-sort automatically based on order values.

---

## Deactivating a Category

If you want to hide a category:

1. Edit the category
2. Toggle **Active** to off
3. Save

Deactivated categories:
- Don't appear in shop navigation
- Don't appear in product dropdowns
- Keep product associations
- Can be reactivated

---

## Deleting a Category

1. Click on the category
2. Click **Delete**
3. Confirm deletion

**Warning**: Products in this category become uncategorized.

---

## Category Images

Add visual appeal with category images:

### Image Guidelines
- Use consistent dimensions (e.g., 800x400)
- Show representative products
- Keep file sizes reasonable
- Use descriptive filenames

### Setting Category Image
1. Edit category
2. Enter Image URL
3. Save

*Note: Images must be hosted externally (URL-based).*

---

## Best Practices

### Naming
- Use clear, customer-friendly names
- Keep names concise
- Avoid jargon unless audience expects it

### Structure
- Match your customers' mental model
- Don't create empty categories
- Merge similar categories if few products

### Maintenance
- Review categories periodically
- Remove unused categories
- Adjust as catalog grows

### SEO (for shop)
- Use descriptive slugs
- Write meaningful descriptions
- Include relevant keywords naturally

---

## Common Patterns

### Small Catalog (< 50 products)
Use simple, flat categories:
- Type A
- Type B
- Type C

### Medium Catalog (50-200 products)
Add one level of nesting:
- Main Category 1
  - Subcategory 1a
  - Subcategory 1b
- Main Category 2
  - Subcategory 2a

### Large Catalog (200+ products)
Consider multiple organization schemes:
- By product type (primary)
- By use case (secondary via tags)
- By theme (collections)

---

*Back to: [Overview](overview.md) - Return to the main guide*
