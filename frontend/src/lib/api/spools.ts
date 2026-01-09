import { apiClient } from '../api'
import type {
  SpoolResponse,
  SpoolListResponse,
  SpoolCreate,
  SpoolUpdate,
  SpoolListParams,
  MaterialType,
} from '@/types/spool'

/**
 * Spools API Client
 * Handles all spool inventory API operations
 */
export const spoolsApi = {
  /**
   * List spools with optional filtering and pagination
   */
  list: async (params?: SpoolListParams): Promise<SpoolListResponse> => {
    const queryParams = new URLSearchParams()

    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.search) queryParams.append('search', params.search)
    if (params?.material_type_id) queryParams.append('material_type_id', params.material_type_id)
    if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString())
    if (params?.low_stock_only) queryParams.append('low_stock_only', params.low_stock_only.toString())

    const queryString = queryParams.toString()
    const url = `/api/v1/spools${queryString ? `?${queryString}` : ''}`

    return apiClient.get<SpoolListResponse>(url)
  },

  /**
   * Get a single spool by ID
   */
  get: async (id: string): Promise<SpoolResponse> => {
    return apiClient.get<SpoolResponse>(`/api/v1/spools/${id}`)
  },

  /**
   * Create a new spool
   */
  create: async (data: SpoolCreate): Promise<SpoolResponse> => {
    return apiClient.post<SpoolResponse>('/api/v1/spools', data)
  },

  /**
   * Update an existing spool
   */
  update: async (id: string, data: SpoolUpdate): Promise<SpoolResponse> => {
    return apiClient.put<SpoolResponse>(`/api/v1/spools/${id}`, data)
  },

  /**
   * Delete a spool
   */
  delete: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/spools/${id}`)
  },

  /**
   * Duplicate a spool
   * Creates a copy with new spool_id, returns the new spool for editing
   */
  duplicate: async (id: string): Promise<SpoolResponse> => {
    return apiClient.post<SpoolResponse>(`/api/v1/spools/${id}/duplicate`)
  },

  /**
   * Update spool weight only
   * Convenience method for quick weight updates
   */
  updateWeight: async (id: string, current_weight: number): Promise<SpoolResponse> => {
    return apiClient.put<SpoolResponse>(`/api/v1/spools/${id}`, { current_weight })
  },
}

/**
 * Material Types API Client
 * Reference data for filament material types
 */
export const materialTypesApi = {
  /**
   * List all available material types
   */
  list: async (): Promise<MaterialType[]> => {
    return apiClient.get<MaterialType[]>('/api/v1/spools/material-types')
  },
}
