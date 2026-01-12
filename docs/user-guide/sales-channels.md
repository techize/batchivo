# Sales Channels

Sales channels represent where you sell your products - marketplaces like Etsy and eBay, your own website, or in-person at craft fairs. Configuring channels accurately ensures proper profit calculations.

---

## Accessing Sales Channels

Click **Channels** in the top navigation bar to manage your sales channels.

---

## Why Configure Channels?

### Accurate Profit Calculations
Each channel has different fees. Batchivo calculates:
- Platform fees (percentage cut)
- Payment processing fees
- Monthly/listing costs

### Price Comparison
See profit margins across all your channels to:
- Identify most profitable platforms
- Set optimal prices per channel
- Decide where to list products

### Order Tracking
Link orders to their source channel for:
- Channel-specific analytics
- Fee tracking
- Performance comparison

---

## Channel List View

The channels page shows all configured channels with:

| Column | Description |
|--------|-------------|
| **Name** | Your name for the channel |
| **Platform** | Type (Etsy, eBay, Fair, etc.) |
| **Fees** | Percentage + fixed fees |
| **Monthly Cost** | Recurring subscription/booth fees |
| **Status** | Active or Inactive |

---

## Creating a Sales Channel

1. Click **+ Add Channel**
2. Fill in the channel details:

### Basic Information

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Your name for this channel (e.g., "My Etsy Shop") | Yes |
| **Platform Type** | Select from available types | Yes |
| **Active** | Whether currently selling here | Yes |

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

3. Click **Create Channel**

---

## Understanding Fees

### Percentage Fees
Most marketplaces take a percentage of each sale:
- **Etsy**: ~6.5% transaction fee
- **eBay**: ~12-13% final value fee
- **Amazon**: 8-15% referral fee
- **PayPal/Stripe**: ~2.9% + fixed

### Fixed Fees
Per-transaction fixed costs:
- Listing fees
- Payment processing fixed portion
- Shipping label fees

### Monthly Costs
Recurring expenses:
- Platform subscriptions
- Booth/table rentals at fairs
- Website hosting

### How Batchivo Calculates

```
Gross Revenue = List Price
Platform Fees = (Price × Fee%) + Fixed Fee
Net Revenue = Gross - Platform Fees
Profit = Net Revenue - Make Cost
Margin % = (Profit / Net Revenue) × 100
```

---

## Common Channel Configurations

### Etsy
| Setting | Typical Value |
|---------|---------------|
| Platform Type | Etsy |
| Fee Percentage | 6.5% |
| Fee Fixed | £0.20 |
| Monthly Cost | £0 (or Plus subscription) |

*Note: Etsy also has payment processing fees (~4%) - consider including in percentage.*

### eBay
| Setting | Typical Value |
|---------|---------------|
| Platform Type | eBay |
| Fee Percentage | 12.8% |
| Fee Fixed | £0.30 |
| Monthly Cost | £0 (or store subscription) |

### Craft Fair
| Setting | Typical Value |
|---------|---------------|
| Platform Type | Fair |
| Fee Percentage | 0% |
| Fee Fixed | £0 |
| Monthly Cost | £50-200 (booth fee) |

*Note: Monthly cost for fairs is the booth fee - divide by expected sales for cost-per-order.*

### Own Website
| Setting | Typical Value |
|---------|---------------|
| Platform Type | Online Shop |
| Fee Percentage | 2.9% (payment processor) |
| Fee Fixed | £0.20 |
| Monthly Cost | £0-30 (hosting) |

---

## Editing a Channel

1. Click on the channel in the list
2. Click **Edit**
3. Modify settings
4. Click **Save**

---

## Deactivating a Channel

If you stop selling on a platform:

1. Edit the channel
2. Toggle **Active** to off
3. Save

Deactivated channels:
- Don't appear in pricing dropdowns
- Keep historical data intact
- Can be reactivated later

---

## Deleting a Channel

1. Click on the channel
2. Click **Delete**
3. Confirm deletion

**Warning**: Deleting removes the channel permanently. Historical orders linked to this channel lose their channel reference.

---

## Using Channels with Products

### Setting Product Prices

1. Go to a product's detail page
2. Find the **Pricing** section
3. Set prices for each active channel
4. Compare margins across channels

### Profit Comparison

The product pricing table shows per-channel:

| Metric | Description |
|--------|-------------|
| **List Price** | Your asking price |
| **Platform Fees** | Calculated from channel config |
| **Net Revenue** | What you actually receive |
| **Profit** | After subtracting make cost |
| **Margin %** | Profit as % of net revenue |

---

## Monthly Cost Allocation

For channels with monthly costs (subscriptions, booth fees):

### Option 1: Per-Order Allocation
Divide monthly cost by expected orders:
```
Cost per Order = Monthly Cost / Expected Monthly Orders
Add to Fixed Fee when creating channel
```

### Option 2: Track Separately
Keep monthly costs separate and review overall profitability monthly.

### Example: Craft Fair

If booth costs £100 and you expect 50 sales:
- Per-order cost: £2.00
- Add £2.00 to Fixed Fee

---

## Best Practices

### Accurate Fee Tracking
- Research actual fees for each platform
- Include ALL fees (platform + payment processing)
- Update when platforms change fees
- Review annually

### Channel Management
- Deactivate rather than delete unused channels
- Use descriptive names ("Etsy - Main Shop" vs just "Etsy")
- Review channel performance regularly

### Pricing Strategy
- Set different prices per channel based on fees
- Consider channel-specific promotions
- Monitor which channels perform best

---

## Channel Analytics

Use channel data to understand:

### Which channels are most profitable?
Compare margins across channels for the same products.

### Where should you focus?
Channels with:
- Higher margins
- More volume
- Better customer fit

### Fee impact
How much are you paying in fees per channel? Is it worth it?

---

*Next: [Printers](printers.md) - Manage your 3D printer fleet*
