/**
 * TypeScript types for Consumable Inventory API
 * These match the Pydantic schemas in backend/app/schemas/consumable.py
 */

// =============================================================================
// ConsumableType Types
// =============================================================================

// Base consumable type fields
export interface ConsumableTypeBase {
  sku: string // Unique SKU within tenant (e.g., MAG-3X1, INS-M3)
  name: string // Human-readable name (e.g., Magnet 3mm x 1mm)
  description?: string | null // Detailed description
  category?: string | null // magnets, inserts, hardware, finishing, packaging

  // Unit information
  unit_of_measure: string // each, ml, g, pack

  // Current pricing
  current_cost_per_unit?: number | null // Current cost per unit

  // Stock management
  quantity_on_hand: number // Current stock quantity
  reorder_point?: number | null // Stock level that triggers reorder alert
  reorder_quantity?: number | null // Suggested quantity to order

  // Supplier information
  preferred_supplier?: string | null // Preferred supplier/vendor name
  supplier_sku?: string | null // Supplier's SKU/product code
  supplier_url?: string | null // URL to purchase from supplier (e.g., Amazon)
  typical_lead_days?: number | null // Typical delivery time in days

  // Status
  is_active: boolean // Whether this consumable is active
}

// Create consumable type request (POST /api/v1/consumables/types)
export type ConsumableTypeCreate = ConsumableTypeBase

// Update consumable type request (PUT /api/v1/consumables/types/{id})
export interface ConsumableTypeUpdate {
  sku?: string
  name?: string
  description?: string | null
  category?: string | null
  unit_of_measure?: string
  current_cost_per_unit?: number | null
  quantity_on_hand?: number
  reorder_point?: number | null
  reorder_quantity?: number | null
  preferred_supplier?: string | null
  supplier_sku?: string | null
  supplier_url?: string | null
  typical_lead_days?: number | null
  is_active?: boolean
}

// Consumable type response
export interface ConsumableTypeResponse extends ConsumableTypeBase {
  id: string // UUID
  tenant_id: string // UUID
  created_at: string // ISO 8601 datetime
  updated_at: string // ISO 8601 datetime

  // Computed fields
  is_low_stock: boolean // Whether stock is below reorder point
  stock_value: number // Total value of stock on hand
}

// List response for consumable types
export interface ConsumableTypeListResponse {
  total: number
  consumables: ConsumableTypeResponse[]
  page: number
  page_size: number
}

// Query parameters for list endpoint
export interface ConsumableTypeListParams {
  page?: number
  page_size?: number
  search?: string
  category?: string
  is_active?: boolean
  low_stock_only?: boolean
}

// =============================================================================
// ConsumablePurchase Types
// =============================================================================

// Base purchase fields
export interface ConsumablePurchaseBase {
  consumable_type_id: string // UUID of consumable type
  quantity_purchased: number
  total_cost: number

  // Source
  supplier?: string | null
  order_reference?: string | null
  purchase_url?: string | null // URL to purchase (e.g., Amazon link)
  purchase_date?: string | null // ISO 8601 date

  notes?: string | null
}

// Create purchase request
export type ConsumablePurchaseCreate = ConsumablePurchaseBase

// Update purchase request
export interface ConsumablePurchaseUpdate {
  quantity_purchased?: number
  total_cost?: number
  supplier?: string | null
  order_reference?: string | null
  purchase_url?: string | null
  purchase_date?: string | null
  notes?: string | null
}

// Purchase response
export interface ConsumablePurchaseResponse extends ConsumablePurchaseBase {
  id: string // UUID
  tenant_id: string // UUID
  cost_per_unit: number
  quantity_remaining: number // For FIFO tracking
  created_at: string // ISO 8601 datetime
  updated_at: string // ISO 8601 datetime
}

// Purchase with nested type info
export interface ConsumablePurchaseWithType extends ConsumablePurchaseResponse {
  consumable_sku: string
  consumable_name: string
}

// List response for purchases
export interface ConsumablePurchaseListResponse {
  total: number
  purchases: ConsumablePurchaseWithType[]
  page: number
  page_size: number
}

// Query parameters for purchase list
export interface ConsumablePurchaseListParams {
  page?: number
  page_size?: number
  consumable_type_id?: string
}

// =============================================================================
// ConsumableUsage Types
// =============================================================================

// Usage type enum
export type UsageType = 'production' | 'adjustment' | 'waste' | 'return'

// Base usage fields
export interface ConsumableUsageBase {
  consumable_type_id: string // UUID
  quantity_used: number // Positive for usage, negative for returns

  // Optional links
  production_run_id?: string | null
  product_id?: string | null

  // Context
  usage_type: UsageType
  notes?: string | null
}

// Create usage request
export type ConsumableUsageCreate = ConsumableUsageBase

// Usage response
export interface ConsumableUsageResponse extends ConsumableUsageBase {
  id: string // UUID
  tenant_id: string // UUID
  cost_at_use?: number | null // Cost per unit at time of use
  total_cost: number // Total cost of this usage
  created_at: string // ISO 8601 datetime
  updated_at: string // ISO 8601 datetime
}

// Usage with nested details
export interface ConsumableUsageWithDetails extends ConsumableUsageResponse {
  consumable_sku: string
  consumable_name: string
}

// List response for usage
export interface ConsumableUsageListResponse {
  total: number
  usage: ConsumableUsageWithDetails[]
  page: number
  page_size: number
}

// Query parameters for usage list
export interface ConsumableUsageListParams {
  page?: number
  page_size?: number
  consumable_type_id?: string
  usage_type?: UsageType
}

// =============================================================================
// Stock Adjustment & Alerts
// =============================================================================

// Stock adjustment request
export interface StockAdjustment {
  quantity_adjustment: number // Positive to add, negative to remove
  reason: string // Required reason for adjustment
  notes?: string | null
}

// Low stock alert
export interface LowStockAlert {
  consumable_id: string // UUID
  sku: string
  name: string
  quantity_on_hand: number
  reorder_point: number
  reorder_quantity?: number | null
  preferred_supplier?: string | null
  stock_value: number
}

// =============================================================================
// Consumable Categories (Common values)
// =============================================================================

export const CONSUMABLE_CATEGORIES = [
  'magnets',
  'inserts',
  'hardware',
  'finishing',
  'packaging',
  'adhesives',
  'other',
] as const

export type ConsumableCategory = (typeof CONSUMABLE_CATEGORIES)[number]

// =============================================================================
// Units of Measure (Common values)
// =============================================================================

export const UNITS_OF_MEASURE = [
  'each',
  'pack',
  'box',
  'g',
  'kg',
  'ml',
  'L',
  'meter',
  'foot',
] as const

export type UnitOfMeasure = (typeof UNITS_OF_MEASURE)[number]
