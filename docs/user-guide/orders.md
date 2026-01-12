# Orders

Orders represent customer purchases. Batchivo helps you track orders from receipt through fulfillment and delivery.

---

## Accessing Orders

Click **Orders** in the top navigation bar to view all customer orders.

---

## Order List View

The orders page displays all orders with:

| Column | Description |
|--------|-------------|
| **Order #** | Unique order identifier |
| **Customer** | Customer name |
| **Status** | Current order status |
| **Items** | Number of items in order |
| **Total** | Order total amount |
| **Date** | When order was placed |
| **Channel** | Sales channel (Etsy, eBay, etc.) |

### Filtering

Use the status filter to show:
- **All** - Every order
- **Pending** - New orders awaiting processing
- **Processing** - Orders being prepared
- **Shipped** - Orders in transit
- **Delivered** - Completed orders
- **Cancelled** - Cancelled orders
- **Refunded** - Refunded orders

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

### Status Flow

```
Pending → Processing → Shipped → Delivered
                    ↘ Cancelled
                    ↘ Refunded
```

---

## Order Detail Page

Click on any order to view full details:

### Customer Information
- Name
- Email address
- Phone number

### Shipping Address
- Full delivery address
- Any delivery notes

### Order Items
- Product name and SKU
- Quantity ordered
- Unit price and line total

### Order Summary
- Subtotal
- Shipping cost
- Tax (if applicable)
- Total amount

### Order Timeline
- When order was placed
- When shipped (with tracking)
- When delivered

### Internal Notes
- Private notes for your reference
- Not visible to customers

---

## Processing an Order

### Starting Processing

1. Open the order detail page
2. Review order items
3. The order status will show as "Pending" or "Processing"

### Linking to Production

When processing an order:
1. Create a production run for the required items
2. Note the order number in the run
3. Track production completion

### Shipping an Order

When items are ready to ship:

1. Click **Ship Order**
2. Enter shipping details:
   - **Tracking Number** - Carrier tracking number
   - **Tracking URL** - Link to tracking page (optional)
3. Click **Confirm**

The order status changes to "Shipped" and timestamps are recorded.

### Marking as Delivered

When the customer receives their order:

1. Click **Mark Delivered**
2. Confirm the delivery

The order status changes to "Delivered".

---

## Adding Internal Notes

Keep private notes about orders:

1. Click **Add Notes** or the notes icon
2. Enter your internal notes
3. Save

Notes are only visible to you, not customers. Use them for:
- Special handling instructions
- Customer communication history
- Issue tracking

---

## Quick Actions

From the order list, you can perform quick actions without opening the detail page:

| Action | Description |
|--------|-------------|
| **View** | Open order details |
| **Ship** | Mark as shipped (opens tracking dialog) |
| **Deliver** | Mark as delivered |

---

## Order Sources

Orders can come from:

### Manual Entry
Create orders directly in Batchivo for:
- Phone orders
- In-person sales
- Custom requests

### Sales Channel Integration
(Future feature) Automatic import from:
- Etsy
- eBay
- Shopify
- WooCommerce

### Shop Frontend
Orders placed through your Batchivo shop (if configured).

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

### Problem Order

1. Add internal notes documenting issue
2. Communicate with customer
3. Update status as appropriate (cancel/refund if needed)

### Bulk Shipments

For multiple orders shipping together:
1. Process each order individually
2. Use same tracking for combined shipments
3. Ship each order with shared tracking

---

## Best Practices

### Order Processing
- Review orders promptly
- Check inventory before confirming
- Communicate delays to customers
- Keep internal notes updated

### Shipping
- Always add tracking numbers
- Include tracking URLs for easy customer access
- Ship promptly after production
- Consider shipping insurance for high-value orders

### Record Keeping
- Use internal notes for important details
- Keep order history for reference
- Review cancelled/refunded orders for patterns

---

*Next: [Sales Channels](sales-channels.md) - Configure your sales platforms*
