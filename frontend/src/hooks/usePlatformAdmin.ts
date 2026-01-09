/**
 * Platform Admin Hooks
 *
 * Custom hooks for platform administration functionality.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import {
  getTenants,
  getTenantDetail,
  impersonateTenant,
  deactivateTenant,
  reactivateTenant,
  getAuditLogs,
  type Tenant,
  type TenantDetail,
  type ImpersonationResponse,
  type TenantActionResponse,
  type AuditLog,
} from '@/lib/api/platform'

// ==================== Platform Admin Check ====================

/**
 * Hook to check if current user is a platform admin
 */
export function usePlatformAdmin() {
  const { user, isLoading } = useAuth()

  return {
    isPlatformAdmin: user?.is_platform_admin ?? false,
    isLoading,
    user,
  }
}

// ==================== Tenants Queries ====================

/**
 * Hook to fetch paginated list of tenants
 */
export function useTenants(params?: {
  skip?: number
  limit?: number
  search?: string
  is_active?: boolean
}) {
  const { isPlatformAdmin } = usePlatformAdmin()

  return useQuery({
    queryKey: ['platform', 'tenants', params],
    queryFn: () => getTenants(params),
    enabled: isPlatformAdmin,
    staleTime: 30000, // 30 seconds
  })
}

/**
 * Hook to fetch tenant detail with statistics
 */
export function useTenantDetail(tenantId: string | undefined) {
  const { isPlatformAdmin } = usePlatformAdmin()

  return useQuery({
    queryKey: ['platform', 'tenants', tenantId],
    queryFn: () => getTenantDetail(tenantId!),
    enabled: isPlatformAdmin && !!tenantId,
    staleTime: 30000,
  })
}

// ==================== Tenant Mutations ====================

/**
 * Hook to impersonate a tenant
 */
export function useImpersonateTenant() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (tenantId: string) => impersonateTenant(tenantId),
    onSuccess: () => {
      // Invalidate audit logs after impersonation
      queryClient.invalidateQueries({ queryKey: ['platform', 'audit'] })
    },
  })
}

/**
 * Hook to deactivate a tenant
 */
export function useDeactivateTenant() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (tenantId: string) => deactivateTenant(tenantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform', 'tenants'] })
      queryClient.invalidateQueries({ queryKey: ['platform', 'audit'] })
    },
  })
}

/**
 * Hook to reactivate a tenant
 */
export function useReactivateTenant() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (tenantId: string) => reactivateTenant(tenantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['platform', 'tenants'] })
      queryClient.invalidateQueries({ queryKey: ['platform', 'audit'] })
    },
  })
}

// ==================== Audit Logs ====================

/**
 * Hook to fetch audit logs
 */
export function useAuditLogs(params?: {
  skip?: number
  limit?: number
  action?: string
}) {
  const { isPlatformAdmin } = usePlatformAdmin()

  return useQuery({
    queryKey: ['platform', 'audit', params],
    queryFn: () => getAuditLogs(params),
    enabled: isPlatformAdmin,
    staleTime: 10000, // 10 seconds
  })
}

// ==================== Types Export ====================

export type { Tenant, TenantDetail, ImpersonationResponse, TenantActionResponse, AuditLog }
