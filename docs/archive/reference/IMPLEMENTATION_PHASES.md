# Implementation Phases

**Nozzly - Detailed Development Roadmap**

---

## Overview

This document provides a phase-by-phase implementation plan for Nozzly. Each phase includes:

- **Goals**: What we're building
- **Deliverables**: Concrete outputs
- **Tasks**: Step-by-step execution checklist
- **Success Criteria**: How to know you're done
- **Estimated Time**: Assuming 10-15 hours/week

**Total Estimated Timeline**: 16-20 weeks (4-5 months) for full MVP

---

## Phase 0: Foundation (Weeks 1-2)

### Goals
- Project structure scaffolding
- Local development environment
- Core infrastructure (database, auth, observability)
- CI/CD pipeline

### Deliverables
- ✅ GitHub repository with documentation
- [ ] Backend scaffolding (FastAPI + SQLAlchemy)
- [ ] Frontend scaffolding (React + shadcn/ui)
- [ ] Docker Compose development stack
- [ ] Database migrations (Alembic)
- [ ] Authentik integration
- [ ] OpenTelemetry instrumentation
- [ ] GitHub Actions CI pipeline

---

### Tasks Checklist

#### Documentation (✅ Complete)
- [x] Create repository
- [x] Write CLAUDE.md
- [x] Write README.md
- [x] Write DATABASE_SCHEMA.md
- [x] Write IMPLEMENTATION_PHASES.md (this file)
- [ ] Write DEVELOPMENT.md
- [ ] Write ARCHITECTURE.md
- [ ] Write DEPLOYMENT.md

#### Backend Scaffolding
- [ ] Initialize Python project with Poetry
  ```bash
  mkdir backend && cd backend
  poetry init
  poetry add fastapi uvicorn sqlalchemy alembic pydantic-settings
  poetry add psycopg[binary] asyncpg redis authlib httpx
  poetry add opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
  poetry add celery[redis] qrcode pillow
  poetry add --group dev pytest pytest-asyncio pytest-cov black ruff mypy
  ```

- [ ] Create project structure
  ```bash
  mkdir -p app/{api/v1,auth,models,schemas,services,background,observability}
  touch app/{__init__,main,config,database}.py
  ```

- [ ] Configure `app/config.py` (Pydantic settings)
- [ ] Configure `app/database.py` (async SQLAlchemy)
- [ ] Configure `app/main.py` (FastAPI app with CORS, middleware)
- [ ] Configure `app/observability/tracing.py` (OpenTelemetry setup)

#### Database Setup
- [ ] Initialize Alembic
  ```bash
  poetry run alembic init alembic
  ```

- [ ] Configure `alembic/env.py` (async support)
- [ ] Create initial migration (foundation tables)
  - tenants
  - users
  - user_tenants
  - material_types (seed data)

- [ ] Test migration locally
  ```bash
  poetry run alembic upgrade head
  ```

#### Authentication (Authentik)
- [ ] Create `app/auth/middleware.py` (OIDC integration)
- [ ] Create `app/auth/dependencies.py` (`get_current_user`, `get_current_tenant`)
- [ ] Create `app/auth/models.py` (User, Tenant SQLAlchemy models)
- [ ] Add tenant context middleware (set `app.current_tenant_id`)

#### Frontend Scaffolding
- [ ] Initialize Vite + React + TypeScript
  ```bash
  mkdir frontend && cd frontend
  npm create vite@latest . -- --template react-ts
  npm install
  ```

- [ ] Initialize shadcn/ui
  ```bash
  npx shadcn-ui@latest init
  npx shadcn-ui@latest add button card input label select table
  ```

- [ ] Install dependencies
  ```bash
  npm install @tanstack/react-query @tanstack/react-router
  npm install axios oidc-client-ts recharts jsqr
  npm install vite-plugin-pwa workbox-window
  ```

- [ ] Configure `vite.config.ts` (PWA plugin, path aliases)
- [ ] Create project structure
  ```bash
  mkdir -p src/{components/{ui,layout},hooks,lib,routes,types}
  ```

- [ ] Configure `src/lib/api.ts` (Axios client with auth)
- [ ] Configure `src/lib/auth.ts` (OIDC client setup)

#### Docker Compose Stack
- [ ] Create `docker-compose.yml` at project root
  - PostgreSQL
  - Redis
  - Authentik (server + worker + postgres + redis)
  - Tempo (tracing)
  - Prometheus (metrics)
  - Loki (logs)
  - Grafana (dashboards)

- [ ] Create `infrastructure/observability/tempo.yaml`
- [ ] Create `infrastructure/observability/prometheus.yml`
- [ ] Create Grafana datasource configs

- [ ] Test full stack startup
  ```bash
  docker-compose up -d
  docker-compose ps  # Verify all healthy
  ```

#### CI/CD Pipeline
- [ ] Create `.github/workflows/backend-ci.yml`
  - Run tests (pytest)
  - Lint (ruff, mypy)
  - Format check (black)

- [ ] Create `.github/workflows/frontend-ci.yml`
  - Run tests (vitest)
  - Lint (eslint)
  - Build check

- [ ] Test workflows locally with `act` (optional)

#### Makefile
- [ ] Create `Makefile` with common commands
  - `make dev` - Start development stack
  - `make test` - Run all tests
  - `make lint` - Run linters
  - `make format` - Format code
  - `make migrate` - Run migrations
  - `make build` - Build Docker images

---

### Success Criteria

- [ ] `docker-compose up -d` starts all services successfully
- [ ] Backend accessible at http://localhost:8000/health (returns 200)
- [ ] Frontend accessible at http://localhost:5173
- [ ] Authentik accessible at http://localhost:9000
- [ ] Grafana accessible at http://localhost:3000
- [ ] Database migrations run without errors
- [ ] CI pipelines pass on GitHub
- [ ] OpenTelemetry traces visible in Grafana/Tempo

---

## Phase 1: Core Inventory Management (Weeks 3-4)

### Goals
- CRUD operations for filament spools
- Material types, brands, colors
- Weight tracking
- Basic UI (list + detail views)

### Deliverables
- [ ] Backend: Spools API endpoints
- [ ] Backend: Material types API (read-only)
- [ ] Frontend: Spool list page with search/filter
- [ ] Frontend: Spool detail/edit form
- [ ] Frontend: Add new spool form
- [ ] Database: Spools table + material_types seeded

---

### Tasks Checklist

#### Backend - Models
- [ ] Create `app/models/material_type.py` (SQLAlchemy model)
- [ ] Create `app/models/spool.py` (SQLAlchemy model with tenant_id)
- [ ] Create migration for spools + material_types tables
- [ ] Seed material_types data (PLA, PETG, TPU, ABS, etc.)

#### Backend - Schemas (Pydantic)
- [ ] Create `app/schemas/material_type.py`
  - MaterialTypeOut
- [ ] Create `app/schemas/spool.py`
  - SpoolCreate
  - SpoolUpdate
  - SpoolOut
  - SpoolList (paginated)

#### Backend - API Endpoints
- [ ] Create `app/api/v1/spools.py`
  - `GET /api/v1/spools` - List spools (paginated, filterable)
  - `GET /api/v1/spools/{id}` - Get spool detail
  - `POST /api/v1/spools` - Create new spool
  - `PUT /api/v1/spools/{id}` - Update spool
  - `DELETE /api/v1/spools/{id}` - Delete/deactivate spool

- [ ] Create `app/api/v1/material_types.py`
  - `GET /api/v1/material-types` - List all types

- [ ] Add multi-tenant checks (use `get_current_tenant()` dependency)
- [ ] Add OpenTelemetry spans for each endpoint

#### Backend - Business Logic
- [ ] Create `app/services/inventory.py`
  - `calculate_remaining_weight(spool_id)` → percentage
  - `generate_spool_id(tenant_id)` → unique FIL-XXX
  - `check_low_stock(tenant_id, threshold)` → list of low spools

#### Backend - Tests
- [ ] Test spool CRUD operations
- [ ] Test multi-tenant isolation (user A can't see user B's spools)
- [ ] Test weight validation (current <= initial)
- [ ] Test spool_id uniqueness per tenant

#### Frontend - API Client
- [ ] Create `src/lib/api/spools.ts`
  - `listSpools(filters?)` → Promise<Spool[]>
  - `getSpool(id)` → Promise<Spool>
  - `createSpool(data)` → Promise<Spool>
  - `updateSpool(id, data)` → Promise<Spool>
  - `deleteSpool(id)` → Promise<void>

- [ ] Create `src/lib/api/materialTypes.ts`
  - `listMaterialTypes()` → Promise<MaterialType[]>

#### Frontend - Components
- [ ] Create `src/components/layout/Sidebar.tsx` (navigation)
- [ ] Create `src/components/layout/Header.tsx` (user menu, tenant selector)
- [ ] Create `src/components/inventory/SpoolList.tsx`
  - Data table with search, sort, filter
  - Columns: Spool ID, Material, Color, Brand, Remaining %
  - Actions: View, Edit, Delete
  - Low stock indicator (badge/color)

- [ ] Create `src/components/inventory/SpoolDetail.tsx`
  - Display all spool info
  - Visual weight gauge (progress bar)
  - Purchase history
  - Usage history (Phase 4+)

- [ ] Create `src/components/inventory/SpoolForm.tsx`
  - Material type dropdown
  - Color input (text + color picker)
  - Brand input
  - Initial weight (number input)
  - Purchase cost, supplier, date
  - Storage location
  - Form validation

#### Frontend - Pages/Routes
- [ ] Create `src/routes/inventory/index.tsx` (list page)
- [ ] Create `src/routes/inventory/$spoolId.tsx` (detail page)
- [ ] Create `src/routes/inventory/new.tsx` (create page)

#### Frontend - Hooks
- [ ] Create `src/hooks/useSpools.ts` (TanStack Query hooks)
  - `useSpools(filters)` - List with refetch
  - `useSpool(id)` - Single spool
  - `useCreateSpool()` - Mutation
  - `useUpdateSpool()` - Mutation
  - `useDeleteSpool()` - Mutation

---

### Success Criteria

- [ ] Can create a new spool via UI
- [ ] Spool list displays correctly with filtering
- [ ] Can view spool detail page
- [ ] Can edit spool weight and see percentage update
- [ ] Can delete a spool
- [ ] Multi-tenant isolation verified (test with 2 users)
- [ ] All tests pass
- [ ] Traces visible in Grafana for spool operations

---

## Phase 2: Product Catalog & Costing (Weeks 5-6)

### Goals
- Product CRUD
- Bill of Materials (BOM) editor
- Component tracking
- Automatic cost calculation

### Deliverables
- [ ] Backend: Products API
- [ ] Backend: Product materials (BOM) API
- [ ] Backend: Product components API
- [ ] Frontend: Product list/detail/form
- [ ] Frontend: BOM editor (multi-material selector)
- [ ] Frontend: Cost breakdown display

---

### Tasks Checklist

#### Backend - Models
- [ ] Create `app/models/product.py`
- [ ] Create `app/models/product_material.py`
- [ ] Create `app/models/product_component.py`
- [ ] Create migrations

#### Backend - Schemas
- [ ] Create `app/schemas/product.py`
  - ProductCreate, ProductUpdate, ProductOut
  - ProductWithCost (includes calculated cost)
- [ ] Create `app/schemas/product_material.py`
  - ProductMaterialCreate, ProductMaterialOut
- [ ] Create `app/schemas/product_component.py`
  - ProductComponentCreate, ProductComponentOut

#### Backend - API Endpoints
- [ ] `GET /api/v1/products` - List products
- [ ] `GET /api/v1/products/{id}` - Get product with BOM
- [ ] `POST /api/v1/products` - Create product
- [ ] `PUT /api/v1/products/{id}` - Update product
- [ ] `DELETE /api/v1/products/{id}` - Delete product
- [ ] `GET /api/v1/products/{id}/cost` - Get cost breakdown
- [ ] `POST /api/v1/products/{id}/materials` - Add material to BOM
- [ ] `DELETE /api/v1/products/{id}/materials/{material_id}` - Remove from BOM
- [ ] `POST /api/v1/products/{id}/components` - Add component
- [ ] `DELETE /api/v1/products/{id}/components/{component_id}` - Remove component

#### Backend - Services
- [ ] Create `app/services/costing.py`
  - `calculate_material_cost(product_id)` → Decimal
  - `calculate_component_cost(product_id)` → Decimal
  - `calculate_labor_cost(product_id)` → Decimal
  - `calculate_overhead_cost(product_id)` → Decimal
  - `calculate_total_cost(product_id)` → CostBreakdown

#### Backend - Tests
- [ ] Test product CRUD
- [ ] Test multi-material BOM
- [ ] Test cost calculation accuracy
- [ ] Test component cost aggregation

#### Frontend - Components
- [ ] Create `src/components/products/ProductList.tsx`
- [ ] Create `src/components/products/ProductDetail.tsx`
- [ ] Create `src/components/products/ProductForm.tsx`
- [ ] Create `src/components/products/BOMEditor.tsx`
  - Material selector (dropdown of spools)
  - Weight input per material
  - Material slot selector (primary, support, etc.)
  - Add/remove rows
- [ ] Create `src/components/products/ComponentEditor.tsx`
  - Component name input
  - Quantity + unit cost inputs
  - Add/remove rows
- [ ] Create `src/components/products/CostBreakdown.tsx`
  - Visual breakdown (pie chart or stacked bar)
  - Material, component, labor, overhead sections
  - Total cost display

#### Frontend - Routes
- [ ] `src/routes/products/index.tsx`
- [ ] `src/routes/products/$productId.tsx`
- [ ] `src/routes/products/new.tsx`

#### Frontend - Hooks
- [ ] `src/hooks/useProducts.ts`

---

### Success Criteria

- [ ] Can create product with multiple materials
- [ ] Can add components (magnets, etc.)
- [ ] Cost calculation displays accurate breakdown
- [ ] BOM editor is intuitive (drag-drop optional)
- [ ] Can edit labor hours and see cost update
- [ ] All tests pass

---

## Phase 3: Pricing Engine (Weeks 7-8)

### Goals
- Sales channel management
- Product pricing per channel
- Fee calculations
- Multi-marketplace comparison

### Deliverables
- [ ] Backend: Sales channels API
- [ ] Backend: Product pricing API
- [ ] Frontend: Channel management
- [ ] Frontend: Pricing calculator with comparison table
- [ ] Frontend: Export pricing sheet (CSV)

---

### Tasks Checklist

#### Backend - Models
- [ ] Create `app/models/sales_channel.py`
- [ ] Create `app/models/product_pricing.py`
- [ ] Create migrations

#### Backend - Schemas
- [ ] `app/schemas/sales_channel.py`
- [ ] `app/schemas/product_pricing.py`
- [ ] `app/schemas/pricing_comparison.py` (for comparison view)

#### Backend - API Endpoints
- [ ] `GET /api/v1/sales-channels` - List channels
- [ ] `POST /api/v1/sales-channels` - Create channel
- [ ] `PUT /api/v1/sales-channels/{id}` - Update channel
- [ ] `DELETE /api/v1/sales-channels/{id}` - Delete channel
- [ ] `GET /api/v1/products/{id}/pricing` - Get pricing for all channels
- [ ] `PUT /api/v1/products/{id}/pricing/{channel_id}` - Update pricing for channel
- [ ] `GET /api/v1/pricing/compare?product_id={id}` - Compare all channels
- [ ] `GET /api/v1/pricing/export?product_ids=[]` - Export CSV

#### Backend - Services
- [ ] Create `app/services/pricing.py`
  - `calculate_platform_fees(list_price, channel)` → Decimal
  - `calculate_net_revenue(list_price, fees)` → Decimal
  - `calculate_list_price(cost, margin, fees)` → Decimal (reverse calc)
  - `calculate_break_even_price(cost, fees)` → Decimal
  - `compare_channels(product_id)` → ComparisonTable

#### Backend - Tests
- [ ] Test fee calculations (percentage, fixed, hybrid)
- [ ] Test reverse pricing (target margin → list price)
- [ ] Test comparison logic
- [ ] Test CSV export format

#### Frontend - Components
- [ ] `src/components/channels/ChannelList.tsx`
- [ ] `src/components/channels/ChannelForm.tsx`
- [ ] `src/components/pricing/PricingCalculator.tsx`
  - Input: Target margin %
  - Display: List price, fees, net revenue, profit
  - Per-channel calculator
- [ ] `src/components/pricing/ComparisonTable.tsx`
  - Columns: Channel, List Price, Fees, Net Revenue, Profit, Margin %
  - Highlight best option
  - Sort by profit/margin
- [ ] `src/components/pricing/ExportButton.tsx`
  - Export selected products to CSV/PDF

#### Frontend - Routes
- [ ] `src/routes/channels/index.tsx`
- [ ] `src/routes/pricing/calculator.tsx`
- [ ] `src/routes/pricing/compare.tsx`

---

### Success Criteria

- [ ] Can create sales channels (Etsy, eBay, etc.)
- [ ] Can input target margin and get calculated list price
- [ ] Comparison table shows accurate data
- [ ] Can identify most profitable channel at a glance
- [ ] Can export pricing sheet to CSV

---

## Phase 4: Sales & Inventory Deduction (Weeks 9-10)

### Goals
- Order tracking
- Automatic inventory deduction on sale
- Customer database (basic)
- Order status workflow

### Deliverables
- [ ] Backend: Orders API
- [ ] Backend: Inventory deduction logic
- [ ] Frontend: Order list/detail/form
- [ ] Frontend: Order status updates
- [ ] Frontend: Inventory transaction history

---

### Tasks Checklist

#### Backend - Models
- [ ] Create `app/models/order.py`
- [ ] Update `inventory_transactions` model (if needed)
- [ ] Create migrations

#### Backend - Schemas
- [ ] `app/schemas/order.py`
  - OrderCreate, OrderUpdate, OrderOut
  - OrderWithDetails (includes product, channel info)

#### Backend - API Endpoints
- [ ] `GET /api/v1/orders` - List orders (filterable by status, date)
- [ ] `GET /api/v1/orders/{id}` - Get order detail
- [ ] `POST /api/v1/orders` - Create order (triggers deduction)
- [ ] `PUT /api/v1/orders/{id}` - Update order
- [ ] `PATCH /api/v1/orders/{id}/status` - Update status only
- [ ] `DELETE /api/v1/orders/{id}` - Cancel order (reverse deduction)

#### Backend - Services
- [ ] Update `app/services/inventory.py`
  - `deduct_material(order)` - Deduct from spools based on product BOM
  - `reverse_deduction(order)` - Restore inventory (for cancellations)
  - `validate_sufficient_stock(product_id, quantity)` - Check before order

#### Backend - Tests
- [ ] Test order creation deducts correct amounts
- [ ] Test insufficient stock error handling
- [ ] Test cancellation restores inventory
- [ ] Test inventory transaction log accuracy

#### Frontend - Components
- [ ] `src/components/orders/OrderList.tsx`
  - Status badges (pending, printing, shipped, etc.)
  - Date filters
  - Search by order number, customer
- [ ] `src/components/orders/OrderDetail.tsx`
  - Order summary
  - Product details
  - Cost/profit breakdown
  - Status timeline
- [ ] `src/components/orders/OrderForm.tsx`
  - Product selector
  - Quantity input
  - Channel selector
  - Customer info inputs
  - Stock validation (warn if low)
- [ ] `src/components/orders/OrderStatusStepper.tsx`
  - Visual status progression
  - Update status button
- [ ] `src/components/inventory/TransactionHistory.tsx`
  - List all transactions for a spool
  - Filter by type (usage, purchase, adjustment)
  - Link to originating order

#### Frontend - Routes
- [ ] `src/routes/orders/index.tsx`
- [ ] `src/routes/orders/$orderId.tsx`
- [ ] `src/routes/orders/new.tsx`

---

### Success Criteria

- [ ] Creating an order deducts material from spools
- [ ] Inventory transaction log shows usage entry
- [ ] Canceling an order restores inventory
- [ ] Cannot create order if insufficient stock
- [ ] Order status can be updated through workflow
- [ ] Transaction history visible on spool detail page

---

## Phase 5: Reorder Management (Weeks 11-12)

### Goals
- Usage rate tracking
- Reorder point calculations
- Low stock alerts
- Purchase order generation

### Deliverables
- [ ] Backend: Reorder settings API
- [ ] Backend: Suppliers API
- [ ] Backend: Purchases API
- [ ] Backend: Background job for daily calculations
- [ ] Frontend: Reorder dashboard
- [ ] Frontend: Supplier management
- [ ] Frontend: Purchase order form

---

### Tasks Checklist

#### Backend - Models
- [ ] Create `app/models/supplier.py`
- [ ] Create `app/models/purchase.py`
- [ ] Create `app/models/purchase_item.py`
- [ ] Create `app/models/reorder_setting.py`
- [ ] Create migrations

#### Backend - Schemas
- [ ] `app/schemas/supplier.py`
- [ ] `app/schemas/purchase.py`
- [ ] `app/schemas/reorder_setting.py`
- [ ] `app/schemas/reorder_alert.py`

#### Backend - API Endpoints
- [ ] `GET /api/v1/suppliers` - List suppliers
- [ ] `POST /api/v1/suppliers` - Create supplier
- [ ] `PUT /api/v1/suppliers/{id}` - Update supplier
- [ ] `GET /api/v1/purchases` - List purchases
- [ ] `POST /api/v1/purchases` - Create purchase (with items)
- [ ] `PUT /api/v1/purchases/{id}/receive` - Mark received (creates spools)
- [ ] `GET /api/v1/reorder/alerts` - Get current low stock alerts
- [ ] `GET /api/v1/reorder/settings` - Get reorder settings
- [ ] `PUT /api/v1/reorder/settings/{id}` - Update settings
- [ ] `POST /api/v1/reorder/calculate` - Trigger manual recalculation

#### Backend - Services
- [ ] Create `app/services/reorder.py`
  - `calculate_daily_usage(material, color, brand, days=30)` → avg grams/day
  - `calculate_reorder_point(avg_usage, lead_time, safety_days)` → grams
  - `get_low_stock_items(tenant_id)` → List[ReorderAlert]
  - `suggest_reorder_quantity(material, color, brand)` → grams

#### Backend - Background Jobs
- [ ] Create `app/background/tasks.py`
  - `@celery.task daily_usage_calculation()` - Run at 3 AM
  - `@celery.task check_reorder_points()` - Run at 9 AM
  - `@celery.task send_low_stock_emails()` - Notify users

- [ ] Configure Celery Beat schedule

#### Backend - Tests
- [ ] Test usage calculation accuracy
- [ ] Test reorder point formula
- [ ] Test alert generation
- [ ] Test purchase receipt creates spools

#### Frontend - Components
- [ ] `src/components/reorder/ReorderDashboard.tsx`
  - Low stock alerts (count badge)
  - Usage trends chart
  - Reorder recommendations
- [ ] `src/components/reorder/AlertList.tsx`
  - Material, color, current stock, reorder point
  - Action: Create purchase order
- [ ] `src/components/suppliers/SupplierList.tsx`
- [ ] `src/components/suppliers/SupplierForm.tsx`
- [ ] `src/components/purchases/PurchaseForm.tsx`
  - Supplier selector
  - Line items (material, quantity, cost)
  - Expected delivery date
- [ ] `src/components/purchases/PurchaseList.tsx`
  - Status filter (ordered, shipped, received)
  - Receive button (marks as received, creates spools)

#### Frontend - Routes
- [ ] `src/routes/reorder/dashboard.tsx`
- [ ] `src/routes/suppliers/index.tsx`
- [ ] `src/routes/purchases/index.tsx`
- [ ] `src/routes/purchases/new.tsx`

---

### Success Criteria

- [ ] Daily background job calculates usage rates
- [ ] Low stock alerts appear on dashboard
- [ ] Can create purchase order from alert
- [ ] Receiving purchase creates new spools automatically
- [ ] Reorder point calculations are accurate
- [ ] Email notifications sent for low stock (optional)

---

## Phase 6: QR Code Scanning (Weeks 13-14)

### Goals
- QR code generation per spool
- Printable labels
- Mobile camera scanning (PWA)
- Quick update workflow

### Deliverables
- [ ] Backend: QR code generation endpoint
- [ ] Backend: QR code deep link handling
- [ ] Frontend: Label generator + print view
- [ ] Frontend: QR scanner (camera access)
- [ ] Frontend: Quick update form

---

### Tasks Checklist

#### Backend - Services
- [ ] Update `app/services/qr_generator.py`
  - `generate_qr_code(spool_id, tenant_id)` → base64 image
  - `generate_deep_link(spool_id)` → URL (nozzly.app/spool/update/FIL-001)

#### Backend - API Endpoints
- [ ] `GET /api/v1/spools/{id}/qr` - Get QR code image
- [ ] `GET /api/v1/spools/{id}/label` - Get printable label (PDF)
- [ ] `POST /api/v1/spools/qr/bulk` - Generate QR codes for multiple spools

#### Frontend - Components
- [ ] `src/components/inventory/QRScanner.tsx`
  - Camera access (getUserMedia API)
  - jsQR library for scanning
  - Decode QR → extract spool ID → navigate to update form
- [ ] `src/components/inventory/LabelGenerator.tsx`
  - Label template (spool ID, material, color)
  - QR code embedded
  - Print stylesheet
  - Bulk generation option
- [ ] `src/components/inventory/QuickUpdateForm.tsx`
  - Pre-filled with spool info
  - Weight input (focus on load)
  - Optional notes
  - Submit → update + redirect

#### Frontend - Routes
- [ ] `src/routes/scan.tsx` (QR scanner page)
- [ ] `src/routes/spool/update/$spoolId.tsx` (quick update)
- [ ] `src/routes/labels/generate.tsx` (label generator)

#### Frontend - PWA Features
- [ ] Update `manifest.json` (camera permission)
- [ ] Test camera access on mobile devices
- [ ] Offline support for recently scanned spools

---

### Success Criteria

- [ ] Can generate QR code for any spool
- [ ] QR code includes deep link to spool update form
- [ ] Can print labels (individually or bulk)
- [ ] Camera opens on mobile when scanning
- [ ] Scanning QR navigates to correct spool
- [ ] Quick update form submits successfully
- [ ] Works offline (with service worker)

---

## Phase 7: Dashboard & Analytics (Weeks 15-16)

### Goals
- Executive dashboard
- Sales trends visualization
- Inventory analytics
- Profit tracking
- Exportable reports

### Deliverables
- [ ] Backend: Analytics API endpoints
- [ ] Frontend: Dashboard page with widgets
- [ ] Frontend: Charts (Recharts)
- [ ] Frontend: Report exports (CSV, PDF)

---

### Tasks Checklist

#### Backend - Services
- [ ] Create `app/services/analytics.py`
  - `get_inventory_summary(tenant_id)` → total value, count, low stock count
  - `get_sales_trends(tenant_id, period)` → daily/weekly/monthly sales
  - `get_profit_by_product(tenant_id, period)` → top/bottom products
  - `get_profit_by_channel(tenant_id, period)` → channel comparison
  - `get_material_usage_trends(tenant_id, period)` → usage over time
  - `get_inventory_turnover(tenant_id)` → turnover ratio

#### Backend - API Endpoints
- [ ] `GET /api/v1/analytics/dashboard` - All dashboard widgets in one call
- [ ] `GET /api/v1/analytics/sales-trends?period=30d` - Sales over time
- [ ] `GET /api/v1/analytics/profit-by-product?period=30d` - Product profitability
- [ ] `GET /api/v1/analytics/profit-by-channel?period=30d` - Channel profitability
- [ ] `GET /api/v1/analytics/inventory-value` - Current inventory value
- [ ] `GET /api/v1/analytics/material-usage?period=90d` - Usage trends
- [ ] `GET /api/v1/reports/sales?start=&end=&format=csv` - Export sales report
- [ ] `GET /api/v1/reports/inventory?format=csv` - Export inventory snapshot
- [ ] `GET /api/v1/reports/profit?start=&end=&format=csv` - Export profit report

#### Frontend - Components
- [ ] `src/components/dashboard/Dashboard.tsx` (layout)
- [ ] `src/components/dashboard/InventoryValueWidget.tsx`
  - Total value (sum of current_weight × cost_per_gram)
  - Total spool count
  - Low stock count (badge)
- [ ] `src/components/dashboard/SalesTrendChart.tsx`
  - Line chart (Recharts)
  - Daily, weekly, monthly toggle
  - Revenue vs profit lines
- [ ] `src/components/dashboard/TopProductsWidget.tsx`
  - Bar chart (profit by product)
  - Top 5 + bottom 5
- [ ] `src/components/dashboard/ChannelComparisonWidget.tsx`
  - Pie chart (revenue by channel)
  - Table with metrics
- [ ] `src/components/dashboard/MaterialUsageChart.tsx`
  - Stacked bar chart (usage by material type)
  - Identifies popular materials
- [ ] `src/components/dashboard/LowStockWidget.tsx`
  - Quick list of low stock items
  - Link to reorder dashboard
- [ ] `src/components/reports/ExportButton.tsx`
  - Dropdown: CSV, PDF
  - Date range picker
  - Report type selector

#### Frontend - Routes
- [ ] `src/routes/dashboard.tsx` (main dashboard)
- [ ] `src/routes/analytics/sales.tsx` (detailed sales analysis)
- [ ] `src/routes/analytics/products.tsx` (product performance)
- [ ] `src/routes/analytics/inventory.tsx` (inventory analytics)
- [ ] `src/routes/reports.tsx` (report generator)

---

### Success Criteria

- [ ] Dashboard loads in <2 seconds
- [ ] Charts render correctly with real data
- [ ] Can toggle time periods (7d, 30d, 90d, 1y)
- [ ] Can export reports to CSV
- [ ] Inventory value is accurate
- [ ] Top/bottom products identified correctly
- [ ] Dashboard is mobile-responsive

---

## Phase 8: Integrations (Weeks 17-20+)

### Goals
- Marketplace API integrations (optional)
- Slicer integration (optional)
- Printer integration (optional)
- Email notifications

### Deliverables
- [ ] Etsy API integration (orders auto-import)
- [ ] eBay API integration (orders auto-import)
- [ ] Shopify webhook integration
- [ ] .gcode parser (extract weight/time)
- [ ] OctoPrint API integration
- [ ] Bambu Connect integration
- [ ] Email notification system

---

### Tasks Checklist

#### Backend - Integrations

**Etsy Integration**
- [ ] Create `app/integrations/etsy.py`
  - OAuth setup
  - Fetch orders endpoint
  - Map Etsy order → Nozzly order
- [ ] Background job: Sync Etsy orders daily

**eBay Integration**
- [ ] Create `app/integrations/ebay.py`
  - OAuth setup
  - Fetch orders endpoint
- [ ] Background job: Sync eBay orders daily

**Shopify Integration**
- [ ] Create `app/integrations/shopify.py`
  - Webhook receiver (orders/create)
  - Map Shopify order → Nozzly order

**Slicer Integration**
- [ ] Create `app/integrations/gcode_parser.py`
  - Parse .gcode file
  - Extract: material usage (grams), print time, layer height
  - API endpoint: `POST /api/v1/integrations/parse-gcode`

**Printer Integration**
- [ ] Create `app/integrations/octoprint.py`
  - Fetch print job status
  - Update order status based on print completion
- [ ] Create `app/integrations/bambu.py`
  - Bambu Connect API integration (similar to OctoPrint)

**Email Notifications**
- [ ] Configure SMTP settings
- [ ] Create `app/services/notifications.py`
  - `send_low_stock_alert(user, items)`
  - `send_order_status_update(customer, order)`
  - `send_purchase_received(user, purchase)`

#### Frontend - Integrations UI
- [ ] `src/routes/settings/integrations.tsx`
  - Etsy: Connect account, sync status
  - eBay: Connect account, sync status
  - Shopify: Webhook URL, test connection
  - OctoPrint: Server URL, API key
  - Bambu: Account credentials
  - Email: SMTP settings test

---

### Success Criteria

- [ ] Etsy orders auto-import daily
- [ ] Shopify orders import via webhook in real-time
- [ ] .gcode file upload extracts material usage
- [ ] Low stock email notifications sent
- [ ] OctoPrint/Bambu print status updates order status

---

## Post-MVP: Future Enhancements

### Nice-to-Have Features

1. **Multi-User Collaboration**
   - Real-time updates (WebSockets)
   - Activity feed
   - User permissions (per-product, per-spool)

2. **Advanced Analytics**
   - Predictive analytics (ML-based demand forecasting)
   - Seasonal trends identification
   - Customer lifetime value (CLV)

3. **Customer Management**
   - Full CRM features
   - Customer orders history
   - Repeat customer identification
   - Email marketing integration

4. **Mobile Native App**
   - React Native app
   - Offline-first architecture
   - Push notifications

5. **White-Label / Self-Hosting**
   - Custom branding per tenant
   - Self-hosted deployment guides
   - Helm chart for easy k8s deployment

6. **Marketplace Features**
   - Public product catalog (optional)
   - Cross-tenant marketplace
   - Product templates (community-shared)

7. **Advanced Reorder Management**
   - Automatic purchase order creation
   - Supplier API integration (auto-order)
   - Price tracking (buy when price drops)

8. **Tax & Accounting**
   - Tax calculation per region
   - QuickBooks/Xero integration
   - Automated tax reports

---

## Development Best Practices

### Code Quality
- Backend: Black formatting, Ruff linting, MyPy type checking
- Frontend: Prettier formatting, ESLint, TypeScript strict mode
- Pre-commit hooks for linting/formatting

### Testing
- Minimum 80% test coverage
- Write tests alongside features (not after)
- Integration tests for critical paths
- E2E tests for user workflows (Playwright - optional)

### Version Control
- Feature branches: `feature/phase-1-inventory`
- Commit messages: Conventional Commits format
- Pull requests: Require CI pass + manual review

### Documentation
- Update API docs when adding endpoints (OpenAPI auto-generated)
- Update README when adding features
- Write ADRs for significant architecture decisions

### Observability
- Add OpenTelemetry spans for new business logic
- Create Grafana dashboards for new features
- Set up alerts for new critical paths

---

## Timeline Summary

| Phase | Weeks | Description |
|-------|-------|-------------|
| Phase 0 | 1-2 | Foundation (infrastructure, scaffolding) |
| Phase 1 | 3-4 | Core inventory management |
| Phase 2 | 5-6 | Product catalog & costing |
| Phase 3 | 7-8 | Pricing engine |
| Phase 4 | 9-10 | Sales tracking & deduction |
| Phase 5 | 11-12 | Reorder management |
| Phase 6 | 13-14 | QR code scanning |
| Phase 7 | 15-16 | Dashboard & analytics |
| Phase 8 | 17-20+ | Integrations (optional) |

**Total: 16-20 weeks (4-5 months)** at 10-15 hours/week

---

## Success Metrics

### Technical Metrics
- [ ] 80%+ test coverage
- [ ] <2s page load times
- [ ] <100ms API response times (p95)
- [ ] Zero SQL N+1 queries
- [ ] All critical paths have distributed tracing

### Business Metrics
- [ ] Can track 100+ spools without performance degradation
- [ ] Can manage 50+ products with complex BOMs
- [ ] Can process 20+ orders/day efficiently
- [ ] Reorder alerts reduce stockouts by 90%

### User Experience Metrics
- [ ] Can create a new spool in <30 seconds
- [ ] Can add a product to catalog in <2 minutes
- [ ] Can calculate pricing for 5 channels in <10 seconds
- [ ] Can scan QR code and update weight in <15 seconds

---

*Last Updated: 2025-10-29*
*Document Version: 1.0*
