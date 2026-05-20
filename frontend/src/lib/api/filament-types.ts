import { apiClient } from '../api'
import type {
  FilamentTypeAggregatedListResponse,
  FilamentTypeListParams,
  FilamentTypeListItem,
  SpoolInSheet,
  FilamentTypeUpdate,
  BulkCreateRequest,
  BulkCreateResponse,
  BatchCreateRequest,
  BatchCreateResponse,
} from '@/types/filament-type'

/**
 * Filament Types API Client
 * Handles aggregated filament type list and per-type spool operations.
 */
export const filamentTypesApi = {
  /**
   * List aggregated filament types with optional filtering and pagination.
   * Calls GET /api/v1/filament-types/aggregated
   */
  list: async (params?: FilamentTypeListParams): Promise<FilamentTypeAggregatedListResponse> => {
    const queryParams = new URLSearchParams()

    if (params?.page !== undefined) queryParams.append('page', String(params.page))
    if (params?.page_size !== undefined) queryParams.append('page_size', String(params.page_size))
    if (params?.brand) queryParams.append('brand', params.brand)
    if (params?.color) queryParams.append('color', params.color)
    if (params?.material_type_id) queryParams.append('material_type_id', params.material_type_id)
    if (params?.needs_labels !== undefined) queryParams.append('needs_labels', String(params.needs_labels))
    if (params?.needs_sample !== undefined) queryParams.append('needs_sample', String(params.needs_sample))

    const queryString = queryParams.toString()
    const url = `/api/v1/filament-types/aggregated${queryString ? `?${queryString}` : ''}`

    return apiClient.get<FilamentTypeAggregatedListResponse>(url)
  },

  /**
   * Get all spools belonging to a specific filament type.
   * Calls GET /api/v1/filament-types/{filamentTypeId}/spools
   */
  getSpools: async (filamentTypeId: string): Promise<SpoolInSheet[]> => {
    return apiClient.get<SpoolInSheet[]>(`/api/v1/filament-types/${filamentTypeId}/spools`)
  },

  /**
   * Update a filament type record (partial update).
   * Calls PUT /api/v1/filament-types/{id}
   */
  update: async (id: string, data: FilamentTypeUpdate): Promise<FilamentTypeListItem> => {
    return apiClient.put<FilamentTypeListItem>(`/api/v1/filament-types/${id}`, data)
  },

  bulkCreate: async (data: BulkCreateRequest): Promise<BulkCreateResponse> => {
    // Strip '#' from color_hex if present before sending to backend
    const payload = { ...data, color_hex: data.color_hex?.replace(/^#/, '') ?? data.color_hex }
    return apiClient.post<BulkCreateResponse>('/api/v1/filament-types/bulk-create', payload)
  },
  batchCreate: async (data: BatchCreateRequest): Promise<BatchCreateResponse> => {
    // Strip '#' from color_hex in each entry
    const payload = {
      ...data,
      entries: data.entries.map(e => ({ ...e, color_hex: e.color_hex?.replace(/^#/, '') ?? e.color_hex })),
    }
    return apiClient.post<BatchCreateResponse>('/api/v1/filament-types/batch-create', payload)
  },
}
