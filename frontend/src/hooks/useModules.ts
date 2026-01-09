/**
 * useModules Hook
 *
 * Fetches and caches tenant-specific modules for dynamic navigation.
 * Provides loading states and error handling.
 */

import { useQuery } from '@tanstack/react-query';
import { getModules } from '@/lib/api/modules';
import type { ModulesResponse } from '@/types/modules';

/**
 * Hook to fetch and cache modules for the current tenant.
 *
 * @returns Query result with modules data, loading state, and error
 */
export function useModules() {
  return useQuery<ModulesResponse>({
    queryKey: ['modules'],
    queryFn: getModules,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    refetchOnWindowFocus: false,
    retry: 2,
  });
}

/**
 * Get active modules only (filter out disabled/coming_soon).
 */
export function useActiveModules() {
  const { data, ...rest } = useModules();

  const activeModules = data?.modules.filter(
    (module) => module.status === 'active'
  ) || [];

  return {
    ...rest,
    data: data ? { ...data, modules: activeModules } : undefined,
    modules: activeModules,
    tenantType: data?.tenant_type,
  };
}

/**
 * Check if a specific module is enabled for the current tenant.
 */
export function useModuleEnabled(moduleName: string): boolean {
  const { modules } = useActiveModules();
  return modules.some(
    (m) => m.name === moduleName && m.status === 'active'
  );
}

/**
 * Get navigation items from modules for the sidebar.
 *
 * Flattens module routes into a single navigation array with icons.
 */
export function useNavigationItems() {
  const { modules, tenantType, isLoading, error } = useActiveModules();

  // Build flat navigation from modules
  const navItems = modules
    .sort((a, b) => a.order - b.order)
    .flatMap((module) =>
      module.routes.map((route) => ({
        path: route.path,
        label: route.label,
        icon: route.icon || module.icon,
        exact: route.exact,
        badge: route.badge,
        moduleName: module.name,
      }))
    );

  return {
    navItems,
    tenantType,
    isLoading,
    error,
  };
}

/**
 * Check if the current tenant is a knitting tenant.
 */
export function useIsKnittingTenant(): boolean {
  const { tenantType } = useActiveModules();
  return tenantType === 'hand_knitting' || tenantType === 'machine_knitting';
}

/**
 * Check if the current tenant is a 3D printing tenant.
 */
export function useIs3DPrintTenant(): boolean {
  const { tenantType } = useActiveModules();
  return tenantType === 'three_d_print';
}

/**
 * Check if a specific path is accessible for the current tenant.
 * Returns loading state and access permission.
 */
export function useRouteAccess(path: string) {
  const { modules, isLoading, error } = useActiveModules();

  // If still loading, we don't know yet
  if (isLoading) {
    return { isAllowed: true, isLoading: true, error: null };
  }

  // If error fetching modules, allow access (fail open for better UX)
  if (error) {
    return { isAllowed: true, isLoading: false, error };
  }

  // Check if the path matches any route in active modules
  const isAllowed = modules.some((module) =>
    module.routes.some((route) => {
      // Handle exact matches
      if (route.exact) {
        return path === route.path;
      }
      // Handle path prefix matches (e.g., /yarn matches /yarn/123)
      return path === route.path || path.startsWith(route.path + '/');
    })
  );

  // Also allow common routes that aren't module-specific
  const commonPaths = ['/dashboard', '/settings', '/help', '/logout'];
  const isCommonPath = commonPaths.some(
    (common) => path === common || path.startsWith(common + '/')
  );

  return {
    isAllowed: isAllowed || isCommonPath,
    isLoading: false,
    error: null,
  };
}
