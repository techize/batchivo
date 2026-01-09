# Test Coverage Roadmap to 100%
**Project**: Nozzly.app
**Date**: 2025-12-12
**Current Status**: 53% backend coverage, 32/34 unit tests passing
**Target**: 100% unit test coverage, 100% integration test coverage

## Current State Analysis

### ✅ Existing Test Coverage

**Unit Tests (32/34 passing - 94%)**:
- ✅ `test_production_run_schemas.py` - 16/16 tests (100%)
- ✅ `test_production_run_service.py` - 16/18 tests (89%)

**Integration Tests (43/82 - 52%)**:
- ✅ `test_auth_api.py` - 15 tests (auth endpoints, security)
- ✅ `test_production_runs_api.py` - 28 tests (CRUD, items, materials, completion)
- ✅ `test_products_api.py` - 11 tests (CRUD, tenant isolation, cost calculation)
- ✅ `test_spools_api.py` - 11 tests (CRUD, inventory management, tenant isolation)
- ✅ `test_auth_flow.py` - 7 tests (full auth flow, tenant isolation)

**Total**: 82 integration tests + 34 unit tests = **116 tests**

---

## 🎯 Missing Test Coverage - Analysis

### 1. API Endpoints WITHOUT Integration Tests

| API File | Endpoints | Priority | Complexity | Est. Tests |
|----------|-----------|----------|------------|------------|
| `analytics.py` | Product variance, run variance, production history, spool usage | **HIGH** | Medium | 8-12 |
| `consumables.py` | CRUD operations for consumables | Medium | Low | 6-8 |
| `dashboard.py` | Active runs, low stock, recent activity, KPIs | **HIGH** | Medium | 8-10 |
| `models.py` | CRUD operations for 3D models | Medium | Low | 6-8 |
| `orders.py` | CRUD, order fulfillment, status tracking | **HIGH** | High | 10-15 |
| `payments.py` | Square integration, payment processing, refunds | **CRITICAL** | High | 12-18 |
| `sales_channels.py` | CRUD, channel configuration | Medium | Low | 6-8 |
| `shop.py` | Public storefront, checkout, webhook handling | **CRITICAL** | High | 15-20 |
| `sku.py` | SKU generation, validation | Low | Low | 4-6 |
| `spoolmandb.py` | External API integration, sync | Medium | Medium | 8-10 |
| `users.py` | User management, profile, preferences | Medium | Low | 6-8 |

**Total Estimated**: **89-123 new integration tests needed**

---

### 2. Services WITHOUT Unit Tests

| Service File | Functionality | Priority | Complexity | Est. Tests |
|--------------|---------------|----------|------------|------------|
| `costing.py` | Material cost calculations, pricing | **HIGH** | Medium | 8-12 |
| `inventory_transaction.py` | Stock movements, history tracking | **HIGH** | Medium | 10-15 |
| `sku_generator.py` | SKU generation logic, uniqueness | Medium | Low | 6-8 |
| `spoolmandb_sync.py` | External sync, data mapping | Medium | Medium | 8-10 |
| `square_payment.py` | Payment processing, refund logic | **CRITICAL** | High | 12-18 |

**Total Estimated**: **44-63 new unit tests needed**

---

### 3. Schemas WITHOUT Unit Tests

| Schema File | Models | Priority | Complexity | Est. Tests |
|-------------|--------|----------|------------|------------|
| `auth.py` | Login, Register, Token, User responses | **HIGH** | Low | 8-12 |
| `consumable.py` | Consumable CRUD schemas | Medium | Low | 6-8 |
| `inventory_transaction.py` | Transaction create/response schemas | **HIGH** | Medium | 8-10 |
| `material.py` | Material type schemas | Low | Low | 4-6 |
| `model.py` | 3D model schemas | Medium | Low | 6-8 |
| `payment.py` | Payment request/response schemas | **CRITICAL** | Medium | 10-15 |
| `product.py` | Product CRUD schemas | **HIGH** | Medium | 8-12 |
| `sales_channel.py` | Channel configuration schemas | Medium | Low | 6-8 |
| `spool.py` | Spool CRUD, weighing schemas | **HIGH** | Medium | 10-15 |
| `spoolmandb.py` | Sync request/response schemas | Low | Low | 4-6 |

**Total Estimated**: **70-100 new schema unit tests needed**

---

## 📋 Detailed Test Requirements by Area

### CRITICAL Priority (Security & Revenue)

#### 1. Payment Processing Tests (`payments.py`, `square_payment.py`, `payment.py`)
**Priority**: CRITICAL - Revenue generating functionality

**Integration Tests (`test_payments_api.py`)**: ~15-18 tests
- ✅ Square Integration
  - [ ] `test_create_payment_intent_success` - Create payment with Square
  - [ ] `test_create_payment_intent_invalid_amount` - Validate amount > 0
  - [ ] `test_process_payment_success` - Complete payment flow
  - [ ] `test_process_payment_card_declined` - Handle declined cards
  - [ ] `test_process_payment_insufficient_funds` - Handle insufficient funds

- ✅ Refund Processing
  - [ ] `test_refund_payment_full` - Full refund processing
  - [ ] `test_refund_payment_partial` - Partial refund processing
  - [ ] `test_refund_already_refunded` - Prevent duplicate refunds
  - [ ] `test_refund_amount_exceeds_original` - Validate refund amount

- ✅ Payment Status & History
  - [ ] `test_list_payments_for_order` - Get payment history
  - [ ] `test_payment_status_tracking` - Track payment lifecycle
  - [ ] `test_payment_webhook_handling` - Square webhook processing

- ✅ Security & Validation
  - [ ] `test_payment_requires_authentication` - Auth required
  - [ ] `test_payment_tenant_isolation` - Tenant data isolation
  - [ ] `test_payment_amount_validation` - Min/max amount validation
  - [ ] `test_payment_currency_validation` - Currency validation
  - [ ] `test_payment_idempotency` - Prevent duplicate charges

- ✅ Error Handling
  - [ ] `test_payment_network_error_retry` - Retry logic
  - [ ] `test_payment_square_api_error` - Handle Square errors

**Service Tests (`test_square_payment_service.py`)**: ~12-15 tests
- ✅ Payment Creation
  - [ ] `test_create_square_payment_success` - Create payment with Square API
  - [ ] `test_create_payment_amount_conversion` - Decimal to cents conversion
  - [ ] `test_create_payment_with_customer_id` - Link to customer
  - [ ] `test_create_payment_idempotency_key` - Prevent duplicates

- ✅ Refund Logic
  - [ ] `test_process_refund_full_amount` - Full refund calculation
  - [ ] `test_process_refund_partial_amount` - Partial refund calculation
  - [ ] `test_refund_validation_rules` - Validate refund business rules

- ✅ Payment Verification
  - [ ] `test_verify_payment_status` - Check payment status with Square
  - [ ] `test_verify_payment_not_found` - Handle missing payments

- ✅ Webhook Processing
  - [ ] `test_process_webhook_payment_completed` - Handle successful webhook
  - [ ] `test_process_webhook_payment_failed` - Handle failed webhook
  - [ ] `test_process_webhook_signature_validation` - Verify webhook signatures

- ✅ Error Scenarios
  - [ ] `test_payment_square_api_timeout` - Handle API timeouts
  - [ ] `test_payment_invalid_credentials` - Handle auth failures
  - [ ] `test_payment_rate_limit_exceeded` - Handle rate limiting

**Schema Tests (`test_payment_schemas.py`)**: ~10-12 tests
- ✅ Request Validation
  - [ ] `test_payment_create_valid` - Valid payment request
  - [ ] `test_payment_create_invalid_amount` - Amount validation
  - [ ] `test_payment_create_missing_fields` - Required fields
  - [ ] `test_refund_request_valid` - Valid refund request
  - [ ] `test_refund_request_invalid_amount` - Refund amount validation

- ✅ Response Schemas
  - [ ] `test_payment_response_structure` - Payment response format
  - [ ] `test_payment_status_enum_values` - Valid status values
  - [ ] `test_refund_response_structure` - Refund response format

- ✅ Computed Fields
  - [ ] `test_payment_total_with_tax` - Calculate total with tax
  - [ ] `test_payment_refund_remaining` - Calculate refundable amount
  - [ ] `test_payment_currency_formatting` - Currency display format

---

#### 2. Shop/Storefront Tests (`shop.py`)
**Priority**: CRITICAL - Public-facing revenue generator

**Integration Tests (`test_shop_api.py`)**: ~15-18 tests
- ✅ Product Catalog
  - [ ] `test_list_products_public` - Public product listing
  - [ ] `test_get_product_details_public` - Product detail page
  - [ ] `test_product_images_accessible` - Image URLs work
  - [ ] `test_product_filtering` - Filter by category/price
  - [ ] `test_product_search` - Search functionality

- ✅ Shopping Cart
  - [ ] `test_add_to_cart` - Add product to cart
  - [ ] `test_update_cart_quantity` - Update item quantity
  - [ ] `test_remove_from_cart` - Remove cart item
  - [ ] `test_cart_total_calculation` - Calculate cart total
  - [ ] `test_cart_session_persistence` - Cart persists across sessions

- ✅ Checkout Flow
  - [ ] `test_checkout_initiate` - Start checkout process
  - [ ] `test_checkout_calculate_shipping` - Shipping cost calculation
  - [ ] `test_checkout_apply_discount_code` - Discount code validation
  - [ ] `test_checkout_create_order` - Create order from cart
  - [ ] `test_checkout_payment_processing` - Process payment

- ✅ Order Confirmation
  - [ ] `test_order_confirmation_email` - Email sent
  - [ ] `test_order_tracking_number` - Tracking number generated
  - [ ] `test_order_status_updates` - Status change notifications

---

#### 3. Analytics & Dashboard Tests
**Priority**: HIGH - Business intelligence

**Integration Tests (`test_analytics_api.py`)**: ~10-12 tests
- ✅ Product Analytics
  - [ ] `test_get_product_variance_analysis` - Product variance metrics
  - [ ] `test_get_top_performing_products` - Best sellers
  - [ ] `test_get_product_success_rate` - Success rate by product

- ✅ Production Analytics
  - [ ] `test_get_run_variance_analysis` - Production run variance
  - [ ] `test_get_production_history` - Historical production data
  - [ ] `test_get_material_usage_trends` - Material consumption trends

- ✅ Cost Analytics
  - [ ] `test_get_spool_cost_analysis` - Cost per gram analysis
  - [ ] `test_get_cost_savings_opportunities` - Cost reduction insights

- ✅ Time-based Analytics
  - [ ] `test_analytics_date_range_filtering` - Filter by date range
  - [ ] `test_analytics_aggregation_by_period` - Daily/weekly/monthly aggregation

- ✅ Performance
  - [ ] `test_analytics_query_performance` - Queries complete < 2s
  - [ ] `test_analytics_pagination` - Large datasets paginated

**Integration Tests (`test_dashboard_api.py`)**: ~8-10 tests
- ✅ Dashboard KPIs
  - [ ] `test_get_dashboard_summary` - Overall KPI summary
  - [ ] `test_get_active_production_runs` - Currently running jobs
  - [ ] `test_get_low_stock_alerts` - Inventory warnings
  - [ ] `test_get_recent_activity` - Recent system activity

- ✅ Real-time Updates
  - [ ] `test_dashboard_live_updates` - Real-time data refresh
  - [ ] `test_dashboard_filters` - Filter by date/status

- ✅ Performance Metrics
  - [ ] `test_dashboard_success_rate` - Overall success rate
  - [ ] `test_dashboard_material_efficiency` - Material waste metrics

- ✅ Tenant Isolation
  - [ ] `test_dashboard_tenant_data_only` - Only shows tenant data
  - [ ] `test_dashboard_unauthorized_access` - Requires auth

---

### HIGH Priority (Core Functionality)

#### 4. Order Management Tests (`orders.py`)
**Priority**: HIGH - Core business process

**Integration Tests (`test_orders_api.py`)**: ~12-15 tests
- ✅ Order CRUD
  - [ ] `test_create_order_minimal` - Create with required fields
  - [ ] `test_create_order_full` - Create with all fields
  - [ ] `test_list_orders` - List with pagination
  - [ ] `test_get_order_by_id` - Get order details
  - [ ] `test_update_order_status` - Update order status
  - [ ] `test_delete_order` - Delete order (soft delete)

- ✅ Order Items
  - [ ] `test_add_item_to_order` - Add product to order
  - [ ] `test_update_order_item_quantity` - Update quantity
  - [ ] `test_remove_item_from_order` - Remove item
  - [ ] `test_order_total_calculation` - Calculate order total

- ✅ Order Fulfillment
  - [ ] `test_mark_order_fulfilled` - Mark as fulfilled
  - [ ] `test_order_shipping_tracking` - Add tracking info
  - [ ] `test_order_fulfillment_deducts_inventory` - Inventory updated

- ✅ Order Status
  - [ ] `test_order_status_transitions` - Valid status changes
  - [ ] `test_order_cancellation` - Cancel order
  - [ ] `test_order_refund_processing` - Process refund

#### 5. Inventory Transaction Tests (`inventory_transaction.py`)
**Priority**: HIGH - Critical for inventory accuracy

**Service Tests (`test_inventory_transaction_service.py`)**: ~12-15 tests
- ✅ Transaction Creation
  - [ ] `test_create_transaction_addition` - Add stock transaction
  - [ ] `test_create_transaction_deduction` - Deduct stock transaction
  - [ ] `test_create_transaction_adjustment` - Adjustment transaction
  - [ ] `test_create_transaction_validates_spool_exists` - Spool validation

- ✅ Transaction History
  - [ ] `test_list_transactions_for_spool` - Get spool history
  - [ ] `test_list_transactions_pagination` - Paginated results
  - [ ] `test_list_transactions_filter_by_type` - Filter by transaction type
  - [ ] `test_list_transactions_filter_by_date` - Date range filtering

- ✅ Balance Calculation
  - [ ] `test_calculate_current_balance` - Current stock level
  - [ ] `test_calculate_balance_at_date` - Historical balance
  - [ ] `test_balance_negative_prevention` - Prevent negative stock

- ✅ Transaction Reversal
  - [ ] `test_reverse_transaction` - Reverse/undo transaction
  - [ ] `test_reverse_nonexistent_transaction` - Handle missing transaction

- ✅ Audit Trail
  - [ ] `test_transaction_audit_metadata` - User, timestamp recorded
  - [ ] `test_transaction_reason_required` - Reason for adjustments

**Schema Tests (`test_inventory_transaction_schemas.py`)**: ~8-10 tests
- ✅ Transaction Types
  - [ ] `test_transaction_create_addition` - Addition schema
  - [ ] `test_transaction_create_deduction` - Deduction schema
  - [ ] `test_transaction_create_adjustment` - Adjustment schema
  - [ ] `test_transaction_type_validation` - Valid types only

- ✅ Quantity Validation
  - [ ] `test_transaction_positive_quantity` - Quantity > 0
  - [ ] `test_transaction_decimal_precision` - Decimal precision

- ✅ Response Schema
  - [ ] `test_transaction_response_structure` - Response format
  - [ ] `test_transaction_computed_balance` - Running balance

- ✅ Required Fields
  - [ ] `test_transaction_missing_spool_id` - Spool ID required
  - [ ] `test_transaction_missing_quantity` - Quantity required

#### 6. Costing Service Tests (`costing.py`)
**Priority**: HIGH - Accurate pricing critical

**Service Tests (`test_costing_service.py`)**: ~10-12 tests
- ✅ Material Cost Calculation
  - [ ] `test_calculate_material_cost_basic` - Base material cost
  - [ ] `test_calculate_material_cost_with_waste` - Include waste factor
  - [ ] `test_calculate_material_cost_multi_color` - Multi-material prints
  - [ ] `test_calculate_material_cost_tower` - Purge tower cost

- ✅ Labor Cost Calculation
  - [ ] `test_calculate_labor_cost_by_time` - Time-based labor
  - [ ] `test_calculate_labor_cost_by_complexity` - Complexity factor

- ✅ Total Product Cost
  - [ ] `test_calculate_total_product_cost` - Material + labor + overhead
  - [ ] `test_calculate_cost_with_markup` - Apply profit margin
  - [ ] `test_calculate_bulk_discount` - Quantity discounts

- ✅ Cost Breakdown
  - [ ] `test_get_cost_breakdown_detailed` - Itemized cost breakdown
  - [ ] `test_get_cost_comparison_estimated_vs_actual` - Compare estimates

- ✅ Edge Cases
  - [ ] `test_cost_calculation_zero_quantity` - Handle zero quantity
  - [ ] `test_cost_calculation_rounding` - Proper decimal rounding

---

### MEDIUM Priority (Extended Functionality)

#### 7. Models/3D Models Tests (`models.py`)
**Integration Tests (`test_models_api.py`)**: ~6-8 tests
- [ ] `test_create_model` - Upload 3D model
- [ ] `test_list_models` - List models with pagination
- [ ] `test_get_model_by_id` - Get model details
- [ ] `test_update_model_metadata` - Update model info
- [ ] `test_delete_model` - Delete model
- [ ] `test_model_file_validation` - Validate file types (.stl, .3mf)
- [ ] `test_model_tenant_isolation` - Tenant data isolation
- [ ] `test_model_storage_integration` - File upload to storage

#### 8. Consumables Tests (`consumables.py`)
**Integration Tests (`test_consumables_api.py`)**: ~6-8 tests
- [ ] `test_create_consumable` - Create consumable (nozzles, build plates)
- [ ] `test_list_consumables` - List all consumables
- [ ] `test_get_consumable_by_id` - Get consumable details
- [ ] `test_update_consumable` - Update consumable info
- [ ] `test_delete_consumable` - Delete consumable
- [ ] `test_consumable_usage_tracking` - Track usage/replacement
- [ ] `test_consumable_low_stock_alert` - Alert when low
- [ ] `test_consumable_tenant_isolation` - Tenant data isolation

**Schema Tests (`test_consumable_schemas.py`)**: ~6-8 tests
- [ ] `test_consumable_create_valid` - Valid create schema
- [ ] `test_consumable_create_missing_fields` - Required fields
- [ ] `test_consumable_type_validation` - Valid consumable types
- [ ] `test_consumable_quantity_positive` - Quantity > 0
- [ ] `test_consumable_response_structure` - Response format
- [ ] `test_consumable_usage_history` - Usage tracking schema

#### 9. Sales Channels Tests (`sales_channels.py`)
**Integration Tests (`test_sales_channels_api.py`)**: ~6-8 tests
- [ ] `test_create_sales_channel` - Create channel (Etsy, eBay, etc.)
- [ ] `test_list_sales_channels` - List all channels
- [ ] `test_get_sales_channel_by_id` - Get channel details
- [ ] `test_update_sales_channel` - Update channel config
- [ ] `test_delete_sales_channel` - Delete channel
- [ ] `test_sales_channel_authentication` - OAuth/API key validation
- [ ] `test_sales_channel_sync` - Sync products to channel
- [ ] `test_sales_channel_tenant_isolation` - Tenant data isolation

**Schema Tests (`test_sales_channel_schemas.py`)**: ~6-8 tests
- [ ] `test_sales_channel_create_valid` - Valid create schema
- [ ] `test_sales_channel_type_validation` - Valid channel types
- [ ] `test_sales_channel_auth_required` - Auth credentials required
- [ ] `test_sales_channel_response_structure` - Response format

#### 10. SpoolmanDB Integration Tests (`spoolmandb.py`, `spoolmandb_sync.py`)
**Integration Tests (`test_spoolmandb_api.py`)**: ~8-10 tests
- [ ] `test_search_spoolmandb_materials` - Search external DB
- [ ] `test_import_material_from_spoolmandb` - Import material
- [ ] `test_sync_spool_with_spoolmandb` - Sync spool data
- [ ] `test_spoolmandb_auth_failure` - Handle auth errors
- [ ] `test_spoolmandb_network_timeout` - Handle timeouts
- [ ] `test_spoolmandb_rate_limiting` - Respect rate limits
- [ ] `test_spoolmandb_data_mapping` - Map external to internal format
- [ ] `test_spoolmandb_conflict_resolution` - Handle data conflicts

**Service Tests (`test_spoolmandb_sync_service.py`)**: ~8-10 tests
- [ ] `test_sync_material_types` - Sync material type catalog
- [ ] `test_sync_spool_data` - Sync spool information
- [ ] `test_sync_batch_operations` - Bulk sync operations
- [ ] `test_sync_error_recovery` - Handle sync failures
- [ ] `test_sync_duplicate_detection` - Prevent duplicates
- [ ] `test_sync_data_validation` - Validate imported data
- [ ] `test_sync_timestamp_tracking` - Track last sync time
- [ ] `test_sync_conflict_resolution_strategy` - Resolve conflicts

#### 11. User Management Tests (`users.py`)
**Integration Tests (`test_users_api.py`)**: ~6-8 tests
- [ ] `test_get_current_user_profile` - Get logged-in user info
- [ ] `test_update_user_profile` - Update profile
- [ ] `test_update_user_preferences` - Update preferences
- [ ] `test_change_password` - Change user password
- [ ] `test_delete_user_account` - Delete account
- [ ] `test_list_users_admin_only` - Admin can list users
- [ ] `test_user_activity_log` - Track user activity
- [ ] `test_user_tenant_isolation` - Tenant data isolation

#### 12. SKU Generator Tests (`sku.py`, `sku_generator.py`)
**Integration Tests (`test_sku_api.py`)**: ~4-6 tests
- [ ] `test_generate_sku_for_product` - Generate unique SKU
- [ ] `test_validate_sku_format` - Validate SKU format
- [ ] `test_sku_uniqueness_check` - Check SKU uniqueness
- [ ] `test_sku_pattern_configuration` - Configure SKU pattern

**Service Tests (`test_sku_generator_service.py`)**: ~6-8 tests
- [ ] `test_generate_sku_default_pattern` - Default pattern
- [ ] `test_generate_sku_custom_pattern` - Custom pattern
- [ ] `test_generate_sku_sequential_number` - Sequential numbering
- [ ] `test_generate_sku_uniqueness` - Ensure uniqueness
- [ ] `test_generate_sku_prefix_suffix` - Custom prefix/suffix
- [ ] `test_validate_sku_format_valid` - Valid format check
- [ ] `test_validate_sku_format_invalid` - Invalid format check

---

### LOW Priority (Nice to Have)

#### 13. Additional Schema Tests

**Auth Schemas (`test_auth_schemas.py`)**: ~8-10 tests
- [ ] `test_login_request_valid` - Valid login request
- [ ] `test_login_request_invalid_email` - Email validation
- [ ] `test_register_request_valid` - Valid registration
- [ ] `test_register_password_complexity` - Password requirements
- [ ] `test_token_response_structure` - Token response format
- [ ] `test_user_response_no_password` - Password excluded from response

**Product Schemas (`test_product_schemas.py`)**: ~8-10 tests
- [ ] `test_product_create_valid` - Valid product create
- [ ] `test_product_create_missing_fields` - Required fields
- [ ] `test_product_price_positive` - Price > 0
- [ ] `test_product_sku_format` - SKU validation
- [ ] `test_product_response_structure` - Response format
- [ ] `test_product_with_images` - Image URLs included

**Spool Schemas (`test_spool_schemas.py`)**: ~10-12 tests
- [ ] `test_spool_create_valid` - Valid spool create
- [ ] `test_spool_create_missing_fields` - Required fields
- [ ] `test_spool_weight_positive` - Weight > 0
- [ ] `test_spool_material_type_validation` - Valid material types
- [ ] `test_spool_response_structure` - Response format
- [ ] `test_spool_remaining_weight_computed` - Computed field
- [ ] `test_spool_cost_per_gram_computed` - Computed field

**Material Type Schemas (`test_material_schemas.py`)**: ~4-6 tests
- [ ] `test_material_type_create_valid` - Valid material type
- [ ] `test_material_type_code_unique` - Unique code validation
- [ ] `test_material_type_properties` - Temperature, density fields
- [ ] `test_material_type_response_structure` - Response format

**Model Schemas (`test_model_schemas.py`)**: ~6-8 tests
- [ ] `test_model_create_valid` - Valid 3D model create
- [ ] `test_model_file_type_validation` - Valid file types
- [ ] `test_model_dimensions` - Size/volume fields
- [ ] `test_model_response_structure` - Response format

---

## 📊 Test Effort Estimation Summary

| Category | Tests Needed | Priority | Estimated Effort |
|----------|--------------|----------|------------------|
| **Payment & Shop** | 45-56 tests | CRITICAL | 20-25 hours |
| **Analytics & Dashboard** | 18-22 tests | HIGH | 8-10 hours |
| **Order Management** | 12-15 tests | HIGH | 6-8 hours |
| **Inventory Transactions** | 20-25 tests | HIGH | 10-12 hours |
| **Costing Service** | 10-12 tests | HIGH | 5-6 hours |
| **Models & Consumables** | 12-16 tests | MEDIUM | 6-8 hours |
| **Sales Channels** | 12-16 tests | MEDIUM | 6-8 hours |
| **SpoolmanDB Integration** | 16-20 tests | MEDIUM | 8-10 hours |
| **User Management** | 6-8 tests | MEDIUM | 3-4 hours |
| **SKU Generator** | 10-14 tests | LOW | 4-6 hours |
| **Additional Schemas** | 36-48 tests | LOW | 8-12 hours |
| **TOTAL** | **197-252 tests** | - | **84-109 hours** |

---

## 🎯 Recommended Phased Approach

### Phase 1: Critical Security & Revenue (Week 1-2)
**Focus**: Payment processing, shop/storefront
**Tests**: 45-56 tests
**Effort**: 20-25 hours
**Risk Reduction**: HIGH (protects revenue stream)

**Deliverables**:
- ✅ `test_payments_api.py` - 15-18 integration tests
- ✅ `test_square_payment_service.py` - 12-15 unit tests
- ✅ `test_payment_schemas.py` - 10-12 unit tests
- ✅ `test_shop_api.py` - 15-18 integration tests

### Phase 2: Analytics & Business Intelligence (Week 3)
**Focus**: Dashboard, analytics, reporting
**Tests**: 18-22 tests
**Effort**: 8-10 hours
**Business Value**: HIGH (data-driven decisions)

**Deliverables**:
- ✅ `test_analytics_api.py` - 10-12 integration tests
- ✅ `test_dashboard_api.py` - 8-10 integration tests

### Phase 3: Core Operations (Week 4)
**Focus**: Orders, inventory, costing
**Tests**: 42-52 tests
**Effort**: 21-26 hours
**Operational Impact**: HIGH (daily operations)

**Deliverables**:
- ✅ `test_orders_api.py` - 12-15 integration tests
- ✅ `test_inventory_transaction_service.py` - 12-15 unit tests
- ✅ `test_inventory_transaction_schemas.py` - 8-10 unit tests
- ✅ `test_costing_service.py` - 10-12 unit tests

### Phase 4: Extended Functionality (Week 5-6)
**Focus**: Models, consumables, channels, sync
**Tests**: 48-64 tests
**Effort**: 23-32 hours
**Feature Completeness**: MEDIUM

**Deliverables**:
- ✅ `test_models_api.py` - 6-8 integration tests
- ✅ `test_consumables_api.py` - 6-8 integration tests
- ✅ `test_consumable_schemas.py` - 6-8 unit tests
- ✅ `test_sales_channels_api.py` - 6-8 integration tests
- ✅ `test_sales_channel_schemas.py` - 6-8 unit tests
- ✅ `test_spoolmandb_api.py` - 8-10 integration tests
- ✅ `test_spoolmandb_sync_service.py` - 8-10 unit tests
- ✅ `test_users_api.py` - 6-8 integration tests

### Phase 5: Completeness & Polish (Week 7-8)
**Focus**: SKU, schemas, edge cases
**Tests**: 46-62 tests
**Effort**: 12-18 hours
**Coverage Goal**: 100%

**Deliverables**:
- ✅ All remaining schema tests
- ✅ SKU generator tests
- ✅ Edge case coverage
- ✅ Performance tests
- ✅ Error scenario coverage

---

## 🔧 Testing Infrastructure Improvements Needed

### 1. Fix Current Issues
**Priority**: CRITICAL - Must fix before adding new tests

- [ ] **Database Fixtures** - Fix UNIQUE constraint errors in integration tests
  - Issue: `material_types.code` constraint violations
  - Impact: 39 integration test failures
  - Effort: 2-4 hours

- [ ] **Async Service Tests** - Fix SQLAlchemy session issues
  - Issue: Lazy loading in async context
  - Impact: 2 service test failures
  - Effort: 2-3 hours

- [ ] **Frontend Test Assertions** - Fix SpoolList test data/mocks
  - Issue: Assertion and data loading failures
  - Impact: 15 frontend test failures
  - Effort: 4-6 hours

### 2. Testing Infrastructure Enhancements

- [ ] **Test Data Factories** - Create factory pattern for test data
  ```python
  # Example: tests/factories.py
  class ProductFactory:
      @staticmethod
      def create(**kwargs):
          defaults = {
              "name": "Test Product",
              "sku": f"TEST-{uuid4().hex[:8]}",
              "price": Decimal("10.00")
          }
          return Product(**{**defaults, **kwargs})
  ```

- [ ] **Shared Fixtures** - Centralize common fixtures
  - Payment fixtures (mock Square responses)
  - Order fixtures (complete order workflow)
  - User fixtures (different permission levels)

- [ ] **API Test Helpers** - Create helper functions
  ```python
  async def create_test_order(client, **kwargs):
      """Helper to create a test order with sensible defaults."""
      ...

  async def assert_payment_successful(response):
      """Helper to verify payment response format."""
      ...
  ```

- [ ] **Mock External Services** - Centralize external API mocks
  - Square API mock responses
  - SpoolmanDB API mocks
  - Email service mocks
  - Storage service mocks

### 3. Test Coverage Monitoring

- [ ] **Coverage Enforcement** - Add coverage thresholds to CI
  ```yaml
  # .github/workflows/ci.yml
  - name: Check coverage thresholds
    run: |
      poetry run pytest --cov --cov-fail-under=80
  ```

- [ ] **Coverage Badges** - Add badges to README
  - Backend unit coverage
  - Backend integration coverage
  - Frontend coverage

- [ ] **Coverage Reporting** - Enhanced coverage reports
  - Missing lines report
  - Branch coverage
  - Function coverage

---

## 📋 Test Writing Guidelines

### Integration Test Template
```python
import pytest
from httpx import AsyncClient

class TestFeatureEndpoints:
    """Test Feature API endpoints."""

    @pytest.mark.asyncio
    async def test_create_feature_success(
        self,
        client: AsyncClient,
        test_user,
        test_tenant
    ):
        """Test creating a feature with valid data."""
        # Arrange
        data = {
            "name": "Test Feature",
            "value": 100
        }

        # Act
        response = await client.post(
            "/api/v1/features",
            json=data,
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

        # Assert
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == data["name"]
        assert result["value"] == data["value"]
        assert "id" in result
        assert result["tenant_id"] == str(test_tenant.id)
```

### Unit Test Template (Service)
```python
import pytest
from decimal import Decimal

class TestFeatureService:
    """Test Feature service business logic."""

    @pytest.mark.asyncio
    async def test_calculate_feature_value(
        self,
        db_session,
        test_tenant
    ):
        """Test feature value calculation."""
        # Arrange
        service = FeatureService(db_session, test_tenant)
        input_value = Decimal("100.00")

        # Act
        result = await service.calculate_value(input_value)

        # Assert
        assert result == Decimal("110.00")  # 10% markup
        assert isinstance(result, Decimal)
```

### Unit Test Template (Schema)
```python
import pytest
from pydantic import ValidationError
from decimal import Decimal

class TestFeatureSchemas:
    """Test Feature Pydantic schemas."""

    def test_feature_create_valid(self):
        """Test creating feature with valid data."""
        data = {
            "name": "Test Feature",
            "value": Decimal("100.00")
        }
        feature = FeatureCreate(**data)

        assert feature.name == "Test Feature"
        assert feature.value == Decimal("100.00")

    def test_feature_create_invalid_value(self):
        """Test that negative value raises ValidationError."""
        data = {
            "name": "Test Feature",
            "value": Decimal("-10.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            FeatureCreate(**data)

        assert "greater than 0" in str(exc_info.value)
```

---

## 🎯 Success Criteria

### Phase Completion Criteria
- [ ] **Phase 1**: Payment & shop tests passing (45+ tests, 0 failures)
- [ ] **Phase 2**: Analytics tests passing (18+ tests, 0 failures)
- [ ] **Phase 3**: Operations tests passing (42+ tests, 0 failures)
- [ ] **Phase 4**: Extended features tested (48+ tests, 0 failures)
- [ ] **Phase 5**: 100% unit coverage, 100% integration coverage

### Overall Success Metrics
- [ ] **Backend Unit Coverage**: 100% (currently 53%)
- [ ] **Backend Integration Coverage**: 100% (all endpoints tested)
- [ ] **Frontend Unit Coverage**: 80%+ (currently 17%)
- [ ] **CI Pipeline**: All tests passing in CI
- [ ] **Test Execution Time**: < 5 minutes total
- [ ] **Test Reliability**: < 1% flaky test rate

---

## 📝 Next Steps

1. **Immediate (This Week)**:
   - Fix database fixtures (39 failing integration tests)
   - Fix 2 async service tests
   - Create `test_payments_api.py` skeleton

2. **Short-term (Next 2 Weeks)**:
   - Complete Phase 1 (Payment & Shop tests)
   - Create test data factories
   - Set up coverage enforcement in CI

3. **Medium-term (Next 4-6 Weeks)**:
   - Complete Phases 2-3 (Analytics, Operations)
   - Reach 80%+ backend coverage
   - Fix frontend tests

4. **Long-term (Next 2-3 Months)**:
   - Complete Phases 4-5 (Extended features, 100% coverage)
   - Add E2E tests with Playwright
   - Add performance/load tests

---

**Prepared by**: Nexus (Claude Code)
**Date**: 2025-12-12
**Project**: Nozzly.app Test Coverage Initiative
**Total Estimated Tests**: 197-252 new tests
**Total Estimated Effort**: 84-109 hours (10-14 working days)
