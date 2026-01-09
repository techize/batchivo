# Designers

Designers are the original creators of STL files you print under license. Tracking designers helps with attribution, licensing compliance, and understanding your product origins.

---

## Accessing Designers

Click **Designers** in the top navigation bar to manage your designer database.

---

## Why Track Designers?

### Licensing Compliance
Many STL files are sold with commercial licenses:
- Track which products use which designer's work
- Maintain attribution records
- Document licensing arrangements

### Membership Management
Many designers offer subscription services:
- Track membership costs
- Monitor renewal dates
- Calculate per-product licensing costs

### Attribution
Give credit where it's due:
- Link products to creators
- Maintain designer websites/social links
- Support the design community

---

## Designer List View

The designers page shows all designers with:

| Column | Description |
|--------|-------------|
| **Name** | Designer/studio name |
| **Products** | Number of linked products |
| **Website** | Link to designer's site |
| **Membership** | Cost and renewal info |
| **Status** | Active/Inactive |

---

## Adding a Designer

1. Click **+ Add Designer**
2. Fill in the designer details:

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Designer or studio name | Yes |
| **Slug** | URL-friendly identifier | Auto-generated |
| **Description** | About the designer | No |
| **Active** | Currently using their designs | Yes |

### Contact & Links

| Field | Description | Required |
|-------|-------------|----------|
| **Logo URL** | Designer's logo image | No |
| **Website URL** | Main website | No |
| **Social Links** | Social media profiles | No |

Social links are stored as key-value pairs:
- `patreon`: Patreon URL
- `myminifactory`: MyMiniFactory store
- `instagram`: Instagram profile
- `twitter`: Twitter/X profile
- `youtube`: YouTube channel

### Membership Information

For subscription-based licenses:

| Field | Description | Required |
|-------|-------------|----------|
| **Membership Cost** | Monthly/yearly cost | No |
| **Start Date** | When membership began | No |
| **Renewal Date** | When next payment due | No |

### Notes

Free-form notes field for:
- License terms
- Commercial use restrictions
- Contact information
- Special arrangements

3. Click **Add Designer**

---

## Popular Designer Platforms

### Patreon
Many designers offer STL files through Patreon tiers.

Example entry:
- Name: "Dragon Trappers Lodge"
- Website: https://dragontrapper.com
- Social Links: `{"patreon": "https://patreon.com/dragontrapper"}`
- Membership: £10/month

### MyMiniFactory Tribes
Subscription-based access to designer catalogs.

Example entry:
- Name: "Loot Studios"
- Website: https://www.loot-studios.com
- Social Links: `{"myminifactory": "https://www.myminifactory.com/users/LootStudios"}`
- Membership: £12/month

### One-Time Purchases
For individual file purchases, you might:
- Create designer entry without membership
- Note specific files purchased in Notes
- Track through product links

---

## Linking Products to Designers

### When Creating Products

1. Create or edit a product
2. Select the designer from dropdown
3. Save

### Viewing Designer's Products

1. Go to designer detail page
2. See list of linked products
3. Product count shows in designer list

---

## Membership Cost Allocation

### Per-Product Allocation

To include licensing in product costs:

1. Calculate monthly license cost
2. Estimate products sold using that license
3. Add per-product cost to product pricing

Example:
- Membership: £10/month
- Expected sales: 20 products/month
- Per-product: £0.50

### Tracking ROI

Compare membership cost vs sales:
- Products sold from designer
- Revenue generated
- Is the membership worthwhile?

---

## Renewal Reminders

Use the Renewal Date field to track:
- When subscriptions need renewal
- Annual license renewals
- Credit card updates

Check designers page regularly for upcoming renewals.

---

## Editing a Designer

1. Click on the designer in the list
2. Modify any fields
3. Save changes

---

## Deactivating a Designer

If you stop using a designer's work:

1. Edit the designer
2. Toggle **Active** to off
3. Save

Deactivated designers:
- Don't appear in product dropdowns
- Keep historical product links
- Can be reactivated

---

## Deleting a Designer

1. Click on the designer
2. Click **Delete**
3. Confirm deletion

**Warning**: Products linked to this designer lose their attribution.

---

## Best Practices

### Accurate Records
- Add designers when you first use their work
- Keep website/social links current
- Note license terms in Notes field

### Membership Tracking
- Set renewal dates accurately
- Track all subscription costs
- Review unused memberships

### Attribution
- Always link products to designers
- Use consistent naming
- Support designers you use regularly

---

## Example Workflow

### New Designer Setup

1. Purchase/subscribe to designer's files
2. Add designer to Nozzly:
   - Name and contact info
   - Membership cost and dates
   - License notes
3. Create products from their designs
4. Link products to designer

### Monthly Review

1. Check upcoming renewals
2. Review product counts per designer
3. Evaluate membership ROI
4. Cancel unused subscriptions

---

*Next: [Categories](categories.md) - Organize your products*
