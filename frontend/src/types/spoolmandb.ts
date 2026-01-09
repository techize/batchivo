/**
 * SpoolmanDB types - Community filament database
 */

export interface SpoolmanDBManufacturer {
  id: string
  name: string
  is_active: boolean
  created_at: string
  updated_at: string
  filament_count?: number
}

export interface SpoolmanDBFilament {
  id: string
  external_id: string
  manufacturer_id: string
  manufacturer_name: string
  name: string
  material: string
  density: number | null
  diameter: number
  weight: number
  spool_weight: number | null
  spool_type: string | null
  color_name: string | null
  color_hex: string | null
  extruder_temp: number | null
  bed_temp: number | null
  finish: string | null
  translucent: boolean
  glow: boolean
  pattern: string | null
  multi_color_direction: string | null
  color_hexes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SpoolmanDBManufacturerListResponse {
  manufacturers: SpoolmanDBManufacturer[]
  total: number
}

export interface SpoolmanDBFilamentListResponse {
  filaments: SpoolmanDBFilament[]
  total: number
  page: number
  page_size: number
}

export interface SpoolmanDBFilamentListParams {
  page?: number
  page_size?: number
  manufacturer_id?: string
  manufacturer_name?: string
  material?: string
  search?: string
  diameter?: number
}

export interface SpoolmanDBStats {
  total_manufacturers: number
  total_filaments: number
  materials: string[]
  last_sync: string | null
}

export interface SpoolmanDBSyncResponse {
  success: boolean
  manufacturers_added: number
  manufacturers_updated: number
  filaments_added: number
  filaments_updated: number
  message: string
}
