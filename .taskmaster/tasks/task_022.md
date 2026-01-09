# Task ID: 22

**Title:** Create Dashboard Home Page with Analytics

**Status:** pending

**Dependencies:** 4 ✓, 9 ✓

**Priority:** high

**Description:** Build comprehensive dashboard landing page with summary cards, active production panel, inventory alerts, activity feed, performance charts, and quick actions with supporting backend API endpoints

**Details:**

Create frontend/src/pages/DashboardHome.tsx to replace the current simple Dashboard.tsx (currently just shows SpoolList). This should be the main authenticated landing page after login.

**Frontend Components:**

1. **Summary Cards Row** (4 cards using shadcn/ui Card):
   - Active Prints: Count of in_progress production runs with icon
   - Today's Completed: Completed runs today with success/failed breakdown
   - Low Stock Alerts: Count of spools below reorder point (threshold TBD)
   - Success Rate: Overall percentage (successful items / total items) with color coding

2. **Active Production Panel**:
   - Table showing in_progress production runs
   - Columns: Run Number, Started, Products, Status Progress, Quick Actions
   - Link to full production run detail pages
   - Empty state: "No active production runs" with "Start New Run" button

3. **Inventory Alerts Section**:
   - List of spools with current_weight_g below threshold (e.g., <10% of initial weight)
   - Show: Spool ID, Material, Color, Current Weight, Alert Badge
   - Link to spool detail/reorder workflow
   - Empty state: "All spools adequately stocked"

4. **Recent Activity Feed**:
   - Display recent inventory_transactions (last 10-20)
   - Show: Type badge (PURCHASE, USAGE, ADJUSTMENT, WASTE), timestamp, description, amount
   - Link to related production run or spool
   - Use timeline-style layout with transaction type icons

5. **Performance Charts** (using Recharts):
   - Production Success Rate Trend (7-day or 30-day line chart)
   - Material Usage by Type (pie chart or bar chart)
   - Daily Production Volume (bar chart showing completed items per day)
   - Responsive chart containers with loading skeletons

6. **Quick Actions Section**:
   - Button grid for common actions:
     - Start Production Run
     - Add New Spool
     - Add Consumable
     - View All Inventory
     - View Reports (future)
   - Use shadcn/ui Button with icons from lucide-react

**Backend API Endpoints** (create backend/app/api/v1/dashboard.py):

```python
@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get dashboard summary statistics.
    Returns:
    - active_prints: Count of in_progress production runs
    - completed_today: Count of runs completed today
    - failed_today: Count of runs failed today
    - low_stock_count: Count of spools below threshold
    - success_rate: Overall production success rate (0-100)
    """

@router.get("/dashboard/active-production")
async def get_active_production(
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get active production runs for dashboard.
    Returns list with run_number, started_at, products summary, progress.
    """

@router.get("/dashboard/low-stock")
async def get_low_stock_spools(
    threshold_percent: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get spools below stock threshold.
    Calculate: (current_weight_g / initial_weight_g) * 100 < threshold_percent
    Returns: spool_id, material_type, color, current_weight_g, initial_weight_g, percent_remaining
    """

@router.get("/dashboard/recent-activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get recent inventory transactions for activity feed.
    Returns: transaction_type, created_at, spool_id, amount_grams, reference (production_run_id if applicable)
    Ordered by created_at DESC
    """

@router.get("/dashboard/performance-charts")
async def get_performance_data(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
):
    """
    Get performance chart data.
    Returns:
    - success_rate_trend: Array of {date, success_rate} for last N days
    - material_usage: Array of {material_type, total_grams} for period
    - daily_production: Array of {date, items_completed, items_failed} for period
    """
```

**Data Fetching Strategy:**
- Use TanStack Query with separate queries for each dashboard section
- Implement skeleton loaders for each section during loading
- Auto-refresh dashboard data every 60 seconds using refetchInterval
- Error boundaries for each section to prevent whole dashboard from failing

**Routing:**
- Update frontend/src/main.tsx to use DashboardHome as the root authenticated page (/)
- Move SpoolList to /inventory/spools route
- Keep AppLayout wrapper for consistent navigation

**Styling:**
- Grid layout: 4-column for summary cards, 2-column for main content sections
- Responsive: Stack to single column on mobile
- Use shadcn/ui components: Card, Badge, Button, Separator, Alert
- Charts should be height-constrained (max 300px) with responsive width

**Dependencies:**
- Needs recharts package added to frontend/package.json
- Backend depends on inventory_transaction model/service (Task 10)
- Production run endpoints already exist (Task 9)
- Spool data model already exists

**Test Strategy:**

**Frontend Tests:**
- Component rendering tests for each dashboard section
- Test loading states with skeleton loaders
- Test empty states for each section (no active runs, no alerts, etc.)
- Test error states with error boundaries
- Test chart rendering with mock data
- Test quick action button navigation
- Test auto-refresh functionality (verify refetchInterval works)

**Backend Tests:**
- Unit tests for dashboard summary calculations (count queries, success rate formula)
- Test low stock calculation with various threshold values
- Test recent activity pagination and ordering
- Test performance chart data aggregation for different date ranges
- Integration tests for all dashboard endpoints
- Test tenant isolation for all dashboard queries
- Test with no data (new tenant) returns empty results properly

**Manual Testing:**
- Verify dashboard loads quickly (<2 seconds for all sections)
- Check responsive layout on mobile, tablet, desktop
- Verify auto-refresh updates data without full page reload
- Test with varying data volumes (0 runs, 100+ runs, etc.)
- Verify chart tooltips and interactions work correctly
- Test quick action buttons navigate to correct pages
- Verify activity feed links work (to production runs, spools)

## Subtasks

### 22.1. Create Backend Dashboard API Endpoints

**Status:** pending
**Dependencies:** None

Implement backend/app/api/v1/dashboard.py with all dashboard data endpoints: summary statistics, active production runs, low stock spools, recent activity feed, and performance chart data.

**Details:**

Create new API router at backend/app/api/v1/dashboard.py with the following endpoints:

1. GET /dashboard/summary - Returns active_prints count (in_progress status), completed_today count, failed_today count, low_stock_count (spools below threshold), and success_rate percentage (successful items / total items across all completed runs).

2. GET /dashboard/active-production - Returns list of in_progress production runs with run_number, started_at, products summary (from items relationship), and progress info. Use selectinload for items relationship.

3. GET /dashboard/low-stock - Query spools where (current_weight_g / initial_weight_g) * 100 < threshold_percent (default 10%). Return spool_id, material_type, color, brand, current_weight_g, initial_weight_g, percent_remaining.

4. GET /dashboard/recent-activity - Query inventory_transactions table ordered by created_at DESC, limit parameter (default 20). Return transaction_type, created_at, spool_id, weight_change (as amount_grams), production_run_id (as reference). Use eager loading for spool relationship.

5. GET /dashboard/performance-charts - Query for last N days (default 7): success_rate_trend (group by date, calculate success rate per day), material_usage (group by material_type from spools via production_run_materials, sum actual usage), daily_production (group by date, count successful and failed items from production_run_items).

All endpoints must include tenant isolation via CurrentTenant dependency. Use async/await with AsyncSession. Add proper error handling and type hints. Register router in backend/app/api/v1/__init__.py.

### 22.2. Create Backend Failure Analytics Endpoint

**Status:** pending
**Dependencies:** 22.1

Add GET /dashboard/failure-analytics endpoint to provide failure breakdown by reason, most common failures, and failure trends over time.

**Details:**

Add to backend/app/api/v1/dashboard.py:

GET /dashboard/failure-analytics - Query production_runs table where status='failed'. Parameters: days (default 30, range 1-90).

Returns:
1. failure_by_reason: Array of {reason: string, count: number, percentage: number} - Group by waste_reason field, calculate percentages of total failures.

2. most_common_failures: Top 5 failure reasons with counts, sorted by frequency.

3. failure_trends: Array of {date: string, count: number, reasons: {reason: count}} - Daily failure counts grouped by date, including breakdown by reason per day.

4. total_failures: Total count of failed runs in period.

5. failure_rate: Percentage of failed runs vs total runs (failed / (completed + failed)) * 100.

Use SQLAlchemy groupby and aggregate functions. Filter by tenant_id and date range (created_at >= today - days). Handle null waste_reason as 'Unknown'. Add proper type annotations and error handling.

### 22.3. Install Recharts Package and Configure TypeScript Types

**Status:** pending
**Dependencies:** None

Add recharts charting library to frontend dependencies and configure TypeScript types for chart components.

**Details:**

Run: npm install recharts --save

Update frontend/package.json to include recharts (should auto-add to dependencies).

Verify TypeScript types are included (recharts ships with its own types). If types are missing, run: npm install --save-dev @types/recharts

Create frontend/src/types/dashboard.ts with TypeScript interfaces for all dashboard API responses:
- DashboardSummary (active_prints, completed_today, failed_today, low_stock_count, success_rate)
- ActiveProductionRun (id, run_number, started_at, products_summary, status)
- LowStockSpool (id, spool_id, material_type, color, brand, current_weight_g, initial_weight_g, percent_remaining)
- RecentActivityItem (id, transaction_type, created_at, spool_id, amount_grams, reference)
- PerformanceChartData (success_rate_trend, material_usage, daily_production)
- FailureAnalytics (failure_by_reason, most_common_failures, failure_trends, total_failures, failure_rate)

Include proper typing for chart data arrays (date strings, numeric values).

### 22.4. Create Dashboard API Client Functions

**Status:** pending
**Dependencies:** 22.3

Implement API client functions in frontend/src/lib/api/dashboard.ts for all dashboard endpoints with TanStack Query integration.

**Details:**

Create frontend/src/lib/api/dashboard.ts with API client functions using axios:

1. getDashboardSummary() - GET /api/v1/dashboard/summary
2. getActiveProduction() - GET /api/v1/dashboard/active-production
3. getLowStockSpools(thresholdPercent: number = 10) - GET /api/v1/dashboard/low-stock
4. getRecentActivity(limit: number = 20) - GET /api/v1/dashboard/recent-activity
5. getPerformanceCharts(days: number = 7) - GET /api/v1/dashboard/performance-charts
6. getFailureAnalytics(days: number = 30) - GET /api/v1/dashboard/failure-analytics

All functions should:
- Use the existing apiClient instance from frontend/src/lib/api/client.ts
- Include proper TypeScript return types using interfaces from dashboard.ts
- Handle errors with try/catch and appropriate error messages
- Include JSDoc comments with parameter descriptions

Create React Query hooks in same file:
- useDashboardSummary() - refetchInterval: 60000 (60 seconds)
- useActiveProduction() - refetchInterval: 30000
- useLowStockSpools(threshold) - staleTime: 300000 (5 minutes)
- useRecentActivity(limit) - refetchInterval: 60000
- usePerformanceCharts(days) - staleTime: 300000
- useFailureAnalytics(days) - staleTime: 300000

Use proper query keys: ['dashboard', 'summary'], ['dashboard', 'active-production'], etc.

### 22.5. Create Dashboard UI Components for Summary Cards and Charts

**Status:** pending
**Dependencies:** 22.3

Build reusable dashboard UI components: SummaryCard, PerformanceChart, FailureChart with loading skeletons and empty states.

**Details:**

Create frontend/src/components/dashboard/SummaryCard.tsx:
- Props: title, value, icon (from lucide-react), trend (optional), color scheme
- Use shadcn/ui Card component
- Display large value with subtitle/description
- Show loading skeleton state (use shimmer effect)
- Responsive sizing (adapts to grid layout)

Create frontend/src/components/dashboard/PerformanceChart.tsx:
- Props: data, chartType ('line' | 'bar' | 'pie'), title, height (default 300px)
- Wrapper for Recharts components (LineChart, BarChart, PieChart)
- Includes ResponsiveContainer, Tooltip, Legend
- Color scheme matches app theme
- Loading skeleton (gray placeholder with pulse animation)
- Empty state: "No data available" message with icon

Create frontend/src/components/dashboard/FailureChart.tsx:
- Specialized component for failure analytics
- Props: failureData (from failure analytics endpoint)
- Shows pie chart for failure breakdown by reason
- Shows bar chart for failure trends over time
- Color-coded by failure severity/category
- Includes legend with percentages

Create frontend/src/components/dashboard/LoadingSkeleton.tsx:
- Reusable skeleton component for dashboard sections
- Props: rows, columns, height
- Uses shadcn/ui Skeleton component or custom pulse animation

All components should:
- Use TypeScript with proper prop types
- Include JSDoc comments
- Handle responsive breakpoints (Tailwind classes)
- Match existing shadcn/ui design system

### 22.6. Create Dashboard Sections: Active Production and Inventory Alerts

**Status:** pending
**Dependencies:** 22.4, 22.5

Build ActiveProductionPanel and InventoryAlertsSection components with tables/lists and quick action links.

**Details:**

Create frontend/src/components/dashboard/ActiveProductionPanel.tsx:
- Use useActiveProduction() hook to fetch data
- Display table with columns: Run Number (link to detail), Started (relative time), Products (summary text), Status Progress (progress bar), Quick Actions (buttons)
- Quick Actions: View Details (link to /production-runs/{id}), Complete Run button (if applicable)
- Empty state: Card with "No active production runs" message and "Start New Run" button (links to /production-runs/new)
- Loading state: Skeleton table rows
- Use shadcn/ui Table, Badge, Button, Progress components

Create frontend/src/components/dashboard/InventoryAlertsSection.tsx:
- Use useLowStockSpools(10) hook with 10% threshold
- Display list/table with: Spool ID (link to spool detail), Material + Color, Current Weight, Alert Badge (color-coded by severity: <5% red, 5-10% yellow)
- Quick Actions: Reorder button (future), View Spool Details (link)
- Empty state: "All spools adequately stocked" with green checkmark icon
- Loading state: Skeleton list items
- Use shadcn/ui Alert, Badge, Card components
- Sort by percent_remaining ascending (lowest stock first)

Both components:
- Include section header with icon (from lucide-react)
- Use Separator component between sections
- Handle errors with error boundary fallback
- Responsive layout (stack on mobile)

### 22.7. Create Dashboard Sections: Activity Feed and Quick Actions

**Status:** pending
**Dependencies:** 22.4, 22.5

Build RecentActivityFeed and QuickActionsGrid components with transaction list and action buttons.

**Details:**

Create frontend/src/components/dashboard/RecentActivityFeed.tsx:
- Use useRecentActivity(20) hook
- Display timeline-style list with:
  - Transaction type badge (color-coded: PURCHASE=green, USAGE=blue, ADJUSTMENT=yellow, WASTE=red)
  - Icon for each transaction type (from lucide-react: ShoppingCart, Minus, Settings, Trash2)
  - Timestamp (relative: "5 minutes ago", "2 hours ago")
  - Description text ("Used 45g from spool FIL-001 in production run")
  - Amount with +/- indicator
  - Link to related production run or spool if applicable
- Limit display to 10 items with "View All" link at bottom
- Loading state: Skeleton list items
- Empty state: "No recent activity"
- Use shadcn/ui Card, Badge components with custom timeline styling

Create frontend/src/components/dashboard/QuickActionsGrid.tsx:
- Grid of 4-6 action buttons (2 columns on mobile, 3-4 on desktop)
- Actions:
  1. Start Production Run (link to /production-runs/new, icon: Play)
  2. Add New Spool (opens AddSpoolDialog, icon: Plus)
  3. Add Consumable (opens AddConsumableDialog, icon: Package)
  4. View All Inventory (link to /inventory, icon: Archive)
  5. View Reports (link to /reports - future, icon: BarChart3)
  6. Settings (link to /settings - future, icon: Settings)
- Each button: Large icon, label below, hover effect
- Use shadcn/ui Button with variant="outline"
- Responsive grid: grid-cols-2 md:grid-cols-3 lg:grid-cols-4

Both components:
- Include section header
- Handle loading and error states
- Use consistent spacing and layout

### 22.8. Create Main DashboardHome Page and Update Routing

**Status:** pending
**Dependencies:** 22.5, 22.6, 22.7

Assemble all dashboard components into DashboardHome page, add performance charts and failure analytics sections, and update main routing to use DashboardHome as authenticated landing page.

**Details:**

Create frontend/src/pages/DashboardHome.tsx:
- Import AppLayout wrapper
- Fetch all dashboard data using hooks from dashboard API client
- Layout structure:
  1. Summary Cards Row (grid-cols-1 sm:grid-cols-2 lg:grid-cols-4)
     - Active Prints card (icon: Activity)
     - Today's Completed card (icon: CheckCircle, show success/failed breakdown)
     - Low Stock Alerts card (icon: AlertTriangle)
     - Success Rate card (icon: TrendingUp, color-coded: >90% green, 70-90% yellow, <70% red)
  2. Two-column main content (grid-cols-1 lg:grid-cols-2)
     - Left column:
       - Active Production Panel
       - Inventory Alerts Section
     - Right column:
       - Recent Activity Feed
       - Quick Actions Grid
  3. Performance Charts Section (full width)
     - Three charts in row (grid-cols-1 md:grid-cols-3):
       1. Success Rate Trend (LineChart, 7 days)
       2. Material Usage (PieChart or BarChart by material type)
       3. Daily Production Volume (BarChart with stacked successful/failed)
  4. Failure Analytics Section (full width, below charts)
     - Two charts (grid-cols-1 md:grid-cols-2):
       1. Failure Breakdown by Reason (PieChart)
       2. Failure Trends (LineChart over time)
     - Include statistics: Total failures, failure rate percentage

- Each section wrapped in Card component
- Use Separator between major sections
- Implement error boundaries for each section (fallback UI)
- Loading states: Show skeleton loaders while data fetching
- Auto-refresh: Data refetches based on query refetchInterval

Update frontend/src/main.tsx routing:
- Change root authenticated route ("/") from Dashboard to DashboardHome
- Move SpoolList to /inventory/spools route (if not already)
- Ensure AppLayout wrapper is applied to DashboardHome
- Update sidebar navigation: Dashboard menu item links to "/"

Test routing:
- Verify authenticated users land on DashboardHome after login
- Verify navigation to /inventory routes works
- Verify production run links from dashboard navigate correctly
