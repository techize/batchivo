# Task ID: 20

**Title:** Integrate Production History in Product Pages

**Status:** pending

**Dependencies:** 19

**Priority:** medium

**Description:** Add production history tabs to existing product detail pages

**Details:**

Enhance frontend/src/pages/ProductDetail.tsx to include 'Production History' tab using shadcn/ui Tabs component. Display table of production runs that used this product with columns: Run #, Date, Quantity, Success Rate, Actual vs Estimated Cost. Add average actual cost vs estimated cost summary. Create reusable ProductionHistoryTable component. Implement data fetching using TanStack Query with product ID parameter. Add filtering by date range and run status. Include links to individual production run details.

**Test Strategy:**

Tab integration tests, data fetching tests, table functionality tests, linking to production run details

## Subtasks

### 20.1. Integrate Production History Tab in ProductDetail.tsx

**Status:** pending
**Dependencies:** None

Add 'Production History' tab to existing product detail page using shadcn/ui Tabs component

**Details:**

Enhance frontend/src/pages/ProductDetail.tsx to include new 'Production History' tab alongside existing tabs. Use shadcn/ui Tabs component following established patterns. Import and integrate ProductionHistoryTable component. Update tab navigation and content area to accommodate production history display. Ensure consistent styling and layout with existing product page structure.

### 20.2. Create ProductionHistoryTable Component with Data Fetching

**Status:** pending
**Dependencies:** 20.1

Build reusable table component to display production runs with filtering and data fetching capabilities

**Details:**

Create frontend/src/components/production/ProductionHistoryTable.tsx with columns: Run #, Date, Quantity, Success Rate, Actual vs Estimated Cost. Implement TanStack Query for data fetching with product ID parameter. Add filtering by date range and run status using shadcn/ui components. Include pagination for large datasets. Make component reusable for use in other product-related contexts.

### 20.3. Add Cost Variance Summary and Navigation Links

**Status:** pending
**Dependencies:** 20.2

Implement cost variance calculations and links to individual production run details

**Details:**

Add summary section showing average actual cost vs estimated cost variance with percentage difference and trend indicators. Implement navigation links from table rows to individual production run detail pages. Calculate and display cost variance statistics including min, max, and average differences. Include visual indicators for cost overruns vs savings using appropriate colors and icons.
