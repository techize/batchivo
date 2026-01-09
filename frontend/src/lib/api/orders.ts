/**
 * Orders API client
 *
 * Provides TypeScript functions for interacting with the orders API endpoints.
 * Orders represent customer purchases from sales channels.
 */

import { apiClient } from '../api'

// ==================== Types ====================

/**
 * Order item
 */
export interface OrderItem {
  id: string
  product_id: string | null
  product_sku: string
  product_name: string
  quantity: number
  unit_price: number
  total_price: number
}

/**
 * Order
 */
export interface Order {
  id: string
  order_number: string
  status: string
  customer_email: string
  customer_name: string
  customer_phone: string | null
  shipping_address_line1: string
  shipping_address_line2: string | null
  shipping_city: string
  shipping_county: string | null
  shipping_postcode: string
  shipping_country: string
  shipping_method: string
  shipping_cost: number
  subtotal: number
  total: number
  currency: string
  payment_provider: string
  payment_id: string | null
  payment_status: string
  tracking_number: string | null
  tracking_url: string | null
  shipped_at: string | null
  delivered_at: string | null
  fulfilled_at: string | null
  customer_notes: string | null
  internal_notes: string | null
  created_at: string
  updated_at: string
  items: OrderItem[]
}

/**
 * Order list response
 */
export interface OrderListResponse {
  data: Order[]
  total: number
  page: number
  limit: number
  has_more: boolean
}

/**
 * Update order request
 */
export interface UpdateOrderRequest {
  status?: string
  tracking_number?: string
  tracking_url?: string
  internal_notes?: string
}

/**
 * Ship order request
 */
export interface ShipOrderRequest {
  tracking_number?: string
  tracking_url?: string
}

/**
 * Cancel order request
 */
export interface CancelOrderRequest {
  reason?: string
}

/**
 * Fulfill order response
 */
export interface FulfillOrderResponse {
  message: string
  low_stock_alerts: {
    product_id: string
    product_sku: string
    product_name: string
    current_stock: number
    threshold: number
  }[]
}

/**
 * Order counts by status
 */
export interface OrderCounts {
  pending: number
  processing: number
  shipped: number
  delivered: number
  cancelled: number
  refunded: number
  total: number
}

// ==================== API Functions ====================

/**
 * Get all orders with pagination and filtering
 */
export async function getOrders(params?: {
  status?: string
  search?: string
  date_from?: string
  date_to?: string
  page?: number
  limit?: number
}): Promise<OrderListResponse> {
  const queryParams = new URLSearchParams()
  if (params?.status) queryParams.append('status', params.status)
  if (params?.search) queryParams.append('search', params.search)
  if (params?.date_from) queryParams.append('date_from', params.date_from)
  if (params?.date_to) queryParams.append('date_to', params.date_to)
  if (params?.page) queryParams.append('page', params.page.toString())
  if (params?.limit) queryParams.append('limit', params.limit.toString())

  const query = queryParams.toString()
  return apiClient.get<OrderListResponse>(`/api/v1/orders${query ? `?${query}` : ''}`)
}

/**
 * Get order counts by status
 */
export async function getOrderCounts(): Promise<OrderCounts> {
  return apiClient.get<OrderCounts>('/api/v1/orders/counts')
}

/**
 * Get a single order by ID
 */
export async function getOrder(id: string): Promise<Order> {
  return apiClient.get<Order>(`/api/v1/orders/${id}`)
}

/**
 * Update an order
 */
export async function updateOrder(id: string, data: UpdateOrderRequest): Promise<Order> {
  return apiClient.patch<Order>(`/api/v1/orders/${id}`, data)
}

/**
 * Ship an order
 */
export async function shipOrder(id: string, data: ShipOrderRequest): Promise<{ message: string }> {
  return apiClient.post<{ message: string }>(`/api/v1/orders/${id}/ship`, data)
}

/**
 * Mark order as delivered
 */
export async function deliverOrder(id: string): Promise<{ message: string }> {
  return apiClient.post<{ message: string }>(`/api/v1/orders/${id}/deliver`)
}

/**
 * Fulfill an order (deduct inventory)
 */
export async function fulfillOrder(id: string): Promise<FulfillOrderResponse> {
  return apiClient.post<FulfillOrderResponse>(`/api/v1/orders/${id}/fulfill`)
}

/**
 * Cancel an order
 */
export async function cancelOrder(id: string, data: CancelOrderRequest): Promise<{ message: string }> {
  return apiClient.post<{ message: string }>(`/api/v1/orders/${id}/cancel`, data)
}
