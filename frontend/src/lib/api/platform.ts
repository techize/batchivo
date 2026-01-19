/**
 * Platform Admin API client
 *
 * Provides TypeScript functions for interacting with the platform admin API endpoints.
 * These endpoints are only accessible to platform administrators.
 */

import { apiClient } from '../api'

// ==================== Types ====================

/**
 * Tenant response from list
 */
export interface Tenant {
  id: string
  name: string
  slug: string
  tenant_type: string
  is_active: boolean
  created_at: string
  settings: Record<string, unknown> | null
}

/**
 * Tenant detail with statistics
 */
export interface TenantDetail extends Tenant {
  user_count: number
  product_count: number
  order_count: number
  total_revenue: number
}

/**
 * Paginated tenants response
 */
export interface PaginatedTenantsResponse {
  items: Tenant[]
  total: number
  skip: number
  limit: number
}

/**
 * Platform user
 */
export interface PlatformUser {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_platform_admin: boolean
  created_at: string
}

/**
 * Paginated users response
 */
export interface PaginatedUsersResponse {
  items: PlatformUser[]
  total: number
  skip: number
  limit: number
}

/**
 * Impersonation response
 */
export interface ImpersonationResponse {
  access_token: string
  token_type: string
  tenant_id: string
  tenant_name: string
}

/**
 * Tenant action response
 */
export interface TenantActionResponse {
  id: string
  name: string
  is_active: boolean
  message: string
}

/**
 * Audit log entry
 */
export interface AuditLog {
  id: string
  admin_user_id: string
  action: string
  target_type: string | null
  target_id: string | null
  action_metadata: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

/**
 * Paginated audit logs response
 */
export interface PaginatedAuditLogsResponse {
  items: AuditLog[]
  total: number
  skip: number
  limit: number
}

/**
 * Status of a module for a tenant
 */
export interface TenantModuleStatus {
  module_name: string
  enabled: boolean
  is_default: boolean
  configured: boolean
  enabled_by_user_id: string | null
  updated_at: string | null
}

/**
 * Response containing all module statuses for a tenant
 */
export interface TenantModulesResponse {
  tenant_id: string
  tenant_type: string
  modules: TenantModuleStatus[]
}

/**
 * Response for module enable/disable action
 */
export interface TenantModuleActionResponse {
  module_name: string
  enabled: boolean
  message: string
}

/**
 * Response for resetting modules to defaults
 */
export interface TenantModulesResetResponse {
  tenant_id: string
  tenant_type: string
  modules_reset: number
  message: string
}

// ==================== API Functions ====================

const PLATFORM_API_PREFIX = '/api/v1/platform'

/**
 * List all tenants with pagination and filters
 */
export async function getTenants(params?: {
  skip?: number
  limit?: number
  search?: string
  is_active?: boolean
}): Promise<PaginatedTenantsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.skip !== undefined) queryParams.set('skip', String(params.skip))
  if (params?.limit !== undefined) queryParams.set('limit', String(params.limit))
  if (params?.search) queryParams.set('search', params.search)
  if (params?.is_active !== undefined) queryParams.set('is_active', String(params.is_active))

  const query = queryParams.toString()
  const url = `${PLATFORM_API_PREFIX}/tenants${query ? `?${query}` : ''}`

  return apiClient.get<PaginatedTenantsResponse>(url)
}

/**
 * Get detailed tenant information with statistics
 */
export async function getTenantDetail(tenantId: string): Promise<TenantDetail> {
  return apiClient.get<TenantDetail>(`${PLATFORM_API_PREFIX}/tenants/${tenantId}`)
}

/**
 * Generate impersonation token for a tenant
 */
export async function impersonateTenant(tenantId: string): Promise<ImpersonationResponse> {
  return apiClient.post<ImpersonationResponse>(
    `${PLATFORM_API_PREFIX}/tenants/${tenantId}/impersonate`
  )
}

/**
 * Deactivate a tenant
 */
export async function deactivateTenant(tenantId: string): Promise<TenantActionResponse> {
  return apiClient.post<TenantActionResponse>(
    `${PLATFORM_API_PREFIX}/tenants/${tenantId}/deactivate`
  )
}

/**
 * Reactivate a tenant
 */
export async function reactivateTenant(tenantId: string): Promise<TenantActionResponse> {
  return apiClient.post<TenantActionResponse>(
    `${PLATFORM_API_PREFIX}/tenants/${tenantId}/reactivate`
  )
}

/**
 * List audit logs
 */
export async function getAuditLogs(params?: {
  skip?: number
  limit?: number
  action?: string
}): Promise<PaginatedAuditLogsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.skip !== undefined) queryParams.set('skip', String(params.skip))
  if (params?.limit !== undefined) queryParams.set('limit', String(params.limit))
  if (params?.action) queryParams.set('action', params.action)

  const query = queryParams.toString()
  const url = `${PLATFORM_API_PREFIX}/audit${query ? `?${query}` : ''}`

  return apiClient.get<PaginatedAuditLogsResponse>(url)
}

// ==================== Tenant Module Management ====================

/**
 * Get all module statuses for a tenant
 */
export async function getTenantModules(tenantId: string): Promise<TenantModulesResponse> {
  return apiClient.get<TenantModulesResponse>(
    `${PLATFORM_API_PREFIX}/tenants/${tenantId}/modules`
  )
}

/**
 * Update a module's enabled status for a tenant
 */
export async function updateTenantModule(
  tenantId: string,
  moduleName: string,
  enabled: boolean
): Promise<TenantModuleActionResponse> {
  return apiClient.put<TenantModuleActionResponse>(
    `${PLATFORM_API_PREFIX}/tenants/${tenantId}/modules/${moduleName}`,
    { enabled }
  )
}

/**
 * Reset all modules to defaults for a tenant
 */
export async function resetTenantModules(tenantId: string): Promise<TenantModulesResetResponse> {
  return apiClient.post<TenantModulesResetResponse>(
    `${PLATFORM_API_PREFIX}/tenants/${tenantId}/modules/reset-defaults`
  )
}
