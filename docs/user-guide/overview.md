# Batchivo User Guide - Overview

Welcome to Batchivo, a comprehensive 3D print business management platform designed to help you track inventory, manage production, and grow your 3D printing business.

---

## What is Batchivo?

Batchivo is an all-in-one solution for 3D printing businesses that need to:

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
- Be linked to one or more models
- Include additional components (magnets, inserts, packaging)
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

Batchivo's interface is organized into logical sections accessible from the top navigation bar:

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

---

## Need Help?

- **API Documentation**: See [API Reference](../api-reference/overview.md)
- **Workflows**: Step-by-step guides in [Workflows](../workflows/)
- **Report Issues**: GitHub Issues at [batchivo.com repository](https://github.com/techize/batchivo.com)

---

*Next: [Filament Management](filament-management.md) - Learn to manage your inventory*
