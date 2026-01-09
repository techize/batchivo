# Task ID: 16

**Title:** Build Production Run Detail Page

**Status:** pending

**Dependencies:** 15

**Priority:** high

**Description:** Create comprehensive production run detail page with all data sections

**Details:**

Create frontend/src/pages/ProductionRunDetail.tsx with sections: Header (run number, status badge, dates, duration), Run Overview Card (printer, slicer, timestamps, quality rating with star display, notes), Items Printed Table (product links, planned/successful/failed quantities, success rates, costs), Material Usage Table (spool links with color swatches, estimated/actual weights, variance with color coding), Variance Summary with Recharts bar chart or gauge. Add quick actions: Complete Run, Edit, Delete. Use shadcn/ui Card, Table, and Badge components. Implement data fetching with TanStack Query.

**Test Strategy:**

Component rendering tests, data loading tests, chart rendering tests, action button functionality

## Subtasks

### 16.1. Create ProductionRunDetail page structure and routing

**Status:** pending
**Dependencies:** None

Create the main ProductionRunDetail.tsx component with basic page structure, routing, and data fetching setup using TanStack Query.

**Details:**

Create frontend/src/pages/ProductionRunDetail.tsx with useParams for run ID, implement TanStack Query for data fetching, set up basic page layout with loading states and error handling. Add route configuration in router setup.

### 16.2. Implement Header and Run Overview sections

**Status:** pending
**Dependencies:** 16.1

Build the header section with run metadata and the run overview card with printer information and quality rating display.

**Details:**

Create header section with run number, status badge using shadcn/ui Badge component, dates, and duration calculation. Build Run Overview Card with printer/slicer info, timestamps, quality rating with star display using Radix UI Rating component, and notes field.

### 16.3. Create Items Printed Table component

**Status:** pending
**Dependencies:** 16.1

Build the items printed table showing product links, quantities, success rates, and cost calculations with proper formatting.

**Details:**

Implement Items Printed Table using shadcn/ui Table component. Display product names with links, planned/successful/failed quantities, calculated success rates with percentage formatting, and cost calculations. Add proper column sorting and responsive design.

### 16.4. Build Material Usage Table with variance visualization

**Status:** pending
**Dependencies:** 16.1

Create material usage table with spool information, weight tracking, and color-coded variance display.

**Details:**

Implement Material Usage Table with spool links, color swatches, estimated vs actual weights, and variance calculations. Add color coding for variance: red for >10% over, green for <-10% under, yellow for within ±10%. Include spool color swatches and proper weight formatting.

### 16.5. Add Recharts variance summary and quick actions

**Status:** pending
**Dependencies:** 16.2, 16.3, 16.4

Implement variance summary visualization using Recharts and add quick action buttons for run management.

**Details:**

Create Variance Summary section with Recharts bar chart or gauge showing material variance overview. Implement quick action buttons: Complete Run, Edit, and Delete with proper confirmation dialogs. Follow existing ProductDetail page patterns for layout and styling.
