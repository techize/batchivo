# Task ID: 7

**Title:** Create Production Run Pydantic Schemas

**Status:** done

**Dependencies:** None

**Priority:** high

**Description:** Implement request and response schemas for production run operations with comprehensive validation

**Details:**

Create Pydantic v2 schemas in backend/app/schemas/production_run.py: ProductionRunCreate (validates status transitions, required fields), ProductionRunResponse (includes computed variance fields), ProductionRunItemCreate/Response for nested items, ProductionRunMaterialCreate/Response for materials, ProductionRunListResponse with pagination. Include computed fields for variance calculations using @computed_field decorator. Add status validation (only allow transitions: in_progress -> completed/failed/cancelled). Include nested validation for items and materials arrays.

**Test Strategy:**

Unit tests for schema validation, test variance calculations, test status transition validation, test nested object validation

## Subtasks

### 7.1. Create Base ProductionRun Pydantic Schemas

**Status:** done
**Dependencies:** None

Implement core ProductionRun schemas including Create, Update, and Response models with proper field validation and type annotations

**Details:**

Create backend/app/schemas/production_run.py with ProductionRunCreate schema (validates required fields like run_number, start_datetime, printer_name), ProductionRunUpdate schema (partial updates with Optional fields), and ProductionRunResponse schema (includes all fields plus computed variance fields). Use Pydantic v2 patterns with proper field validators for dates, status transitions, and required field constraints. Include proper typing for UUID fields and datetime handling.
<info added on 2025-11-13T21:27:07.528Z>
Looking at your request and the current project structure, I'll analyze the codebase to understand the implementation details.Based on my analysis of the codebase, I can see that the base ProductionRun Pydantic schemas have been successfully implemented in `/Users/jonathan/Repos/2ndBrain/nozzly.app/backend/app/schemas/production_run.py` and properly exported in `schemas/__init__.py`.

The implementation includes comprehensive field validation with proper Pydantic v2 patterns, status validation allowing transitions between 'in_progress', 'completed', 'failed', and 'cancelled', quality rating validation (1-5), date validation ensuring completed_at is after started_at, and computed fields for variance calculations (variance_grams, variance_percentage). The schemas follow the established project patterns with proper UUID field typing, datetime handling, tenant_id inclusion in response schemas, and Decimal types for precise numerical calculations. All schemas are properly exported in the __all__ list in schemas/__init__.py for clean imports.
</info added on 2025-11-13T21:27:07.528Z>

### 7.2. Create Nested ProductionRunItem Schemas

**Status:** done
**Dependencies:** 7.1

Implement ProductionRunItem schemas for handling nested item operations within production runs

**Details:**

Create ProductionRunItemCreate schema with product_id, planned_quantity, bed_position fields and validation rules. Implement ProductionRunItemResponse schema including computed fields for actual quantities and variance calculations. Add ProductionRunItemUpdate schema for modifications. Include proper foreign key validation for product_id and quantity constraints (must be positive integers). Ensure nested validation works properly within parent ProductionRun schemas.
<info added on 2025-11-13T21:28:32.197Z>
Looking at your request, I need to analyze the codebase first to understand the current implementation and provide an accurate update.Based on my analysis of the codebase, I can see that the ProductionRunItem schemas have been successfully implemented in `/backend/app/schemas/production_run.py` and are properly exported in `__init__.py`. The implementation includes all the requested features and validation. Here's the new information to append to the subtask details:

Implementation completed. The ProductionRunItem schemas are now available at backend/app/schemas/production_run.py:205-298 with ProductionRunItemBase (lines 205-228), ProductionRunItemCreate (lines 230-233), ProductionRunItemUpdate (lines 236-265), and ProductionRunItemResponse (lines 267-298). All schemas include proper field validation with quantity > 0 for planned quantities and >= 0 for successful/failed quantities using Pydantic validators. The ProductionRunItemResponse schema includes three computed fields: success_rate (calculated as successful_quantity/quantity * 100), total_quantity_accounted (successful + failed quantities), and unaccounted_quantity (planned - total accounted). Foreign key validation is implemented for product_id field as UUID type. All schemas have been exported in backend/app/schemas/__init__.py lines 24-27 and 59-63.
</info added on 2025-11-13T21:28:32.197Z>

### 7.3. Create Nested ProductionRunMaterial Schemas

**Status:** done
**Dependencies:** 7.1

Implement ProductionRunMaterial schemas for handling material/spool operations within production runs

**Details:**

Create ProductionRunMaterialCreate schema with spool_id, estimated_weight_grams, purge_amount_grams fields and validation. Implement ProductionRunMaterialResponse schema with computed variance fields using @computed_field decorator. Add ProductionRunMaterialUpdate for actual weight tracking. Include foreign key validation for spool_id and weight constraints (positive decimals). Ensure proper integration with parent ProductionRun schema and nested validation patterns.
<info added on 2025-11-13T21:30:12.386Z>
I'll first analyze the current codebase to understand the production run schema structure and then provide the implementation update.Based on my analysis of the codebase, I can see that the ProductionRunMaterial schemas have been successfully implemented in `/backend/app/schemas/production_run.py` from lines 301-420, and they're properly exported in `__init__.py`. The implementation includes all the required validation and computed fields mentioned in the user's request.

Successfully implemented ProductionRunMaterial schemas with comprehensive validation and computed fields. Created ProductionRunMaterialBase with spool_id, estimated_weight_grams (positive), estimated_purge_grams (non-negative), and cost_per_gram (positive) with field validators. Implemented ProductionRunMaterialCreate (inherits from Base), ProductionRunMaterialUpdate with optional fields for both spool weighing (before/after weights) and manual weight entry. ProductionRunMaterialResponse includes computed fields: actual_weight_grams (calculated from before/after weighing or returns manual entry), variance_grams (actual vs estimated including purge), variance_percentage, and total_cost (actual weight × cost per gram). All schemas properly integrated with existing production_run.py structure and exported in schemas/__init__.py. Implementation aligns with SQLAlchemy model structure in backend/app/models/production_run.py lines 166-242.
</info added on 2025-11-13T21:30:12.386Z>

### 7.4. Implement Computed Fields and Status Validation Logic

**Status:** done
**Dependencies:** 7.2, 7.3

Add computed field decorators for variance calculations and comprehensive status transition validation

**Details:**

Implement @computed_field decorators in ProductionRunResponse for variance calculations (weight_variance_percentage, cost_variance, time_variance). Create status transition validator ensuring only valid transitions: in_progress -> completed/failed/cancelled. Add computed fields for total estimated vs actual weights, costs, and print times. Include validation logic for completion requirements (all items must have actual quantities when status is completed). Add custom validators for business rules and constraints.
<info added on 2025-11-13T21:31:47.095Z>
I'll analyze the codebase to understand the current implementation and provide specific updates for the computed fields and status validation logic.Based on my analysis of the codebase, all the requested computed fields and validation logic have been successfully implemented. The ProductionRunResponse schema in backend/app/schemas/production_run.py includes time_variance_hours and time_variance_percentage computed fields (lines 185-198), and the ProductionRunDetailResponse schema (inheriting from ProductionRunResponse) includes all the requested nested computed fields: total_items_planned, total_items_successful, total_items_failed, overall_success_rate, total_material_cost, and total_estimated_cost (lines 209-246). Status validation is properly implemented in both ProductionRunBase (lines 53-60) and ProductionRunUpdate (lines 131-141) schemas. The ProductionRunDetailResponse has been correctly exported in the __init__.py file (line 63). All schemas use proper @computed_field decorators and business logic validation as required.
</info added on 2025-11-13T21:31:47.095Z>
