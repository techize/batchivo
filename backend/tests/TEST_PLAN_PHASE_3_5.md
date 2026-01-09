# Test Plan: Phase 3.5 - Backend Test Coverage Improvements

**Date**: 2025-12-15
**Target**: Achieve 95%+ coverage on Production Run Service and API
**Current Status**: Service 68%, API 81%

---

## Coverage Gaps Analysis

### Production Run Service (`app/services/production_run.py`) - 68% Coverage

**Uncovered Lines**: 94-98, 187, 190, 193-198, 240, 267, 291, 319-337, 356, 360-364, 392-410, 473, 589, 592, 690, 802, 833-835, 906-986, 1016-1097

**Critical Uncovered Areas**:
1. **Material Cost Calculations** (Lines 94-98)
   - Fetching cost_per_gram from spool when material cost is zero
   - Fallback to zero if spool has no cost

2. **Status Transitions** (Lines 319-337, 392-410)
   - Transition validation logic
   - Status change authorization
   - Invalid transition error handling

3. **Variance Calculations** (Lines 906-986)
   - Time variance calculations
   - Material weight variance calculations
   - Aggregate variance across materials
   - Edge cases: null values, zero denominators

4. **Complex Filtering** (Lines 1016-1097)
   - Multi-criteria filtering
   - Date range queries
   - Status-based filtering
   - Sorting logic

5. **Bulk Operations** (Lines 473, 589, 592, 690, 802)
   - Batch updates
   - Cascading operations
   - Transaction rollback scenarios

---

## Production Run Service - Test Implementation Plan

### Priority 1: Material Cost Calculations (5 tests)

**File**: `tests/unit/test_production_run_service.py`

1. **test_create_run_with_zero_cost_material**
   - Given: Material with cost_per_gram = 0
   - When: Creating production run
   - Then: Should fetch cost from spool

2. **test_create_run_with_missing_spool_cost**
   - Given: Material with cost = 0, Spool also has no cost
   - When: Creating production run
   - Then: Should default to 0, not error

3. **test_create_run_with_provided_material_cost**
   - Given: Material with explicit cost_per_gram > 0
   - When: Creating production run
   - Then: Should use provided cost, not fetch from spool

4. **test_update_run_recalculates_material_costs**
   - Given: Existing run with materials
   - When: Updating material weights
   - Then: Should recalculate total costs

5. **test_material_cost_with_multiple_spools**
   - Given: Multiple materials from different spools
   - When: Creating run
   - Then: Should fetch correct cost for each spool

### Priority 2: Variance Calculations (8 tests)

**File**: `tests/unit/test_production_run_service.py` (extend existing `TestVarianceCalculations`)

6. **test_variance_with_null_estimated_time**
   - Given: Run with actual_time but no estimated_time
   - When: Calculating variance
   - Then: Should return None or handle gracefully

7. **test_variance_with_zero_estimated_time**
   - Given: Run with actual_time, estimated_time = 0
   - When: Calculating variance
   - Then: Should avoid division by zero

8. **test_variance_with_null_actual_time**
   - Given: Run with estimated_time but no actual_time
   - When: Calculating variance
   - Then: Should return None

9. **test_material_variance_with_null_values**
   - Given: Materials with missing actual weights
   - When: Calculating material variance
   - Then: Should handle nulls correctly

10. **test_material_variance_with_zero_estimated_weight**
    - Given: Material with actual weight, estimated = 0
    - When: Calculating variance
    - Then: Should avoid division by zero

11. **test_aggregate_variance_mixed_materials**
    - Given: Multiple materials, some with variance, some null
    - When: Calculating aggregate variance
    - Then: Should calculate average correctly

12. **test_variance_calculation_precision**
    - Given: High-precision decimal values
    - When: Calculating variance
    - Then: Should maintain decimal precision

13. **test_variance_with_negative_actual_values**
    - Given: Invalid negative actual values
    - When: Calculating variance
    - Then: Should validate or handle appropriately

### Priority 3: Status Transitions (10 tests)

**File**: `tests/unit/test_production_run_service.py`

14. **test_transition_pending_to_in_progress**
    - Given: Run in 'pending' status
    - When: Transitioning to 'in_progress'
    - Then: Should succeed

15. **test_transition_in_progress_to_completed**
    - Given: Run in 'in_progress' status
    - When: Transitioning to 'completed'
    - Then: Should succeed and set completed_at

16. **test_transition_in_progress_to_failed**
    - Given: Run in 'in_progress' status
    - When: Transitioning to 'failed'
    - Then: Should succeed

17. **test_invalid_transition_completed_to_pending**
    - Given: Run in 'completed' status
    - When: Attempting transition to 'pending'
    - Then: Should raise validation error

18. **test_invalid_transition_failed_to_in_progress**
    - Given: Run in 'failed' status
    - When: Attempting transition to 'in_progress'
    - Then: Should raise validation error

19. **test_transition_requires_authorization**
    - Given: User without proper permissions
    - When: Attempting status transition
    - Then: Should raise authorization error

20. **test_transition_updates_timestamp**
    - Given: Any valid transition
    - When: Transitioning
    - Then: Should update updated_at timestamp

21. **test_transition_to_cancelled_from_pending**
    - Given: Run in 'pending' status
    - When: Transitioning to 'cancelled'
    - Then: Should succeed

22. **test_transition_to_cancelled_from_in_progress**
    - Given: Run in 'in_progress' status
    - When: Transitioning to 'cancelled'
    - Then: Should succeed

23. **test_transition_preserves_immutable_fields**
    - Given: Completed run
    - When: Attempting any update
    - Then: Should prevent modification of core fields

### Priority 4: Complex Filtering & Queries (7 tests)

**File**: `tests/unit/test_production_run_service.py`

24. **test_filter_by_status_list**
    - Given: Multiple runs with different statuses
    - When: Filtering by status list ['pending', 'in_progress']
    - Then: Should return only matching runs

25. **test_filter_by_date_range**
    - Given: Runs with various created_at dates
    - When: Filtering by date range
    - Then: Should return runs within range

26. **test_filter_by_model_id**
    - Given: Runs with different models
    - When: Filtering by specific model_id
    - Then: Should return runs containing that model

27. **test_complex_multi_filter**
    - Given: Many runs
    - When: Filtering by status + date range + model
    - Then: Should apply all filters correctly

28. **test_sorting_by_created_at_desc**
    - Given: Runs created at different times
    - When: Sorting by created_at DESC
    - Then: Should return newest first

29. **test_sorting_by_status**
    - Given: Runs with mixed statuses
    - When: Sorting by status
    - Then: Should order correctly

30. **test_pagination_with_filters**
    - Given: Many runs matching filter
    - When: Applying pagination (skip/limit)
    - Then: Should return correct page

### Priority 5: Bulk Operations & Edge Cases (5 tests)

**File**: `tests/unit/test_production_run_service.py`

31. **test_batch_update_status**
    - Given: Multiple run IDs
    - When: Batch updating status
    - Then: Should update all or rollback on error

32. **test_cascade_delete_with_materials**
    - Given: Run with materials
    - When: Deleting run
    - Then: Should cascade delete materials

33. **test_create_run_with_duplicate_model**
    - Given: Items list with same model_id twice
    - When: Creating run
    - Then: Should handle or prevent duplicates

34. **test_update_run_concurrent_modification**
    - Given: Run being updated by two requests
    - When: Concurrent updates
    - Then: Should handle with optimistic locking

35. **test_create_run_with_invalid_spool_id**
    - Given: Material with non-existent spool_id
    - When: Creating run
    - Then: Should raise validation error

---

## Production Runs API (`app/api/v1/production_runs.py`) - 81% Coverage

**Uncovered Lines**: 72, 103-122, 127-158, 208, 211, 239, 325, 401, 452, 532, 598, 642, 658, 733, 799, 853, 931, 973-999, 1034-1059

**Critical Uncovered Areas**:
1. **Query Parameter Validation** (Lines 103-122, 127-158)
   - Filter parameter parsing
   - Invalid parameter handling
   - Type coercion errors

2. **Error Response Formatting** (Lines 208, 211, 239, etc.)
   - 404 not found scenarios
   - 400 validation errors
   - 500 internal errors

3. **Pagination Edge Cases** (Lines 325, 401, 452)
   - Invalid skip/limit values
   - Empty result sets
   - Large offset handling

4. **Status-Specific Endpoints** (Lines 973-999, 1034-1059)
   - Status transition endpoints
   - Bulk status updates
   - Authorization checks

---

## Production Runs API - Test Implementation Plan

### Priority 1: Query Parameter Validation (5 tests)

**File**: `tests/integration/test_production_runs_api.py`

36. **test_list_with_invalid_status_filter**
    - Given: Invalid status value in query param
    - When: GET /production-runs?status=invalid
    - Then: Should return 400 with error message

37. **test_list_with_date_filter**
    - Given: Valid date range filters
    - When: GET /production-runs?start_date=2024-01-01&end_date=2024-12-31
    - Then: Should return filtered results

38. **test_list_with_invalid_date_format**
    - Given: Invalid date format in filter
    - When: GET /production-runs?start_date=invalid
    - Then: Should return 400 with error message

39. **test_list_with_model_filter**
    - Given: Valid model_id filter
    - When: GET /production-runs?model_id=model-123
    - Then: Should return runs containing that model

40. **test_list_with_multiple_filters**
    - Given: Multiple query parameters
    - When: GET /production-runs?status=in_progress&model_id=model-123
    - Then: Should apply all filters

### Priority 2: Pagination Edge Cases (5 tests)

**File**: `tests/integration/test_production_runs_api.py`

41. **test_pagination_with_invalid_skip**
    - Given: Negative skip value
    - When: GET /production-runs?skip=-1
    - Then: Should return 400 or default to 0

42. **test_pagination_with_invalid_limit**
    - Given: Limit exceeding maximum
    - When: GET /production-runs?limit=10000
    - Then: Should cap at max limit

43. **test_pagination_empty_results**
    - Given: Skip beyond total results
    - When: GET /production-runs?skip=1000
    - Then: Should return empty array with correct total

44. **test_pagination_with_sorting**
    - Given: Pagination + sort parameters
    - When: GET /production-runs?skip=10&limit=10&sort=created_at
    - Then: Should return correctly sorted page

45. **test_pagination_defaults**
    - Given: No pagination parameters
    - When: GET /production-runs
    - Then: Should use default skip=0, limit=50

### Priority 3: Error Response Handling (5 tests)

**File**: `tests/integration/test_production_runs_api.py`

46. **test_get_nonexistent_run_404**
    - Given: Non-existent run ID
    - When: GET /production-runs/999999
    - Then: Should return 404 with message

47. **test_update_nonexistent_run_404**
    - Given: Non-existent run ID
    - When: PATCH /production-runs/999999
    - Then: Should return 404

48. **test_delete_nonexistent_run_404**
    - Given: Non-existent run ID
    - When: DELETE /production-runs/999999
    - Then: Should return 404

49. **test_create_with_invalid_payload**
    - Given: Missing required fields
    - When: POST /production-runs with incomplete data
    - Then: Should return 422 with validation errors

50. **test_update_with_invalid_data_types**
    - Given: Wrong data types in payload
    - When: PATCH /production-runs/1 with {run_number: 123}
    - Then: Should return 422 validation error

---

## Test Execution Plan

### Phase 1: Service Layer (Tests 1-35)
**Estimated Time**: 60-90 minutes
**Priority**: Highest impact on coverage

1. Set up test fixtures and helpers
2. Implement material cost tests (1-5)
3. Implement variance tests (6-13)
4. Run coverage check → Should reach ~85%
5. Implement status transition tests (14-23)
6. Run coverage check → Should reach ~92%
7. Implement filtering tests (24-30)
8. Implement bulk operations (31-35)
9. Run final coverage → Should reach 95%+

### Phase 2: API Layer (Tests 36-50)
**Estimated Time**: 30-45 minutes
**Priority**: High - completes backend coverage

1. Implement query parameter tests (36-40)
2. Implement pagination tests (41-45)
3. Run coverage check → Should reach ~90%
4. Implement error response tests (46-50)
5. Run final coverage → Should reach 95%+

### Phase 3: Verification
**Estimated Time**: 10-15 minutes

1. Run full backend test suite
2. Generate coverage report
3. Verify targets met:
   - Service: ≥95%
   - API: ≥95%
4. Update CURRENT_SESSION.md
5. Commit changes

---

## Success Criteria

✅ Production Run Service coverage: ≥95%
✅ Production Runs API coverage: ≥95%
✅ All new tests passing
✅ No existing tests broken
✅ Test execution time: <30s total

---

## Implementation Notes

- Use existing fixtures from `conftest.py`
- Follow existing test patterns in `test_production_run_service.py`
- Mock external dependencies (spools, models)
- Use `pytest-asyncio` for async tests
- Group related tests in classes for organization
