# Task ID: 15

**Title:** Create Multi-Step Production Run Form

**Status:** pending

**Dependencies:** 14

**Priority:** high

**Description:** Implement 4-step wizard for creating production runs

**Details:**

Create frontend/src/components/production-runs/CreateRunWizard.tsx using React Hook Form v7.66+ and Zod v4.1+ validation. Step 1: Basic Info (auto-generated run number preview, start date/time, printer name, slicer software, estimated print time, temperatures). Step 2: Items to Print (product multi-select, quantity inputs, bed position, display estimated costs from BOM). Step 3: Materials (spool selectors filtered by material/color, estimated weights from BOM, purge amounts). Step 4: Review & Submit with validation summary. Use shadcn/ui Form components, implement step validation, save draft state to localStorage, show progress indicator.

**Test Strategy:**

Form validation tests, step navigation tests, draft saving functionality, integration with API

## Subtasks

### 15.1. Create wizard infrastructure with step navigation and validation

**Status:** pending
**Dependencies:** None

Build the core multi-step form wizard framework with step navigation, progress indicator, and validation orchestration

**Details:**

Create CreateRunWizard.tsx component with React Hook Form and Zod validation. Implement step navigation (Next/Previous buttons), progress indicator showing current step (1 of 4), step validation before navigation, and form context provider for sharing state between steps. Include TypeScript interfaces for wizard state management.

### 15.2. Implement Step 1 - Basic info form with auto-generated previews

**Status:** pending
**Dependencies:** 15.1

Create the first step of the wizard for basic production run information with auto-generated run number and validation

**Details:**

Build Step1BasicInfo component with fields: auto-generated run number preview (format: RUN-YYYYMMDD-###), start date/time picker, printer name dropdown, slicer software select, estimated print time input, temperature fields (nozzle/bed). Use shadcn/ui Form components with Zod validation. Implement real-time preview updates for run number generation.

### 15.3. Implement Step 2 - Items selection with product multi-select and cost estimation

**Status:** pending
**Dependencies:** 15.1

Create the items selection step with product multi-select, quantity inputs, and real-time cost estimation from BOM

**Details:**

Build Step2ItemSelection component with product multi-select dropdown, quantity inputs for each selected product, bed position assignments, and estimated cost display calculated from BOM. Include add/remove item functionality, validation for minimum 1 item, and real-time cost calculation updates. Use React Hook Form's useFieldArray for dynamic item management.

### 15.4. Implement Step 3 - Materials selection with spool filtering and weight estimation

**Status:** pending
**Dependencies:** 15.1

Create materials selection step with filtered spool selectors and estimated weight calculations from BOM

**Details:**

Build Step3MaterialSelection component with spool selectors filtered by material type and color based on selected products. Calculate estimated weights from BOM, include purge amount inputs, show available spool weights with low stock warnings. Implement material requirements validation ensuring all product materials are covered.

### 15.5. Implement Step 4 - Review and validation summary

**Status:** pending
**Dependencies:** 15.1, 15.2, 15.3, 15.4

Create the final review step with comprehensive validation summary and submission preparation

**Details:**

Build Step4ReviewSubmit component displaying summary of all entered data: basic info, selected items with costs, material allocations with weights. Include validation summary showing any warnings or errors, estimated total cost breakdown, and final submission button. Add edit shortcuts to return to previous steps for corrections.

### 15.6. Implement form state management with localStorage draft saving and submission

**Status:** pending
**Dependencies:** 15.1, 15.2, 15.3, 15.4, 15.5

Add comprehensive form state management including draft saving to localStorage and API submission logic

**Details:**

Implement draft saving functionality using localStorage to persist form state between sessions, auto-save on step navigation, draft restoration on component mount. Create submission logic with optimistic updates, error handling, and success/failure feedback. Include form reset functionality and draft cleanup after successful submission.
