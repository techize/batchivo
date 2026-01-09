/**
 * Sales Channels API client
 *
 * Provides TypeScript functions for interacting with the sales channels API endpoints.
 */

import { apiClient } from '../api'

// ==================== Types ====================

export type PlatformType = 'fair' | 'online_shop' | 'shopify' | 'ebay' | 'etsy' | 'amazon' | 'other'

export interface SalesChannel {
  id: string
  tenant_id: string
  name: string
  platform_type: PlatformType
  fee_percentage: string
  fee_fixed: string
  monthly_cost: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SalesChannelListResponse {
  channels: SalesChannel[]
  total: number
}

export interface SalesChannelCreateRequest {
  name: string
  platform_type: PlatformType
  fee_percentage?: string
  fee_fixed?: string
  monthly_cost?: string
  is_active?: boolean
}

export interface SalesChannelUpdateRequest {
  name?: string
  platform_type?: PlatformType
  fee_percentage?: string
  fee_fixed?: string
  monthly_cost?: string
  is_active?: boolean
}

export interface SalesChannelListParams {
  skip?: number
  limit?: number
  search?: string
  platform_type?: PlatformType
  is_active?: boolean
}

// ==================== API Functions ====================

/**
 * List all sales channels with pagination and filtering
 */
export async function listSalesChannels(params?: SalesChannelListParams): Promise<SalesChannelListResponse> {
  const queryParams = new URLSearchParams()

  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString())
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString())
  if (params?.search) queryParams.append('search', params.search)
  if (params?.platform_type) queryParams.append('platform_type', params.platform_type)
  if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString())

  const url = `/api/v1/sales-channels${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
  return apiClient.get<SalesChannelListResponse>(url)
}

/**
 * Get a single sales channel by ID
 */
export async function getSalesChannel(channelId: string): Promise<SalesChannel> {
  return apiClient.get<SalesChannel>(`/api/v1/sales-channels/${channelId}`)
}

/**
 * Create a new sales channel
 */
export async function createSalesChannel(data: SalesChannelCreateRequest): Promise<SalesChannel> {
  return apiClient.post<SalesChannel>('/api/v1/sales-channels', data)
}

/**
 * Update an existing sales channel
 */
export async function updateSalesChannel(channelId: string, data: SalesChannelUpdateRequest): Promise<SalesChannel> {
  return apiClient.put<SalesChannel>(`/api/v1/sales-channels/${channelId}`, data)
}

/**
 * Delete a sales channel
 * @param channelId - The channel ID to delete
 * @param permanent - If true, permanently removes from database. If false (default), soft deletes by setting is_active=false
 */
export async function deleteSalesChannel(channelId: string, permanent = false): Promise<void> {
  const url = permanent
    ? `/api/v1/sales-channels/${channelId}?permanent=true`
    : `/api/v1/sales-channels/${channelId}`
  return apiClient.delete(url)
}

// ==================== Helpers ====================

/**
 * Get platform display name
 */
export function getPlatformDisplayName(platformType: PlatformType): string {
  const names: Record<PlatformType, string> = {
    fair: 'Fair/Market',
    online_shop: 'Online Shop',
    shopify: 'Shopify',
    ebay: 'eBay',
    etsy: 'Etsy',
    amazon: 'Amazon',
    other: 'Other',
  }
  return names[platformType] || platformType
}

/**
 * Get platform color for badges
 */
export function getPlatformColor(platformType: PlatformType): string {
  const colors: Record<PlatformType, string> = {
    fair: 'bg-purple-500/10 text-purple-600 border-purple-200',
    online_shop: 'bg-blue-500/10 text-blue-600 border-blue-200',
    shopify: 'bg-green-500/10 text-green-600 border-green-200',
    ebay: 'bg-yellow-500/10 text-yellow-700 border-yellow-200',
    etsy: 'bg-orange-500/10 text-orange-600 border-orange-200',
    amazon: 'bg-amber-500/10 text-amber-700 border-amber-200',
    other: 'bg-gray-500/10 text-gray-600 border-gray-200',
  }
  return colors[platformType] || colors.other
}
