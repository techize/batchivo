/**
 * TypeScript types for Spool API
 * These match the Pydantic schemas in backend/app/schemas/spool.py
 */

// Base spool fields (used for creation and responses)
export interface SpoolBase {
  spool_id: string
  material_type_id: string // UUID
  brand: string
  color: string
  color_hex?: string | null // Hex color code (e.g., FF5733)
  finish?: string | null

  // Filament specifications
  diameter: number // Typically 1.75 or 2.85mm
  density?: number | null // g/cm³
  extruder_temp?: number | null // Recommended extruder temp °C
  bed_temp?: number | null // Recommended bed temp °C

  // Special filament properties
  translucent: boolean
  glow: boolean
  pattern?: string | null // marble, gradient, speckled, etc.
  spool_type?: string | null // cardboard, plastic, refill, etc.

  // Weight tracking
  initial_weight: number
  current_weight: number
  empty_spool_weight?: number | null

  // Purchase info
  purchase_date?: string | null // ISO 8601 date string
  purchase_price?: number | null
  supplier?: string | null

  // Batch tracking
  purchased_quantity: number
  spools_remaining: number

  // Organization
  storage_location?: string | null
  notes?: string | null
  qr_code_id?: string | null
  is_active: boolean
}

// Create spool request (POST /api/v1/spools)
export type SpoolCreate = SpoolBase

// Update spool request (PUT /api/v1/spools/{id})
// All fields are optional for partial updates
export interface SpoolUpdate {
  spool_id?: string
  material_type_id?: string
  brand?: string
  color?: string
  color_hex?: string | null
  finish?: string | null

  // Filament specifications
  diameter?: number
  density?: number | null
  extruder_temp?: number | null
  bed_temp?: number | null

  // Special filament properties
  translucent?: boolean
  glow?: boolean
  pattern?: string | null
  spool_type?: string | null

  initial_weight?: number
  current_weight?: number
  empty_spool_weight?: number | null

  purchase_date?: string | null
  purchase_price?: number | null
  supplier?: string | null

  purchased_quantity?: number
  spools_remaining?: number

  storage_location?: string | null
  notes?: string | null
  qr_code_id?: string | null
  is_active?: boolean
}

// Spool response (GET /api/v1/spools/{id} or in list)
export interface SpoolResponse extends SpoolBase {
  id: string // UUID
  tenant_id: string // UUID
  created_at: string // ISO 8601 datetime string
  updated_at: string // ISO 8601 datetime string

  // Computed fields
  remaining_weight: number
  remaining_percentage: number

  // Material type info
  material_type_code: string
  material_type_name: string
}

// List response (GET /api/v1/spools)
export interface SpoolListResponse {
  total: number
  spools: SpoolResponse[]
  page: number
  page_size: number
}

// Query parameters for list endpoint
export interface SpoolListParams {
  page?: number
  page_size?: number
  search?: string
  material_type_id?: string
  is_active?: boolean
  low_stock_only?: boolean
}

// Material Type (from backend reference data)
export interface MaterialType {
  id: string // UUID
  name: string
  code: string
  description?: string | null
  typical_density?: number | null
  typical_cost_per_kg?: number | null
  min_temp?: number | null
  max_temp?: number | null
  bed_temp?: number | null
  created_at: string
  updated_at: string
}
