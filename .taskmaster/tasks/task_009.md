# Task ID: 9

**Title:** Create Production Run API Endpoints

**Status:** done

**Dependencies:** 8 ✓

**Priority:** high

**Description:** Implement FastAPI REST endpoints for production run CRUD operations

**Details:**

Create backend/app/api/v1/production_runs.py with endpoints: POST / (create run), GET / (list with filters for status, date range, product, spool), GET /{id} (detail with eager loading of items and materials), PUT /{id} (update), DELETE /{id} (soft delete), POST /{id}/complete (complete and create inventory transactions). Include nested endpoints for items and materials: POST /{id}/items, PUT /{id}/items/{item_id}, DELETE /{id}/items/{item_id}. Add query parameters for filtering and pagination. Use CurrentTenant and CurrentUser dependencies. Include proper error handling and HTTP status codes.

**Test Strategy:**

Integration tests for all endpoints, test tenant isolation, test pagination and filtering, test error scenarios

## Subtasks

### 9.1. Implement Main CRUD Endpoints

**Status:** done
**Dependencies:** None

Create the core REST API endpoints for production run management including create, read, update, and delete operations with proper validation and error handling.

**Details:**

Create backend/app/api/v1/production_runs.py with main endpoints: POST / (create production run with validation), GET / (list production runs with filtering by status, date range, product, spool), GET /{id} (get single production run with eager loading of items and materials), PUT /{id} (update production run with status transition validation), DELETE /{id} (soft delete production run). Use CurrentTenant and CurrentUser dependencies for security. Include proper HTTP status codes and error responses.

### 9.2. Implement Production Run Completion Endpoint

**Status:** done
**Dependencies:** 9.1

Create the completion endpoint that handles finalizing production runs and creating inventory transactions for material usage.

**Details:**

Implement POST /{id}/complete endpoint that transitions production run to completed status, validates actual vs estimated quantities, creates inventory transactions for material usage deduction, calculates variance metrics, and updates spool weights. Include business logic validation to prevent double completion and ensure proper inventory tracking. Handle rollback scenarios for failed transactions.

### 9.3. Implement Production Run Items Nested Endpoints

**Status:** done
**Dependencies:** 9.1

Create nested API endpoints for managing items within production runs including add, update, and remove operations.

**Details:**

Implement nested endpoints under /{id}/items: POST /{id}/items (add new item to production run), PUT /{id}/items/{item_id} (update item quantity or bed position), DELETE /{id}/items/{item_id} (remove item from production run). Include validation to ensure items belong to the correct production run and tenant. Validate that total quantities don't exceed physical constraints.

### 9.4. Implement Production Run Materials Nested Endpoints

**Status:** done
**Dependencies:** 9.1

Create nested API endpoints for managing materials and spool assignments within production runs.

**Details:**

Implement nested endpoints under /{id}/materials: POST /{id}/materials (assign spool to production run), PUT /{id}/materials/{material_id} (update estimated weight or actual usage), DELETE /{id}/materials/{material_id} (remove material assignment). Include validation to ensure spool availability and sufficient material quantity. Validate material compatibility with products being printed.

### 9.5. Implement Query Parameters and Pagination

**Status:** done
**Dependencies:** 9.1

Add comprehensive query parameter support for filtering, sorting, and pagination across all production run endpoints.

**Details:**

Implement query parameters for GET / endpoint: filtering by status, date range (start_date, end_date), product_id, spool_id, printer; sorting by created_at, start_date, completion_date; pagination with page, page_size, total_count. Use SQLAlchemy query building with proper indexing. Include response metadata with pagination info and total counts. Follow existing API patterns for consistency.
