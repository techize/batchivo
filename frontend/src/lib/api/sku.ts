import { apiClient } from '../api'
import type { NextSKUResponse, SKUAvailabilityResponse, SKUEntityType } from '@/types/sku'

/**
 * SKU API Client
 * Handles SKU generation and availability checking
 */
export const skuApi = {
  /**
   * Get the next available SKU for an entity type
   * @param entityType - PROD, MOD, COM, or FIL
   */
  getNextSKU: async (entityType: SKUEntityType): Promise<NextSKUResponse> => {
    return apiClient.get<NextSKUResponse>(`/api/v1/sku/next/${entityType}`)
  },

  /**
   * Check if a specific SKU is available for use
   * @param entityType - PROD, MOD, COM, or FIL
   * @param sku - The SKU to check
   */
  checkAvailability: async (entityType: SKUEntityType, sku: string): Promise<SKUAvailabilityResponse> => {
    return apiClient.get<SKUAvailabilityResponse>(`/api/v1/sku/check/${entityType}/${encodeURIComponent(sku)}`)
  },
}
