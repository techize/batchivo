# Production Run System - Implementation PRD

## Overview

Implement the complete Production Run system for tracking actual 3D printing manufacturing data. The database layer is complete; this PRD covers API endpoints, business logic, and UI components.

## Database Status

✅ **Already Complete:**
- Database schema migration (`a8d3e5f7g9h1_add_production_runs_tables.py`)
- SQLAlchemy models (`ProductionRun`, `ProductionRunItem`, `ProductionRunMaterial`)
- Design document (`docs/PRODUCTION_RUNS.md`)

## Implementation Scope

### Phase 1: Backend API Layer

**1. Pydantic Schemas**
- Create request/response schemas for production runs
- Create nested schemas for items and materials
- Add validation for status transitions, weights, quantities
- Include computed fields for variance calculations

**2. Service Layer (Business Logic)**
- Production run CRUD operations
- Run number generation (format: `{tenant_short}-YYYYMMDD-NNN`)
- Inventory transaction creation on run completion
- Variance calculation and analysis
- Quality tracking and reprint linking

**3. API Endpoints**

Production Runs:
- `POST /api/v1/production-runs` - Create new run
- `GET /api/v1/production-runs` - List runs with filters (status, date range, product, spool)
- `GET /api/v1/production-runs/{id}` - Get run details with items and materials
- `PUT /api/v1/production-runs/{id}` - Update run
- `POST /api/v1/production-runs/{id}/complete` - Complete run and create inventory transactions
- `DELETE /api/v1/production-runs/{id}` - Delete run (soft delete)

Production Run Items:
- `POST /api/v1/production-runs/{id}/items` - Add item to run
- `PUT /api/v1/production-runs/{id}/items/{item_id}` - Update item quantities
- `DELETE /api/v1/production-runs/{id}/items/{item_id}` - Remove item from run

Production Run Materials:
- `POST /api/v1/production-runs/{id}/materials` - Add material/spool to run
- `PUT /api/v1/production-runs/{id}/materials/{mat_id}` - Update material weights
- `DELETE /api/v1/production-runs/{id}/materials/{mat_id}` - Remove material

Analytics:
- `GET /api/v1/production-runs/variance-report` - Variance analysis across runs
- `GET /api/v1/products/{id}/production-history` - Production history for product
- `GET /api/v1/spools/{id}/production-usage` - Which runs used this spool

**4. Inventory Integration**
- On run completion: Create `inventory_transactions` records
- Deduct actual filament from spool `current_weight`
- Support rollback if run status changes
- Transaction type: 'usage' with reference to production run

**5. Business Rules**
- Only 'in_progress' runs can be modified
- Completed runs are immutable (except status change to failed/cancelled)
- Run number auto-generated and unique per tenant per day
- Variance calculation: `(actual - estimated) / estimated * 100`
- Quality rating must be 1-5 if provided
- Reprint must reference original run ID

### Phase 2: Frontend UI Components

**1. Navigation & Layout**
- Add "Production" menu item in sidebar
- Create production runs route `/production-runs`
- Add nested routes for detail and forms

**2. Production Run List Page**

Features:
- Data table with columns: Run #, Date, Products, Status, Variance %, Actions
- Status badges: in_progress (blue), completed (green), failed (red), cancelled (gray)
- Variance color coding: >10% over (red), <-10% under (green), within ±10% (yellow)
- Filters: Status, Date range, Product selector, Spool selector
- Search by run number
- Pagination
- Sort by date, run number, variance
- Actions: View, Edit (if in_progress), Complete, Delete

**3. Create Production Run Form**

Multi-step wizard:
- Step 1: Basic Info
  - Auto-generated run number (read-only preview)
  - Start date/time (default: now)
  - Printer name (text input or dropdown of saved printers)
  - Slicer software (text input or dropdown)
  - Estimated print time (hours)
  - Bed/nozzle temperatures

- Step 2: Items to Print
  - Product selector (multi-select or add rows)
  - Quantity per product
  - Bed position (optional, for organization)
  - Display estimated costs from product BOM

- Step 3: Materials
  - For each required material/color (from selected products):
    - Spool selector (filtered by material type/color)
    - Estimated weight (from product BOM × quantity)
    - Estimated purge (for multi-color prints)
  - Total estimated filament display
  - Total estimated purge display

- Step 4: Review & Submit
  - Summary of all entered data
  - Validation errors displayed
  - Submit button creates run with status 'in_progress'

**4. Production Run Detail Page**

Sections:
- Header: Run number, status badge, started date, duration
- Quick actions: Complete Run, Edit, Delete

- Run Overview Card:
  - Printer name
  - Slicer software
  - Started/Completed timestamps
  - Duration (actual vs estimated)
  - Temperatures
  - Quality rating (stars)
  - Notes

- Items Printed Table:
  - Product (with link)
  - Quantity planned
  - Successful quantity
  - Failed quantity
  - Success rate %
  - Estimated cost
  - Bed position

- Material Usage Table:
  - Spool (with link and color swatch)
  - Estimated weight
  - Estimated purge
  - Actual weight
  - Actual purge
  - Variance (grams and %)
  - Cost

- Variance Summary:
  - Total estimated vs actual filament
  - Total estimated vs actual purge
  - Overall variance %
  - Visual chart (bar chart or gauge)

**5. Complete Production Run Form**

Form to finalize run:
- For each material:
  - Option 1: "Use Estimate" button (copies estimated to actual)
  - Option 2: Enter spool weight before/after (auto-calculates)
  - Option 3: Manually enter actual weight used
  - Actual purge amount

- For each item:
  - Successful quantity (default: planned quantity)
  - Failed quantity
  - If failures exist, prompt for waste reason

- Overall quality rating (1-5 stars)
- Quality notes (textarea)
- Completion notes (textarea)

- Review variance before submit:
  - Show material-by-material variance
  - Highlight high variance (>10%)
  - Warning if variance is significant

- Submit action:
  - Validates all required fields
  - Creates inventory transactions
  - Updates spool weights
  - Sets status to 'completed'
  - Shows success message with variance summary

**6. Edit Production Run Form**

Only for 'in_progress' runs:
- Allow editing all fields except run number
- Can add/remove items and materials
- Cannot edit if status is 'completed', 'failed', or 'cancelled'

**7. Variance Analysis Dashboard** (Optional - Phase 2.5)

Charts and insights:
- Line chart: Estimated vs Actual over time (by run date)
- Bar chart: Variance by product (which products are most off)
- Table: Products with highest variance (candidates for BOM update)
- Recommendations: "Product X is consistently 15% over estimate - consider updating BOM"

### Phase 3: Integration & Polish

**1. Product Integration**
- In Product detail page: Add "Production History" tab
- Show table of production runs that used this product
- Display average actual cost vs estimated cost

**2. Spool Integration**
- In Spool detail page: Add "Production Usage" tab
- Show table of production runs that used this spool
- Display total grams used across all runs

**3. Inventory Transaction Linking**
- In Inventory Transactions list: Add "Source" column
- Link production runs from transactions
- Filter by transaction type 'usage'

**4. Reprint Workflow**
- On production run detail page with failed items:
- "Create Reprint" button
- Pre-populates new run with failed items
- Links to original run via `original_run_id`

**5. Error Handling**
- Handle case where spool doesn't have enough weight
- Validate quantities (successful + failed ≤ planned)
- Prevent completing run without actual weights
- Show helpful error messages

## Technical Requirements

**Backend:**
- FastAPI 0.109+
- SQLAlchemy async queries with tenant isolation
- Pydantic v2 for validation
- OpenTelemetry spans for business operations
- Unit tests for service layer
- Integration tests for API endpoints

**Frontend:**
- React 18 + TypeScript
- TanStack Query for data fetching
- TanStack Router for routing
- shadcn/ui components (Table, Form, Dialog, Card, Badge)
- Zod for client-side validation
- React Hook Form for form management
- Recharts for variance visualizations

**Multi-Tenancy:**
- All queries include tenant_id filter
- Run numbers unique per tenant
- Cannot access other tenant's production runs

**Performance:**
- Paginated lists (default 20 per page)
- Eager load related items and materials on detail view
- Index on production_runs.started_at for date filtering
- Cache tenant settings for run number generation

## Acceptance Criteria

**Backend API:**
- [ ] All CRUD endpoints functional and tested
- [ ] Run number generation follows format: `{tenant_short}-YYYYMMDD-NNN`
- [ ] Inventory transactions created on run completion
- [ ] Spool weights deducted correctly
- [ ] Variance calculations accurate
- [ ] Multi-tenant isolation enforced
- [ ] OpenTelemetry instrumentation added
- [ ] 80%+ test coverage

**Frontend UI:**
- [ ] Production run list page with filters and search
- [ ] Create production run wizard (4 steps)
- [ ] Production run detail page with all data sections
- [ ] Complete production run form with variance preview
- [ ] Edit production run form (in_progress only)
- [ ] Status badges and variance color coding
- [ ] Responsive design (desktop and tablet)
- [ ] Loading states and error handling

**Integration:**
- [ ] Product detail shows production history
- [ ] Spool detail shows production usage
- [ ] Inventory transactions link to production runs
- [ ] Reprint workflow creates linked run

**User Experience:**
- [ ] Intuitive multi-step form
- [ ] Clear variance indicators
- [ ] Easy "Use Estimate" shortcut for weights
- [ ] Helpful validation messages
- [ ] Success feedback on completion

## Implementation Order

**Week 1: Backend Foundation**
1. Create Pydantic schemas
2. Implement service layer with business logic
3. Add run number generation
4. Create CRUD API endpoints
5. Write unit tests

**Week 2: Backend Completion**
6. Implement inventory integration
7. Add variance calculation endpoints
8. Create analytics endpoints
9. Integration testing
10. OpenTelemetry instrumentation

**Week 3: Frontend Core**
11. Create route structure
12. Build production run list page
13. Implement filters and search
14. Create detail page layout
15. Add status badges and variance display

**Week 4: Frontend Forms**
16. Build create run wizard (4 steps)
17. Implement complete run form
18. Add edit run form
19. Integrate with backend API
20. Add form validation

**Week 5: Integration & Polish**
21. Integrate with Product pages
22. Integrate with Spool pages
23. Link inventory transactions
24. Build reprint workflow
25. Add variance dashboard (optional)
26. Final testing and bug fixes

## Dependencies

**Required (Already Complete):**
- ✅ Product model and API
- ✅ Spool model and API
- ✅ Inventory transactions model
- ✅ Tenant authentication
- ✅ Production run database schema and models

**Nice-to-Have (Future):**
- .gcode parser for auto-population (Phase 2)
- Printer integrations (OctoPrint, Bambu) (Phase 3)
- Photo uploads for quality tracking (Phase 3)

## Success Metrics

- User can create production run in <2 minutes
- User can complete run and see variance in <3 minutes
- 100% of actual filament usage tracked
- Variance insights lead to BOM improvements
- Production history provides cost accuracy for pricing

## Notes

- This is a core feature for production management
- Accuracy is critical for cost analysis and inventory
- UI should be fast and intuitive for daily use
- Mobile support can be added later (desktop-first)
- Consider bulk operations in future (complete multiple runs at once)
