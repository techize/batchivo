# Task ID: 19

**Title:** Add Recharts for Variance Visualization

**Status:** pending

**Dependencies:** 18

**Priority:** medium

**Description:** Install Recharts and create variance analysis charts and dashboard

**Details:**

Add 'recharts: ^2.8.0' to frontend package.json. Create frontend/src/components/production-runs/VarianceDashboard.tsx with charts: Line chart (Estimated vs Actual over time by run date), Bar chart (Variance by product showing which products are consistently off), Table of products with highest variance (candidates for BOM updates). Create reusable chart components in frontend/src/components/charts/. Add chart tooltips, legends, and responsive design. Include data transformation utilities for chart data preparation. Add export to CSV functionality for reports.

**Test Strategy:**

Chart rendering tests, data transformation tests, responsive design tests, CSV export functionality

## Subtasks

### 19.1. Install Recharts and Create Base Chart Components

**Status:** pending
**Dependencies:** None

Install Recharts package and create reusable chart component library with proper TypeScript types and shared styling

**Details:**

Add 'recharts: ^2.8.0' to frontend/package.json and run npm install. Create frontend/src/components/charts/ directory with base components: BaseLineChart.tsx, BaseBarChart.tsx, ChartContainer.tsx, and ChartTooltip.tsx. Implement proper TypeScript interfaces for chart data and props. Add consistent styling using shadcn/ui design tokens and ensure responsive design with proper breakpoints. Create chart theme configuration for consistent colors and typography.

### 19.2. Implement Line Chart for Estimated vs Actual Trends

**Status:** pending
**Dependencies:** 19.1

Create line chart component showing estimated vs actual values over time by run date with interactive tooltips

**Details:**

Create frontend/src/components/production-runs/EstimatedActualLineChart.tsx using BaseLineChart component. Implement data transformation to prepare production run data for line chart format with separate series for estimated and actual values. Add interactive tooltips showing exact values, variance percentage, and run details. Include legend and axis labels. Add date formatting for x-axis and proper scaling for y-axis values. Ensure chart updates when production run data changes.

### 19.3. Create Variance by Product Bar Chart Analysis

**Status:** pending
**Dependencies:** 19.1

Build bar chart showing variance analysis by product to identify products consistently off from estimates

**Details:**

Create frontend/src/components/production-runs/VarianceByProductChart.tsx using BaseBarChart component. Implement aggregation logic to calculate average variance per product across all production runs. Add color coding for bars based on variance threshold (green for low, yellow for medium, red for high variance). Include interactive tooltips showing product name, average variance, number of runs, and variance trend. Add sorting options for variance amount and product name.

### 19.4. Build Variance Dashboard with Data Utils and CSV Export

**Status:** pending
**Dependencies:** 19.2, 19.3

Create complete variance dashboard component with data transformation utilities and CSV export functionality

**Details:**

Create frontend/src/components/production-runs/VarianceDashboard.tsx that combines both chart components with a table of products with highest variance. Implement frontend/src/utils/chartDataUtils.ts for data transformation functions. Create CSV export functionality using a library like react-csv or custom implementation. Add dashboard layout with responsive grid using shadcn/ui components. Include filters for date range, product category, and variance threshold. Add loading states and error handling for data fetching.
