/**
 * TypeScript types for Printer system
 *
 * Mirrors the backend Pydantic schemas for type safety
 */

/**
 * Base printer fields
 */
export interface PrinterBase {
  name: string;
  manufacturer?: string | null;
  model?: string | null;
  serial_number?: string | null;
  bed_size_x_mm?: number | null;
  bed_size_y_mm?: number | null;
  bed_size_z_mm?: number | null;
  nozzle_diameter_mm?: number | null;
  default_bed_temp?: number | null;
  default_nozzle_temp?: number | null;
  capabilities?: Record<string, unknown> | null;
  notes?: string | null;
  is_active?: boolean;
}

/**
 * Printer creation payload
 */
export type PrinterCreate = PrinterBase

/**
 * Printer update payload (all fields optional)
 */
export type PrinterUpdate = Partial<PrinterBase>

/**
 * Printer response from API
 */
export interface Printer extends PrinterBase {
  id: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

/**
 * Paginated list response for printers
 */
export interface PrinterListResponse {
  printers: Printer[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Filters for listing printers
 */
export interface PrinterFilters {
  is_active?: boolean;
  skip?: number;
  limit?: number;
}

/**
 * Printer summary for embedding in other responses
 */
export interface PrinterSummary {
  id: string;
  name: string;
  manufacturer?: string | null;
  model?: string | null;
}
