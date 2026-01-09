# Task ID: 18

**Title:** Implement Edit Production Run Form

**Status:** pending

**Dependencies:** 17

**Priority:** medium

**Description:** Create edit form for in-progress production runs only

**Details:**

Create frontend/src/components/production-runs/EditRunForm.tsx that loads existing run data and allows editing all fields except run number. Implement status-based form disabling (only allow editing for 'in_progress' status). Support adding/removing items and materials with proper validation. Use React Hook Form with Zod validation. Add unsaved changes warning. Implement optimistic updates with proper error handling and rollback. Show read-only view for completed/failed/cancelled runs with edit suggestion message.

**Test Strategy:**

Form pre-population tests, status-based validation tests, unsaved changes handling, optimistic updates

## Subtasks

### 18.1. Create EditRunForm component with pre-population and status validation

**Status:** pending
**Dependencies:** None

Create the base EditRunForm.tsx component that loads existing production run data and implements status-based form field disabling.

**Details:**

Create frontend/src/components/production-runs/EditRunForm.tsx with React Hook Form setup. Implement form pre-population from existing run data using useEffect. Add status-based validation that only allows editing when status is 'in_progress'. Disable all form fields for completed/failed/cancelled runs and show appropriate read-only message with edit suggestion.

### 18.2. Implement dynamic items and materials management

**Status:** pending
**Dependencies:** 18.1

Add functionality for dynamically adding and removing production run items and materials with proper validation.

**Details:**

Implement dynamic form array management for production_run_items and production_run_materials. Create add/remove functionality with proper React Hook Form field array methods. Add validation for required fields, positive quantities, and weight values. Ensure proper form state updates when adding/removing items.

### 18.3. Add unsaved changes warning and Zod validation

**Status:** pending
**Dependencies:** 18.2

Implement unsaved changes detection with warning dialog and comprehensive Zod validation schema.

**Details:**

Create Zod validation schema for EditRunForm with all field validations. Implement unsaved changes detection using form dirty state. Add beforeunload event listener and custom dialog for navigation warnings. Create validation error display with proper error messages. Ensure validation prevents form submission with invalid data.

### 18.4. Implement optimistic updates with error handling and rollback

**Status:** pending
**Dependencies:** 18.3

Add optimistic UI updates with proper error handling and rollback mechanisms for failed updates.

**Details:**

Implement optimistic updates using React Query mutations with onMutate, onError, and onSuccess handlers. Add loading states and error display. Create rollback mechanism that restores previous form state on API errors. Implement proper error messaging and retry functionality. Add success notifications for completed updates.
