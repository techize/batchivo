# Task ID: 17

**Title:** Create Production Run Completion Form

**Status:** pending

**Dependencies:** 16

**Priority:** high

**Description:** Build form to finalize production runs with weight tracking and variance preview

**Details:**

Create frontend/src/components/production-runs/CompleteRunForm.tsx. For each material: 3 input options (Use Estimate button, Before/After weight inputs with auto-calculation, Manual actual weight). For each item: successful/failed quantity inputs with validation (sum ≤ planned). Add overall quality rating (1-5 stars using Radix UI), quality notes textarea, completion notes. Show variance preview before submit with color-coded warnings for >10% variance. Include 'Use All Estimates' shortcut button. Implement optimistic updates with TanStack Query. Add confirmation dialog for significant variances.

**Test Strategy:**

Form validation tests, variance calculation tests, optimistic update tests, confirmation dialog tests

## Subtasks

### 17.1. Implement Weight Input Options Component

**Status:** pending
**Dependencies:** None

Create the three weight input methods: Use Estimate button, Before/After weight inputs with auto-calculation, and Manual actual weight input for each material in the production run.

**Details:**

Build weight input component with three distinct input modes. Use Estimate button applies the estimated weight from the production run plan. Before/After weight inputs allow users to enter starting and ending spool weights with automatic calculation of consumed weight. Manual input allows direct entry of actual weight used. Include proper TypeScript types and validation for each input method. Use controlled components with React Hook Form for form state management.

### 17.2. Build Item Quantity Tracking with Validation

**Status:** pending
**Dependencies:** 17.1

Implement successful/failed quantity inputs for each production item with validation ensuring the sum doesn't exceed planned quantities.

**Details:**

Create quantity tracking inputs for each item in the production run. Add separate fields for successful and failed quantities. Implement real-time validation to ensure successful + failed quantities do not exceed the planned quantity for each item. Display validation errors inline with clear messaging. Include visual indicators for valid/invalid states and running totals. Use Radix UI form components for consistent styling.

### 17.3. Create Quality Rating and Notes Interface

**Status:** pending
**Dependencies:** None

Build quality rating component with 1-5 star rating using Radix UI and textarea fields for quality notes and completion notes.

**Details:**

Implement star rating component using Radix UI's primitive components. Create interactive 1-5 star rating with hover states and clear visual feedback. Add quality notes textarea with character limits and validation. Include completion notes textarea for general run completion remarks. Style components consistently with the rest of the application using Tailwind CSS and shadcn/ui patterns.

### 17.4. Implement Variance Preview with Color-coded Warnings

**Status:** pending
**Dependencies:** 17.1, 17.2

Build variance calculation system that shows real-time preview of material usage and quantity variances with color-coded warnings for >10% variance.

**Details:**

Create variance preview component that calculates differences between planned and actual values for both materials and quantities. Display percentage variance with color coding: green for <5% variance, yellow for 5-10% variance, red for >10% variance. Show both absolute and percentage differences. Include summary cards showing total variance impact. Calculate variance in real-time as user inputs change. Add 'Use All Estimates' shortcut button to quickly apply estimated values.

### 17.5. Integrate TanStack Query with Confirmation Dialogs

**Status:** pending
**Dependencies:** 17.4

Implement optimistic updates using TanStack Query and add confirmation dialogs for submissions with significant variances (>10%).

**Details:**

Set up TanStack Query mutation for production run completion with optimistic updates. Implement confirmation dialog that triggers for high variance scenarios (>10% material or quantity variance). Dialog should display variance details and require explicit confirmation. Handle mutation success/error states with proper loading indicators and error messages. Include retry logic for failed submissions. Update cache optimistically and rollback on errors.
