/**
 * TypeScript types for Production Run Plate system
 *
 * Mirrors the backend Pydantic schemas for type safety
 */

import type { ModelSummary } from './production-run';
import type { PrinterSummary } from './printer';

export type PlateStatus = 'pending' | 'printing' | 'complete' | 'failed' | 'cancelled';

/**
 * Base production run plate fields
 */
export interface ProductionRunPlateBase {
  model_id: string;
  printer_id: string;
  plate_number: number;
  plate_name: string;
  quantity?: number;
  prints_per_plate: number;
  print_time_minutes?: number | null;
  estimated_material_weight_grams?: number | null;
  notes?: string | null;
}

/**
 * Production run plate creation payload
 */
export type ProductionRunPlateCreate = ProductionRunPlateBase

/**
 * Production run plate update payload (all fields optional)
 */
export interface ProductionRunPlateUpdate {
  notes?: string | null;
  successful_prints?: number;
  failed_prints?: number;
  actual_print_time_minutes?: number | null;
  actual_material_weight_grams?: number | null;
}

/**
 * Production run plate response from API
 */
export interface ProductionRunPlate extends ProductionRunPlateBase {
  id: string;
  production_run_id: string;
  status: PlateStatus;
  started_at?: string | null;
  completed_at?: string | null;
  actual_print_time_minutes?: number | null;
  actual_material_weight_grams?: number | null;
  successful_prints: number;
  failed_prints: number;
  created_at: string;
  updated_at: string;

  // Cost analysis (calculated on run completion)
  model_weight_grams?: number | null;
  actual_cost_per_unit?: number | null;

  // Nested model and printer details
  model?: ModelSummary | null;
  printer?: PrinterSummary | null;

  // Computed fields
  total_prints_expected: number;
  completion_percentage: number;
}

/**
 * Paginated list response for plates
 */
export interface ProductionRunPlateListResponse {
  plates: ProductionRunPlate[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Filters for listing plates
 */
export interface PlateFilters {
  status?: PlateStatus;
  skip?: number;
  limit?: number;
}

/**
 * Request payload for marking a plate as complete
 */
export interface MarkPlateCompleteRequest {
  successful_prints: number;
  failed_prints?: number;
  actual_print_time_minutes?: number;
  actual_material_weight_grams?: number;
  notes?: string;
}

/**
 * Plate form data for UI
 */
export interface PlateFormData {
  model_id: string;
  printer_id: string;
  plate_number: number;
  plate_name: string;
  prints_per_plate: number;
  print_time_minutes?: number;
  notes?: string;
}
