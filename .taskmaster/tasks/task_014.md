# Task ID: 14

**Title:** Build Production Run List Page with Filters

**Status:** pending

**Dependencies:** 13 ✓

**Priority:** medium

**Description:** Create comprehensive production run list page with data table and filtering

**Details:**

Create frontend/src/pages/ProductionRunList.tsx using shadcn/ui Table component. Columns: Run #, Date, Products, Status, Variance %, Actions. Implement status badges with color coding: in_progress (blue), completed (green), failed (red), cancelled (gray). Add variance color coding: >10% over (red), <-10% under (green), within ±10% (yellow). Create filters: Status (multi-select), Date range picker, Product selector, Spool selector. Add search by run number. Implement pagination with TanStack Query. Use TanStack Table for sorting and column management. Add loading skeleton states.

**Test Strategy:**

Component tests for filtering, sorting, pagination, status badge rendering, responsive design tests

## Subtasks

### 14.1. Build basic table component with status badges

**Status:** pending
**Dependencies:** None

Create ProductionRunList.tsx with shadcn/ui Table component and implement status badge system

**Details:**

Create frontend/src/pages/ProductionRunList.tsx using shadcn/ui Table component. Set up basic table structure with columns: Run #, Date, Products, Status, Variance %, Actions. Implement status badge component with color coding: in_progress (blue), completed (green), failed (red), cancelled (gray). Use Badge component from shadcn/ui with appropriate variant styling.

### 14.2. Implement variance visualization with color coding

**Status:** pending
**Dependencies:** 14.1

Add variance percentage display with color-coded indicators based on business rules

**Details:**

Implement variance calculation and color coding logic: >10% over budget shows red, <-10% under budget shows green, within ±10% shows yellow. Create reusable VarianceCell component with appropriate styling. Include percentage display with + or - indicators. Add tooltip showing exact variance amounts.

### 14.3. Create comprehensive filter system

**Status:** pending
**Dependencies:** 14.2

Build multi-select status filter, date range picker, and product/spool selectors

**Details:**

Implement filter components: Status multi-select dropdown using shadcn/ui Select, Date range picker using shadcn/ui Calendar, Product selector dropdown with search, Spool selector dropdown with search. Create FilterBar component to house all filters. Add clear filters functionality and active filter indicators.

### 14.4. Integrate search and pagination with TanStack Query

**Status:** pending
**Dependencies:** 14.3

Add search by run number functionality and implement pagination using TanStack Query

**Details:**

Create search input for run number filtering. Integrate TanStack Query for data fetching with query parameters for filters, search, and pagination. Implement TanStack Table for sorting and column management. Add pagination controls with page size options. Include debounced search to avoid excessive API calls.

### 14.5. Implement loading states and responsive design

**Status:** pending
**Dependencies:** 14.4

Add skeleton loading states and ensure responsive table design across devices

**Details:**

Create skeleton loading components for table rows and filter components. Implement responsive table design with horizontal scrolling on mobile devices. Add empty state component when no production runs exist. Follow existing SpoolList patterns for consistency. Include loading states for filter options and search results.
