# Critical Gaps and Documentation Tasks PRD

This PRD captures critical feature gaps identified from competitive analysis and documentation tasks.

## Critical Gap 1: Printer Integration System (High Priority)

### Goal
Integrate with 3D printer firmware/software for automatic filament usage tracking and real-time monitoring.

### Requirements
1. **OctoPrint Integration**
   - Connect to OctoPrint instances via API
   - Track active spool per printer
   - Auto-deduct filament usage from .gcode estimation
   - Receive print completion notifications

2. **Moonraker/Klipper Integration**
   - WebSocket connection for real-time updates
   - Spool tracking via Klipper macros
   - Integration with spool_manager module

3. **Bambu Lab Integration**
   - Cloud API integration for X1/P1 printers
   - AMS (Automatic Material System) spool mapping
   - RFID spool tag support (if available)

4. **Webhook Receiver**
   - Generic webhook endpoint for custom integrations
   - Event types: print_started, print_completed, print_failed
   - Automatic spool weight deduction on completion

### Test Strategy
Test each printer integration independently. Mock external APIs for unit tests. Create integration tests with real printer connections in staging.

---

## Critical Gap 2: Print Queue and Fleet Management System (High Priority)

### Goal
Manage print jobs across multiple printers with intelligent queue management.

### Requirements
1. **Printer Fleet Management**
   - Add/edit/delete printers with capabilities (bed size, materials, speed)
   - Track printer status (idle, printing, maintenance, offline)
   - Assign spools to specific printers

2. **Print Queue System**
   - Create print jobs from products or production runs
   - Assign jobs to compatible printers based on material/size
   - Priority queue with manual reordering
   - Estimated completion times

3. **Queue Intelligence**
   - Automatic printer assignment based on availability and capability
   - Spool recommendations based on current inventory
   - Batch printing optimization (group similar jobs)

4. **Real-time Dashboard**
   - Live printer status grid
   - Progress bars for active prints
   - Estimated queue completion time

### Test Strategy
Unit tests for queue logic and printer matching. Integration tests for WebSocket updates. E2E tests for complete queue workflows.

---

## Critical Gap 3: Complete Cost of Goods Sold (COGS) System (Medium Priority)

### Goal
Provide comprehensive cost tracking including electricity, depreciation, consumables, and labor.

### Requirements
1. **Printer Depreciation Tracking**
   - Add purchase price and expected lifespan per printer
   - Calculate hourly depreciation rate
   - Include in product cost calculations

2. **Electricity Cost Tracking**
   - Configure electricity rate (per kWh)
   - Estimate power consumption per print (by printer/material)
   - Track actual usage if smart plug data available

3. **Consumables Tracking**
   - Nozzle wear cost per print hour
   - Bed adhesive cost allocation
   - Other consumables (glue, tape, etc.)

4. **Labor Cost Integration**
   - Configurable hourly labor rate
   - Track actual time spent on orders
   - Include in margin calculations

5. **True Margin Analysis**
   - Dashboard showing true profit margins
   - Cost breakdown visualization (materials, electricity, depreciation, labor)
   - Comparison with competitor pricing

### Test Strategy
Unit tests for all cost calculations. Integration tests for cost rollup into products. Verify margin calculations match expected values.

---

## Critical Gap 4: AI-Powered Print Failure Detection (Medium Priority)

### Goal
Use machine learning to predict and detect print failures before they complete.

### Requirements
1. **Print Monitoring Integration**
   - Integration with camera feeds (OctoPrint, Obico)
   - Receive frame captures during prints

2. **ML Failure Detection**
   - Basic anomaly detection for layer shifting, stringing, adhesion
   - Integration with external services (Obico, The Spaghetti Detective)
   - Alert notifications for detected issues

3. **Failure Tracking**
   - Log all print failures with causes
   - Track failure rates by material, model, printer
   - Analyze patterns for root cause

4. **Print Quality Analytics**
   - Success rate dashboards
   - Material quality scoring based on print results
   - Recommendations for improving print success

### Test Strategy
Integration tests with mock camera feeds. Test alert generation on failure detection. Verify analytics calculations.

---

## Critical Gap 5: Marketplace Integrations (Medium Priority)

### Goal
Connect directly with e-commerce marketplaces for automatic order import and inventory sync.

### Requirements
1. **Etsy Integration**
   - OAuth2 connection to Etsy shop
   - Import orders automatically
   - Sync inventory levels to listings
   - Update tracking numbers

2. **Shopify Integration**
   - Connect Shopify store
   - Two-way inventory sync
   - Order import and status updates
   - Product catalog sync

3. **eBay Integration**
   - Connect eBay seller account
   - Import orders
   - Sync inventory quantities

4. **Generic API Connector**
   - Webhook endpoint for custom platforms
   - API endpoints for external inventory queries

### Test Strategy
Mock marketplace APIs for unit tests. Integration tests with sandbox/development accounts. E2E tests for complete order import workflows.

---

## Documentation Task 1: User Guide - System Overview (High Priority)

### Goal
Create comprehensive user documentation for the Nozzly platform.

### Requirements
1. Create `docs/user-guide/overview.md` with system introduction
2. Create `docs/user-guide/filament-management.md` covering:
   - Adding new spools
   - Weight tracking methods
   - Low stock alerts
   - SpoolmanDB integration
   - QR code generation and scanning
3. Create `docs/user-guide/models.md` covering:
   - Creating 3D model entries
   - Material requirements (BOM)
   - Components (magnets, inserts)
   - Printer configurations

### Test Strategy
Review documentation for accuracy against current implementation. Have a new user follow guides to verify completeness.

---

## Documentation Task 2: User Guide - Products and Production (High Priority)

### Goal
Document product management and production run workflows.

### Requirements
1. Create `docs/user-guide/products.md` covering:
   - Creating products from models
   - Product components and BOMs
   - Pricing configuration per channel
   - Cost calculation breakdown
2. Create `docs/user-guide/production-runs.md` covering:
   - CreateRunWizard walkthrough
   - Multi-plate runs
   - Completing runs with weight tracking
   - Variance analysis
3. Create `docs/user-guide/orders.md` covering:
   - Order lifecycle
   - Processing and fulfillment
   - Ship and deliver workflows

### Test Strategy
Follow each workflow in the application while writing documentation to ensure accuracy.

---

## Documentation Task 3: API Reference Documentation (High Priority)

### Goal
Create comprehensive API documentation beyond auto-generated Swagger.

### Requirements
1. Create `docs/api-reference/overview.md` covering:
   - Base URL and versioning
   - Authentication (JWT tokens)
   - Rate limiting
   - Error handling patterns
   - Pagination patterns
2. Create detailed endpoint docs for each category:
   - `docs/api-reference/spools.md` (6 endpoints)
   - `docs/api-reference/products.md` (8 endpoints)
   - `docs/api-reference/production-runs.md` (10 endpoints)
   - `docs/api-reference/orders.md` (4 endpoints)
   - `docs/api-reference/analytics.md` (3 endpoints)
3. Include request/response examples for all endpoints

### Test Strategy
Verify each documented endpoint works as described. Test example requests against running API.

---

## Documentation Task 4: Workflow Documentation (Medium Priority)

### Goal
Document complete end-to-end workflows for common business operations.

### Requirements
1. Create `docs/workflows/new-filament-spool.md` - Adding new inventory
2. Create `docs/workflows/production-run.md` - Complete print run workflow
3. Create `docs/workflows/order-fulfillment.md` - Order to delivery
4. Create `docs/workflows/cost-analysis.md` - Analyzing product costs
5. Include screenshots, step-by-step instructions, and tips

### Test Strategy
Execute each workflow while documenting. Have another person follow the workflow to verify clarity.

---

## Documentation Task 5: Architecture Documentation (Medium Priority)

### Goal
Document system architecture for developers and operators.

### Requirements
1. Create `docs/architecture/overview.md` with:
   - System architecture diagram (Mermaid)
   - Component descriptions
   - Data flow diagrams
2. Create `docs/architecture/database.md` with:
   - Entity relationship diagram
   - Table descriptions
   - Multi-tenant RLS policies
3. Create `docs/architecture/deployment.md` with:
   - k3s deployment guide
   - ArgoCD configuration
   - Cloudflare Tunnel setup

### Test Strategy
Review diagrams for accuracy against actual implementation. Verify deployment steps work on fresh cluster.
