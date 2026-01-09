/**
 * TypeScript types for Production Run system
 *
 * Mirrors the backend Pydantic schemas for type safety
 */

export type ProductionRunStatus = 'in_progress' | 'completed' | 'failed' | 'cancelled';

/**
 * Summary of a Model for embedding in responses
 */
export interface ModelSummary {
  id: string;
  sku: string;
  name: string;
  description?: string | null;
}

/**
 * Summary of a MaterialType for embedding in responses
 */
export interface MaterialTypeSummary {
  code: string;
  name: string;
}

/**
 * Summary of a Spool for embedding in responses
 */
export interface SpoolSummary {
  id: string;
  spool_id: string;  // User-friendly ID like FIL-001
  brand: string;
  color: string;
  color_hex?: string | null;
  finish?: string | null;
  material_type?: MaterialTypeSummary | null;
}

/**
 * Base production run fields
 */
export interface ProductionRunBase {
  run_number: string;
  started_at: string; // ISO datetime
  completed_at?: string | null;
  duration_hours?: number | null;

  // Slicer estimates - split by type
  estimated_print_time_hours?: number | null;
  estimated_model_weight_grams?: number | null;
  estimated_flushed_grams?: number | null;
  estimated_tower_grams?: number | null;
  estimated_total_weight_grams?: number | null;

  // Actual usage - split by type
  actual_model_weight_grams?: number | null;
  actual_flushed_grams?: number | null;
  actual_tower_grams?: number | null;
  actual_total_weight_grams?: number | null;

  // Waste tracking
  waste_filament_grams?: number | null;
  waste_reason?: string | null;

  // Metadata
  slicer_software?: string | null;
  printer_name?: string | null;
  bed_temperature?: number | null;
  nozzle_temperature?: number | null;

  // Status
  status: ProductionRunStatus;

  // Quality & failure tracking
  quality_rating?: number | null; // 1-5 stars
  quality_notes?: string | null;

  // Reprint tracking
  original_run_id?: string | null;
  is_reprint: boolean;

  // Notes
  notes?: string | null;
}

/**
 * Production run creation payload
 */
export interface ProductionRunCreate extends Partial<ProductionRunBase> {
  started_at: string;
  status?: ProductionRunStatus;
}

/**
 * Production run update payload (all fields optional)
 */
export type ProductionRunUpdate = Partial<ProductionRunBase>

/**
 * Production run response from API
 */
export interface ProductionRun extends ProductionRunBase {
  id: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;

  // Cost analysis (calculated on completion)
  cost_per_gram_actual?: number | null;
  successful_weight_grams?: number | null;

  // Computed fields
  variance_grams?: number | null;
  variance_percentage?: number | null;
  time_variance_hours?: number | null;
  time_variance_percentage?: number | null;

  // Summary field for list display
  items_summary?: string | null;
}

/**
 * Production run with full details (items + materials)
 */
export interface ProductionRunDetail extends ProductionRun {
  items: ProductionRunItem[];
  materials: ProductionRunMaterial[];

  // Computed aggregates
  total_items_planned: number;
  total_items_successful: number;
  total_items_failed: number;
  overall_success_rate?: number | null;
  total_material_cost: number;
  total_estimated_cost: number;
}

/**
 * Paginated list response
 */
export interface ProductionRunListResponse {
  runs: ProductionRun[];
  total: number;
  skip: number;
  limit: number;
}

// Production Run Items

/**
 * Base production run item fields
 */
export interface ProductionRunItemBase {
  model_id: string;
  quantity: number;
  bed_position?: string | null;

  // Estimated costs
  estimated_material_cost?: number | null;
  estimated_component_cost?: number | null;
  estimated_labor_cost?: number | null;
  estimated_total_cost?: number | null;

  // Notes
  notes?: string | null;
}

/**
 * Production run item creation payload
 */
export type ProductionRunItemCreate = ProductionRunItemBase

/**
 * Production run item update payload
 */
export interface ProductionRunItemUpdate extends Partial<ProductionRunItemBase> {
  successful_quantity?: number;
  failed_quantity?: number;
}

/**
 * Production run item response
 */
export interface ProductionRunItem extends ProductionRunItemBase {
  id: string;
  production_run_id: string;
  successful_quantity: number;
  failed_quantity: number;
  created_at: string;
  updated_at: string;

  // Cost analysis (calculated on run completion)
  model_weight_grams?: number | null;
  actual_cost_per_unit?: number | null;

  // Nested model details
  model?: ModelSummary | null;

  // Computed fields
  success_rate?: number | null;
  total_quantity_accounted: number;
  unaccounted_quantity: number;
}

// Production Run Materials

/**
 * Base production run material fields
 */
export interface ProductionRunMaterialBase {
  spool_id: string;
  // Estimated weights - split by type
  estimated_model_weight_grams: number;
  estimated_flushed_grams: number;
  estimated_tower_grams: number;
  cost_per_gram: number;
}

/**
 * Production run material creation payload
 */
export type ProductionRunMaterialCreate = ProductionRunMaterialBase

/**
 * Production run material update payload
 */
export interface ProductionRunMaterialUpdate extends Partial<ProductionRunMaterialBase> {
  spool_weight_before_grams?: number | null;
  spool_weight_after_grams?: number | null;
  // Actual usage - split by type
  actual_model_weight_grams?: number | null;
  actual_flushed_grams?: number | null;
  actual_tower_grams?: number | null;
}

/**
 * Production run material response
 */
export interface ProductionRunMaterial extends ProductionRunMaterialBase {
  id: string;
  production_run_id: string;

  // Spool weighing
  spool_weight_before_grams?: number | null;
  spool_weight_after_grams?: number | null;

  // Actual usage - split by type
  actual_model_weight_grams?: number | null;
  actual_flushed_grams?: number | null;
  actual_tower_grams?: number | null;

  created_at: string;
  updated_at: string;

  // Nested spool details
  spool?: SpoolSummary | null;

  // Computed fields
  estimated_total_weight: number;
  actual_weight_from_weighing?: number | null;
  actual_total_weight: number;
  variance_grams: number;
  variance_percentage: number;
  estimated_cost: number;
  total_cost: number;
}

// Query filters

/**
 * Filters for listing production runs
 */
export interface ProductionRunFilters {
  status_filter?: ProductionRunStatus;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

// UI-specific types

/**
 * Production run form data (for creating/editing)
 */
export interface ProductionRunFormData {
  run_number?: string;
  started_at: Date;
  printer_name?: string;
  slicer_software?: string;
  bed_temperature?: number;
  nozzle_temperature?: number;
  estimated_print_time_hours?: number;
  estimated_total_filament_grams?: number;
  notes?: string;
}

/**
 * Item form data for adding to production run
 */
export interface ProductionRunItemFormData {
  model_id: string;
  quantity: number;
  bed_position?: string;
}

/**
 * Material form data for adding to production run
 */
export interface ProductionRunMaterialFormData {
  spool_id: string;
  estimated_weight_grams: number;
  estimated_purge_grams: number;
}

/**
 * Spool weighing form data
 */
export interface SpoolWeighingFormData {
  material_id: string;
  spool_weight_before_grams: number;
  spool_weight_after_grams: number;
}

/**
 * Production run statistics for dashboard
 */
export interface ProductionRunStats {
  total_runs: number;
  in_progress_runs: number;
  completed_runs: number;
  failed_runs: number;
  total_items_printed: number;
  total_filament_used_grams: number;
  average_variance_percentage: number;
  average_success_rate: number;
}
