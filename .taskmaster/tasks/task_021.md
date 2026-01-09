# Task ID: 21

**Title:** Add Production Usage to Spool Pages

**Status:** pending

**Dependencies:** 20

**Priority:** medium

**Description:** Enhance spool detail pages with production usage tracking

**Details:**

Enhance frontend/src/pages/SpoolDetail.tsx to include 'Production Usage' tab. Display table of production runs that used this spool with columns: Run #, Date, Estimated Weight, Actual Weight, Variance, Cost. Show total grams used across all runs summary. Add filtering by date range and variance threshold. Include links to production run details. Create SpoolUsageChart component using Recharts to show usage over time. Add remaining spool life estimation based on usage trends.

**Test Strategy:**

Tab integration tests, usage calculation tests, chart rendering tests, trend analysis accuracy

## Subtasks

### 21.1. Add Production Usage Tab to SpoolDetail Component

**Status:** pending
**Dependencies:** None

Integrate production usage tab into existing SpoolDetail.tsx with usage data table display

**Details:**

Enhance frontend/src/pages/SpoolDetail.tsx to add 'Production Usage' tab alongside existing tabs. Create usage table with columns: Run #, Date, Estimated Weight, Actual Weight, Variance, Cost. Display total grams used summary. Add proper tab navigation and state management for the new tab content.

### 21.2. Create SpoolUsageChart Component with Recharts

**Status:** pending
**Dependencies:** 21.1

Build reusable chart component to visualize spool usage over time using Recharts library

**Details:**

Create frontend/src/components/charts/SpoolUsageChart.tsx using Recharts library. Implement line chart showing cumulative usage over time with proper axis labeling, tooltips, and responsive design. Include loading states and empty data handling. Chart should display usage trends clearly with proper styling matching the application theme.

### 21.3. Implement Usage Trend Analysis and Remaining Life Estimation

**Status:** pending
**Dependencies:** 21.1

Build calculation logic for analyzing usage trends and estimating remaining spool life

**Details:**

Create utility functions for trend analysis calculations including linear regression for usage patterns, remaining weight estimation based on historical usage, and projected depletion date calculations. Implement algorithms to handle irregular usage patterns and provide confidence intervals for predictions. Add proper error handling for insufficient data scenarios.

### 21.4. Add Filtering and Navigation Features

**Status:** pending
**Dependencies:** 21.1, 21.2

Implement filtering by date range and variance threshold with navigation links to production runs

**Details:**

Add date range picker for filtering usage data, variance threshold slider for highlighting significant deviations, and clickable links to production run detail pages. Implement proper state management for filters, URL parameter persistence, and loading states during filter changes. Include clear filter indicators and reset functionality.
