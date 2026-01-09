/**
 * API client functions for Printers
 *
 * Provides type-safe API calls for managing printers.
 */

import { api } from '../api';
import type {
  Printer,
  PrinterListResponse,
  PrinterCreate,
  PrinterUpdate,
  PrinterFilters,
} from '@/types/printer';

const BASE_PATH = '/api/v1/printers';

/**
 * Create a new printer
 */
export async function createPrinter(data: PrinterCreate): Promise<Printer> {
  const response = await api.post<Printer>(BASE_PATH, data);
  return response.data;
}

/**
 * List printers with optional filters
 */
export async function listPrinters(
  filters?: PrinterFilters
): Promise<PrinterListResponse> {
  const params = new URLSearchParams();

  if (filters?.is_active !== undefined)
    params.append('is_active', filters.is_active.toString());
  if (filters?.skip !== undefined) params.append('skip', filters.skip.toString());
  if (filters?.limit !== undefined) params.append('limit', filters.limit.toString());

  const queryString = params.toString();
  const url = queryString ? `${BASE_PATH}?${queryString}` : BASE_PATH;

  const response = await api.get<PrinterListResponse>(url);
  return response.data;
}

/**
 * Get a single printer by ID
 */
export async function getPrinter(id: string): Promise<Printer> {
  const response = await api.get<Printer>(`${BASE_PATH}/${id}`);
  return response.data;
}

/**
 * Update a printer
 */
export async function updatePrinter(
  id: string,
  data: PrinterUpdate
): Promise<Printer> {
  const response = await api.put<Printer>(`${BASE_PATH}/${id}`, data);
  return response.data;
}

/**
 * Delete a printer (soft delete)
 */
export async function deletePrinter(id: string): Promise<void> {
  await api.delete(`${BASE_PATH}/${id}`);
}

/**
 * Get active printers only (for dropdowns)
 */
export async function getActivePrinters(): Promise<Printer[]> {
  const response = await listPrinters({ is_active: true, limit: 1000 });
  return response.printers;
}
