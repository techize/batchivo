/**
 * TypeScript types for FilamentType API — matches Pydantic schemas in backend/app/schemas/filament_type.py
 */

// Aggregated filament type list item — one row per unique brand+color+material combination
export interface FilamentTypeListItem {
  id: string
  brand: string
  color: string
  color_hex?: string | null // Hex color code (e.g., FF5733)
  material_type_name: string
  material_type_code: string
  has_sample: boolean
  spool_count: number
  labeled_count: number
}

// Paginated list response (GET /api/v1/filament-types/aggregated)
export interface FilamentTypeAggregatedListResponse {
  total: number
  filament_types: FilamentTypeListItem[]
  page: number
  page_size: number
}

// Query parameters for the aggregated list endpoint
export interface FilamentTypeListParams {
  page?: number
  page_size?: number
  brand?: string
  color?: string
  material_type_id?: string
  needs_labels?: boolean
  needs_sample?: boolean
}

// Individual spool entry within a filament type sheet
export interface SpoolInSheet {
  id: string
  spool_id: string
  current_weight: number
  initial_weight: number
  is_labeled: boolean
  is_active: boolean
}

// Partial update request (PUT /api/v1/filament-types/{id})
export interface FilamentTypeUpdate {
  has_sample?: boolean
  brand?: string
  color?: string
  color_hex?: string | null
  material_type_id?: string
  finish?: string | null
  diameter?: number
  extruder_temp?: number | null
  bed_temp?: number | null
  translucent?: boolean
  glow?: boolean
  notes?: string | null
}
