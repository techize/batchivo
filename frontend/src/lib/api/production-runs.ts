/**
 * API client functions for Production Runs
 *
 * Provides type-safe API calls for managing production runs,
 * items, and materials.
 */

import { api } from '../api';
import type {
  ProductionRunDetail,
  ProductionRunListResponse,
  ProductionRunCreate,
  ProductionRunUpdate,
  ProductionRunFilters,
  ProductionRunItem,
  ProductionRunItemCreate,
  ProductionRunItemUpdate,
  ProductionRunMaterial,
  ProductionRunMaterialCreate,
  ProductionRunMaterialUpdate,
} from '@/types/production-run';
import type {
  ProductionRunPlate,
  ProductionRunPlateListResponse,
  ProductionRunPlateCreate,
  ProductionRunPlateUpdate,
  PlateFilters,
  MarkPlateCompleteRequest,
} from '@/types/production-run-plate';

const BASE_PATH = '/api/v1/production-runs';

// Production Run CRUD

/**
 * Create a new production run
 */
export async function createProductionRun(
  data: ProductionRunCreate,
  items?: ProductionRunItemCreate[],
  materials?: ProductionRunMaterialCreate[]
): Promise<ProductionRunDetail> {
  const response = await api.post<ProductionRunDetail>(BASE_PATH, {
    ...data,
    items: items || [],
    materials: materials || [],
  });
  return response.data;
}

/**
 * List production runs with optional filters
 */
export async function listProductionRuns(
  filters?: ProductionRunFilters
): Promise<ProductionRunListResponse> {
  const params = new URLSearchParams();

  if (filters?.status_filter) params.append('status_filter', filters.status_filter);
  if (filters?.start_date) params.append('start_date', filters.start_date);
  if (filters?.end_date) params.append('end_date', filters.end_date);
  if (filters?.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters?.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const url = queryString ? `${BASE_PATH}?${queryString}` : BASE_PATH;

  const response = await api.get<ProductionRunListResponse>(url);
  return response.data;
}

/**
 * Get a single production run by ID with full details
 */
export async function getProductionRun(id: string): Promise<ProductionRunDetail> {
  const response = await api.get<ProductionRunDetail>(`${BASE_PATH}/${id}`);
  return response.data;
}

/**
 * Update a production run
 */
export async function updateProductionRun(
  id: string,
  data: ProductionRunUpdate
): Promise<ProductionRunDetail> {
  const response = await api.patch<ProductionRunDetail>(`${BASE_PATH}/${id}`, data);
  return response.data;
}

/**
 * Delete a production run
 */
export async function deleteProductionRun(id: string): Promise<void> {
  await api.delete(`${BASE_PATH}/${id}`);
}

/**
 * Complete a production run (deducts inventory)
 */
export async function completeProductionRun(id: string): Promise<ProductionRunDetail> {
  const response = await api.post<ProductionRunDetail>(`${BASE_PATH}/${id}/complete`);
  return response.data;
}

/**
 * Material usage entry for cancel/fail operations
 */
export interface MaterialUsageEntry {
  spool_id: string;
  grams: number;
}

/**
 * Cancel request options
 */
export interface CancelProductionRunRequest {
  cancel_mode: 'full_reversal' | 'record_partial';
  partial_usage?: MaterialUsageEntry[];
}

/**
 * Failure reason option from API
 */
export interface FailureReasonOption {
  value: string;
  label: string;
  description?: string;
}

/**
 * Fail request options
 */
export interface FailProductionRunRequest {
  failure_reason: string;
  waste_materials: MaterialUsageEntry[];
  notes?: string;
}

/**
 * Cancel a production run
 *
 * @param id - Production run ID
 * @param request - Cancel options (mode and optional partial usage)
 */
export async function cancelProductionRun(
  id: string,
  request: CancelProductionRunRequest
): Promise<ProductionRunDetail> {
  const response = await api.post<ProductionRunDetail>(
    `${BASE_PATH}/${id}/cancel`,
    request
  );
  return response.data;
}

/**
 * Mark a production run as failed with waste tracking
 *
 * @param id - Production run ID
 * @param request - Failure details (reason, waste materials, notes)
 */
export async function failProductionRun(
  id: string,
  request: FailProductionRunRequest
): Promise<ProductionRunDetail> {
  const response = await api.post<ProductionRunDetail>(
    `${BASE_PATH}/${id}/fail`,
    request
  );
  return response.data;
}

/**
 * Get predefined failure reason options
 */
export async function getFailureReasons(): Promise<FailureReasonOption[]> {
  const response = await api.get<FailureReasonOption[]>(`${BASE_PATH}/failure-reasons`);
  return response.data;
}

// Production Run Items

/**
 * Add an item to a production run
 */
export async function addProductionRunItem(
  runId: string,
  data: ProductionRunItemCreate
): Promise<ProductionRunItem> {
  const response = await api.post<ProductionRunItem>(
    `${BASE_PATH}/${runId}/items`,
    data
  );
  return response.data;
}

/**
 * Update a production run item
 */
export async function updateProductionRunItem(
  runId: string,
  itemId: string,
  data: ProductionRunItemUpdate
): Promise<ProductionRunItem> {
  const response = await api.patch<ProductionRunItem>(
    `${BASE_PATH}/${runId}/items/${itemId}`,
    data
  );
  return response.data;
}

/**
 * Delete a production run item
 */
export async function deleteProductionRunItem(
  runId: string,
  itemId: string
): Promise<void> {
  await api.delete(`${BASE_PATH}/${runId}/items/${itemId}`);
}

// Production Run Materials

/**
 * Add a material/spool to a production run
 */
export async function addProductionRunMaterial(
  runId: string,
  data: ProductionRunMaterialCreate
): Promise<ProductionRunMaterial> {
  const response = await api.post<ProductionRunMaterial>(
    `${BASE_PATH}/${runId}/materials`,
    data
  );
  return response.data;
}

/**
 * Update a production run material (e.g., record spool weighing)
 */
export async function updateProductionRunMaterial(
  runId: string,
  materialId: string,
  data: ProductionRunMaterialUpdate
): Promise<ProductionRunMaterial> {
  const response = await api.patch<ProductionRunMaterial>(
    `${BASE_PATH}/${runId}/materials/${materialId}`,
    data
  );
  return response.data;
}

/**
 * Delete a production run material
 */
export async function deleteProductionRunMaterial(
  runId: string,
  materialId: string
): Promise<void> {
  await api.delete(`${BASE_PATH}/${runId}/materials/${materialId}`);
}

// Utility functions

/**
 * Calculate estimated total weight for a production run
 */
export function calculateEstimatedTotalWeight(
  materials: ProductionRunMaterialCreate[]
): number {
  return materials.reduce((total, material) => {
    return total + material.estimated_weight_grams + material.estimated_purge_grams;
  }, 0);
}

/**
 * Calculate estimated total cost for materials
 */
export function calculateEstimatedMaterialCost(
  materials: ProductionRunMaterialCreate[]
): number {
  return materials.reduce((total, material) => {
    const weight = material.estimated_weight_grams + material.estimated_purge_grams;
    return total + weight * material.cost_per_gram;
  }, 0);
}

/**
 * Format run number for display
 */
export function formatRunNumber(runNumber: string): string {
  return runNumber;
}

/**
 * Get status badge color
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'in_progress':
      return 'blue';
    case 'completed':
      return 'green';
    case 'failed':
      return 'red';
    case 'cancelled':
      return 'gray';
    default:
      return 'gray';
  }
}

/**
 * Format status for display
 */
export function formatStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format duration in hours to human-readable string
 */
export function formatDuration(hours: number): string {
  if (hours < 1) {
    const minutes = Math.round(hours * 60);
    return `${minutes}m`;
  }

  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);

  if (minutes === 0) {
    return `${wholeHours}h`;
  }

  return `${wholeHours}h ${minutes}m`;
}

/**
 * Check if production run can be completed
 */
export function canCompleteRun(run: ProductionRunDetail): {
  canComplete: boolean;
  reason?: string;
} {
  if (run.status === 'completed') {
    return { canComplete: false, reason: 'Run is already completed' };
  }

  if (run.status === 'cancelled') {
    return { canComplete: false, reason: 'Run is cancelled' };
  }

  if (run.materials.length === 0) {
    return { canComplete: false, reason: 'No materials added to run' };
  }

  // Check if all materials have actual usage recorded
  // Note: actual_model_weight_grams or actual_weight_from_weighing must be set
  const missingUsage = run.materials.some(
    (material) => material.actual_model_weight_grams == null && material.actual_weight_from_weighing == null
  );

  if (missingUsage) {
    return {
      canComplete: false,
      reason: 'Some materials do not have actual usage recorded',
    };
  }

  return { canComplete: true };
}

// Production Run Plates

/**
 * Create a new plate within a production run
 */
export async function createProductionRunPlate(
  runId: string,
  data: ProductionRunPlateCreate
): Promise<ProductionRunPlate> {
  const response = await api.post<ProductionRunPlate>(
    `${BASE_PATH}/${runId}/plates`,
    data
  );
  return response.data;
}

/**
 * List plates for a production run with optional filters
 */
export async function listProductionRunPlates(
  runId: string,
  filters?: PlateFilters
): Promise<ProductionRunPlateListResponse> {
  const params = new URLSearchParams();

  if (filters?.status) params.append('status_filter', filters.status);
  if (filters?.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters?.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const url = queryString
    ? `${BASE_PATH}/${runId}/plates?${queryString}`
    : `${BASE_PATH}/${runId}/plates`;

  const response = await api.get<ProductionRunPlateListResponse>(url);
  return response.data;
}

/**
 * Get a single plate by ID
 */
export async function getProductionRunPlate(
  runId: string,
  plateId: string
): Promise<ProductionRunPlate> {
  const response = await api.get<ProductionRunPlate>(
    `${BASE_PATH}/${runId}/plates/${plateId}`
  );
  return response.data;
}

/**
 * Update a production run plate
 */
export async function updateProductionRunPlate(
  runId: string,
  plateId: string,
  data: ProductionRunPlateUpdate
): Promise<ProductionRunPlate> {
  const response = await api.patch<ProductionRunPlate>(
    `${BASE_PATH}/${runId}/plates/${plateId}`,
    data
  );
  return response.data;
}

/**
 * Start printing a plate (transition from pending to printing)
 */
export async function startProductionRunPlate(
  runId: string,
  plateId: string
): Promise<ProductionRunPlate> {
  const response = await api.post<ProductionRunPlate>(
    `${BASE_PATH}/${runId}/plates/${plateId}/start`
  );
  return response.data;
}

/**
 * Mark a plate as complete with results
 */
export async function completeProductionRunPlate(
  runId: string,
  plateId: string,
  data: MarkPlateCompleteRequest
): Promise<ProductionRunPlate> {
  const response = await api.post<ProductionRunPlate>(
    `${BASE_PATH}/${runId}/plates/${plateId}/complete`,
    data
  );
  return response.data;
}

/**
 * Mark a plate as failed
 */
export async function failProductionRunPlate(
  runId: string,
  plateId: string,
  notes?: string
): Promise<ProductionRunPlate> {
  const url = notes
    ? `${BASE_PATH}/${runId}/plates/${plateId}/fail?notes=${encodeURIComponent(notes)}`
    : `${BASE_PATH}/${runId}/plates/${plateId}/fail`;
  const response = await api.post<ProductionRunPlate>(url);
  return response.data;
}

/**
 * Cancel a plate
 */
export async function cancelProductionRunPlate(
  runId: string,
  plateId: string,
  notes?: string
): Promise<ProductionRunPlate> {
  const url = notes
    ? `${BASE_PATH}/${runId}/plates/${plateId}/cancel?notes=${encodeURIComponent(notes)}`
    : `${BASE_PATH}/${runId}/plates/${plateId}/cancel`;
  const response = await api.post<ProductionRunPlate>(url);
  return response.data;
}

/**
 * Delete a plate from a production run
 */
export async function deleteProductionRunPlate(
  runId: string,
  plateId: string
): Promise<void> {
  await api.delete(`${BASE_PATH}/${runId}/plates/${plateId}`);
}

/**
 * Get plate status badge color
 */
export function getPlateStatusColor(status: string): string {
  switch (status) {
    case 'pending':
      return 'gray';
    case 'printing':
      return 'blue';
    case 'complete':
      return 'green';
    case 'failed':
      return 'red';
    case 'cancelled':
      return 'gray';
    default:
      return 'gray';
  }
}

/**
 * Format plate status for display
 */
export function formatPlateStatus(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}
