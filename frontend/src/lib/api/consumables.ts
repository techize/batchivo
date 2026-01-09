import { apiClient } from '../api'
import type {
  ConsumableTypeResponse,
  ConsumableTypeListResponse,
  ConsumableTypeCreate,
  ConsumableTypeUpdate,
  ConsumableTypeListParams,
  ConsumablePurchaseResponse,
  ConsumablePurchaseListResponse,
  ConsumablePurchaseCreate,
  ConsumablePurchaseListParams,
  ConsumableUsageCreate,
  ConsumableUsageResponse,
  StockAdjustment,
  LowStockAlert,
} from '@/types/consumable'

/**
 * Consumables API Client
 * Handles all consumable inventory API operations
 */
export const consumablesApi = {
  // =============================================================================
  // ConsumableType CRUD
  // =============================================================================

  /**
   * List consumable types with optional filtering and pagination
   */
  list: async (params?: ConsumableTypeListParams): Promise<ConsumableTypeListResponse> => {
    const queryParams = new URLSearchParams()

    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.search) queryParams.append('search', params.search)
    if (params?.category) queryParams.append('category', params.category)
    if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString())
    if (params?.low_stock_only) queryParams.append('low_stock_only', params.low_stock_only.toString())

    const queryString = queryParams.toString()
    const url = `/api/v1/consumables/types${queryString ? `?${queryString}` : ''}`

    return apiClient.get<ConsumableTypeListResponse>(url)
  },

  /**
   * Get a single consumable type by ID
   */
  get: async (id: string): Promise<ConsumableTypeResponse> => {
    return apiClient.get<ConsumableTypeResponse>(`/api/v1/consumables/types/${id}`)
  },

  /**
   * Create a new consumable type
   */
  create: async (data: ConsumableTypeCreate): Promise<ConsumableTypeResponse> => {
    return apiClient.post<ConsumableTypeResponse>('/api/v1/consumables/types', data)
  },

  /**
   * Update an existing consumable type
   */
  update: async (id: string, data: ConsumableTypeUpdate): Promise<ConsumableTypeResponse> => {
    return apiClient.put<ConsumableTypeResponse>(`/api/v1/consumables/types/${id}`, data)
  },

  /**
   * Delete a consumable type
   */
  delete: async (id: string): Promise<void> => {
    return apiClient.delete<void>(`/api/v1/consumables/types/${id}`)
  },

  /**
   * Adjust stock level for a consumable
   */
  adjustStock: async (id: string, data: StockAdjustment): Promise<ConsumableTypeResponse> => {
    return apiClient.post<ConsumableTypeResponse>(`/api/v1/consumables/types/${id}/adjust-stock`, data)
  },

  /**
   * Get low stock alerts
   */
  getLowStockAlerts: async (): Promise<LowStockAlert[]> => {
    return apiClient.get<LowStockAlert[]>('/api/v1/consumables/alerts/low-stock')
  },

  /**
   * Get available categories
   */
  getCategories: async (): Promise<string[]> => {
    return apiClient.get<string[]>('/api/v1/consumables/categories')
  },

  // =============================================================================
  // ConsumablePurchase CRUD
  // =============================================================================

  /**
   * List purchases with optional filtering and pagination
   */
  listPurchases: async (params?: ConsumablePurchaseListParams): Promise<ConsumablePurchaseListResponse> => {
    const queryParams = new URLSearchParams()

    if (params?.page) queryParams.append('page', params.page.toString())
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString())
    if (params?.consumable_type_id) queryParams.append('consumable_type_id', params.consumable_type_id)

    const queryString = queryParams.toString()
    const url = `/api/v1/consumables/purchases${queryString ? `?${queryString}` : ''}`

    return apiClient.get<ConsumablePurchaseListResponse>(url)
  },

  /**
   * Create a new purchase (automatically updates stock)
   */
  createPurchase: async (data: ConsumablePurchaseCreate): Promise<ConsumablePurchaseResponse> => {
    return apiClient.post<ConsumablePurchaseResponse>('/api/v1/consumables/purchases', data)
  },

  // =============================================================================
  // ConsumableUsage
  // =============================================================================

  /**
   * Record consumable usage
   */
  recordUsage: async (data: ConsumableUsageCreate): Promise<ConsumableUsageResponse> => {
    return apiClient.post<ConsumableUsageResponse>('/api/v1/consumables/usage', data)
  },
}
