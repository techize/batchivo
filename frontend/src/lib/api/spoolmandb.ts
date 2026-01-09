import { apiClient } from '../api'
import type {
  SpoolmanDBManufacturerListResponse,
  SpoolmanDBFilament,
  SpoolmanDBFilamentListResponse,
  SpoolmanDBFilamentListParams,
  SpoolmanDBStats,
  SpoolmanDBSyncResponse,
} from '@/types/spoolmandb'

/**
 * SpoolmanDB API Client
 * Community filament database operations
 */
export const spoolmandbApi = {
  /**
   * Get database statistics
   */
  getStats: async (): Promise<SpoolmanDBStats> => {
    return apiClient.get<SpoolmanDBStats>('/api/v1/spoolmandb/stats')
  },

  /**
   * Trigger database sync from SpoolmanDB
   */
  sync: async (): Promise<SpoolmanDBSyncResponse> => {
    return apiClient.post<SpoolmanDBSyncResponse>('/api/v1/spoolmandb/sync')
  },

  /**
   * List manufacturers with optional search
   */
  listManufacturers: async (search?: string): Promise<SpoolmanDBManufacturerListResponse> => {
    const queryParams = new URLSearchParams()
    if (search) queryParams.append('search', search)
    const queryString = queryParams.toString()
    const url = `/api/v1/spoolmandb/manufacturers${queryString ? `?${queryString}` : ''}`
    return apiClient.get<SpoolmanDBManufacturerListResponse>(url)
  },

  /**
   * List filaments with filtering
   */
  listFilaments: async (params?: SpoolmanDBFilamentListParams): Promise<SpoolmanDBFilamentListResponse> => {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.manufacturer_id) queryParams.append('manufacturer_id', params.manufacturer_id)
    if (params?.manufacturer_name) queryParams.append('manufacturer_name', params.manufacturer_name)
    if (params?.material) queryParams.append('material', params.material)
    if (params?.search) queryParams.append('search', params.search)
    if (params?.diameter) queryParams.append('diameter', params.diameter.toString())

    const queryString = queryParams.toString()
    const url = `/api/v1/spoolmandb/filaments${queryString ? `?${queryString}` : ''}`
    return apiClient.get<SpoolmanDBFilamentListResponse>(url)
  },

  /**
   * Get a single filament by ID
   */
  getFilament: async (id: string): Promise<SpoolmanDBFilament> => {
    return apiClient.get<SpoolmanDBFilament>(`/api/v1/spoolmandb/filaments/${id}`)
  },

  /**
   * Get list of unique materials
   */
  listMaterials: async (): Promise<{ materials: { material: string; count: number }[]; total: number }> => {
    return apiClient.get('/api/v1/spoolmandb/materials')
  },
}
