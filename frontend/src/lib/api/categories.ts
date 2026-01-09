/**
 * Categories API client
 *
 * Provides TypeScript functions for interacting with the categories API endpoints.
 * Categories are used to organize products in the shop.
 */

import { apiClient } from '../api'

// ==================== Types ====================

export interface Category {
  id: string
  tenant_id: string
  name: string
  slug: string
  description?: string
  image_url?: string
  parent_id?: string
  display_order: number
  is_active: boolean
  product_count?: number
  created_at: string
  updated_at: string
}

export interface CategoryListResponse {
  categories: Category[]
  total: number
}

export interface CategoryCreateRequest {
  name: string
  slug?: string
  description?: string
  image_url?: string
  parent_id?: string
  display_order?: number
  is_active?: boolean
}

export interface CategoryUpdateRequest {
  name?: string
  slug?: string
  description?: string
  image_url?: string | null
  parent_id?: string | null
  display_order?: number
  is_active?: boolean
}

export interface CategoryListParams {
  skip?: number
  limit?: number
  search?: string
  parent_id?: string | null
  is_active?: boolean
}

// ==================== API Functions ====================

/**
 * List all categories with pagination and filtering
 */
export async function listCategories(params?: CategoryListParams): Promise<CategoryListResponse> {
  const queryParams = new URLSearchParams()

  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString())
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString())
  if (params?.search) queryParams.append('search', params.search)
  if (params?.parent_id !== undefined) {
    queryParams.append('parent_id', params.parent_id === null ? 'null' : params.parent_id)
  }
  if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString())

  const url = `/api/v1/categories${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
  return apiClient.get<CategoryListResponse>(url)
}

/**
 * Get a single category by ID
 */
export async function getCategory(categoryId: string): Promise<Category> {
  return apiClient.get<Category>(`/api/v1/categories/${categoryId}`)
}

/**
 * Create a new category
 */
export async function createCategory(data: CategoryCreateRequest): Promise<Category> {
  return apiClient.post<Category>('/api/v1/categories', data)
}

/**
 * Update an existing category
 */
export async function updateCategory(categoryId: string, data: CategoryUpdateRequest): Promise<Category> {
  return apiClient.patch<Category>(`/api/v1/categories/${categoryId}`, data)
}

/**
 * Delete a category
 */
export async function deleteCategory(categoryId: string): Promise<void> {
  return apiClient.delete(`/api/v1/categories/${categoryId}`)
}

/**
 * Reorder categories (bulk update display_order)
 */
export async function reorderCategories(categoryOrders: { id: string; display_order: number }[]): Promise<void> {
  // Update each category's display_order
  await Promise.all(
    categoryOrders.map(({ id, display_order }) =>
      updateCategory(id, { display_order })
    )
  )
}

// ==================== Product-Category Assignment ====================

/**
 * Assign a product to a category
 */
export async function assignProductToCategory(categoryId: string, productId: string): Promise<void> {
  return apiClient.post(`/api/v1/categories/${categoryId}/products/${productId}`, {})
}

/**
 * Remove a product from a category
 */
export async function removeProductFromCategory(categoryId: string, productId: string): Promise<void> {
  return apiClient.delete(`/api/v1/categories/${categoryId}/products/${productId}`)
}
