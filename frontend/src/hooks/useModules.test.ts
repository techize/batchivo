import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import {
  useModules,
  useActiveModules,
  useModuleEnabled,
  useNavigationItems,
  useIsKnittingTenant,
  useIs3DPrintTenant,
  useRouteAccess,
} from './useModules'
import { createWrapper } from '@/test/test-utils'

// Mock the modules API
vi.mock('@/lib/api/modules', () => ({
  getModules: vi.fn(),
}))

import { getModules } from '@/lib/api/modules'

const mockGetModules = vi.mocked(getModules)

const mockModulesResponse = {
  tenant_type: 'three_d_print',
  modules: [
    {
      name: 'inventory',
      display_name: 'Inventory',
      description: 'Manage filament and materials',
      icon: 'Package',
      status: 'active' as const,
      order: 1,
      routes: [
        { path: '/inventory', label: 'Inventory', exact: true },
        { path: '/spools', label: 'Spools' },
      ],
    },
    {
      name: 'production',
      display_name: 'Production',
      description: 'Track production runs',
      icon: 'Printer',
      status: 'active' as const,
      order: 2,
      routes: [
        { path: '/production-runs', label: 'Production Runs' },
      ],
    },
    {
      name: 'coming_soon',
      display_name: 'Coming Soon',
      description: 'Future feature',
      icon: 'Star',
      status: 'coming_soon' as const,
      order: 99,
      routes: [
        { path: '/future', label: 'Future' },
      ],
    },
  ],
}

const mockKnittingResponse = {
  ...mockModulesResponse,
  tenant_type: 'hand_knitting',
}

describe('useModules', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches modules successfully', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useModules(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toEqual(mockModulesResponse)
    expect(mockGetModules).toHaveBeenCalledTimes(1)
  })

  it('starts in loading state before data arrives', () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useModules(), {
      wrapper: createWrapper(),
    })

    // Should start in loading state
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })
})

describe('useActiveModules', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('filters out non-active modules', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useActiveModules(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // Should only have 2 active modules (not the coming_soon one)
    expect(result.current.modules).toHaveLength(2)
    expect(result.current.modules.map(m => m.name)).toEqual(['inventory', 'production'])
    expect(result.current.tenantType).toBe('three_d_print')
  })

  it('returns empty array when no data', async () => {
    mockGetModules.mockResolvedValue(undefined as unknown as typeof mockModulesResponse)

    const { result } = renderHook(() => useActiveModules(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.modules).toEqual([])
  })
})

describe('useModuleEnabled', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns true for enabled modules', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useModuleEnabled('inventory'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(true)
    })
  })

  it('returns false for disabled modules', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useModuleEnabled('coming_soon'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(false)
    })
  })

  it('returns false for non-existent modules', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useModuleEnabled('nonexistent'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(false)
    })
  })
})

describe('useNavigationItems', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('builds flat navigation from modules', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useNavigationItems(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // Should have 3 nav items (2 from inventory, 1 from production)
    expect(result.current.navItems).toHaveLength(3)
    expect(result.current.navItems[0].path).toBe('/inventory')
    expect(result.current.navItems[0].moduleName).toBe('inventory')
    expect(result.current.tenantType).toBe('three_d_print')
  })

  it('sorts by module order', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useNavigationItems(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // Inventory (order 1) should come before Production (order 2)
    const inventoryIndex = result.current.navItems.findIndex(n => n.moduleName === 'inventory')
    const productionIndex = result.current.navItems.findIndex(n => n.moduleName === 'production')
    expect(inventoryIndex).toBeLessThan(productionIndex)
  })
})

describe('useIsKnittingTenant', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns true for hand_knitting tenant', async () => {
    mockGetModules.mockResolvedValue(mockKnittingResponse)

    const { result } = renderHook(() => useIsKnittingTenant(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(true)
    })
  })

  it('returns false for 3D print tenant', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useIsKnittingTenant(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(false)
    })
  })
})

describe('useIs3DPrintTenant', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns true for three_d_print tenant', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useIs3DPrintTenant(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(true)
    })
  })

  it('returns false for knitting tenant', async () => {
    mockGetModules.mockResolvedValue(mockKnittingResponse)

    const { result } = renderHook(() => useIs3DPrintTenant(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current).toBe(false)
    })
  })
})

describe('useRouteAccess', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns allowed for module routes', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useRouteAccess('/inventory'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.isAllowed).toBe(true)
  })

  it('returns allowed for nested module routes', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useRouteAccess('/spools/123'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.isAllowed).toBe(true)
  })

  it('returns allowed for common paths', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useRouteAccess('/dashboard'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.isAllowed).toBe(true)
  })

  it('returns not allowed for unknown paths', async () => {
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useRouteAccess('/unknown-route'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.isAllowed).toBe(false)
  })

  it('returns allowed while loading (optimistic)', async () => {
    // When initially loading, we allow access to avoid blocking the user
    mockGetModules.mockResolvedValue(mockModulesResponse)

    const { result } = renderHook(() => useRouteAccess('/inventory'), {
      wrapper: createWrapper(),
    })

    // During initial render, should be optimistic
    expect(result.current.isAllowed).toBe(true)

    // Wait for load to complete
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // After loading, /inventory should still be allowed
    expect(result.current.isAllowed).toBe(true)
  })
})
