import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getModules, getModule, updateModuleSettings } from './modules'
import { apiClient } from '../api'

// Mock the apiClient
vi.mock('../api', () => ({
  apiClient: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}))

const mockApiClient = vi.mocked(apiClient)

describe('modules API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getModules', () => {
    it('fetches all modules for the tenant', async () => {
      const mockResponse = {
        tenant_type: 'three_d_print',
        modules: [
          {
            name: 'inventory',
            display_name: 'Inventory',
            description: 'Manage inventory',
            icon: 'Package',
            status: 'active',
            order: 1,
            routes: [{ path: '/inventory', label: 'Inventory' }],
          },
        ],
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await getModules()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/modules')
      expect(result).toEqual(mockResponse)
      expect(result.tenant_type).toBe('three_d_print')
      expect(result.modules).toHaveLength(1)
    })

    it('handles empty modules list', async () => {
      const mockResponse = {
        tenant_type: 'basic',
        modules: [],
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await getModules()

      expect(result.modules).toHaveLength(0)
    })

    it('propagates API errors', async () => {
      mockApiClient.get.mockRejectedValue(new Error('Unauthorized'))

      await expect(getModules()).rejects.toThrow('Unauthorized')
    })
  })

  describe('getModule', () => {
    it('fetches a specific module by name', async () => {
      const mockModule = {
        name: 'inventory',
        display_name: 'Inventory',
        description: 'Manage filament and materials',
        icon: 'Package',
        status: 'active',
        order: 1,
        routes: [
          { path: '/inventory', label: 'Inventory', exact: true },
          { path: '/spools', label: 'Spools' },
        ],
      }
      mockApiClient.get.mockResolvedValue(mockModule)

      const result = await getModule('inventory')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/modules/inventory')
      expect(result).toEqual(mockModule)
    })

    it('handles module not found', async () => {
      mockApiClient.get.mockRejectedValue(new Error('Module not found'))

      await expect(getModule('nonexistent')).rejects.toThrow('Module not found')
    })
  })

  describe('updateModuleSettings', () => {
    it('updates module settings', async () => {
      const mockModule = {
        name: 'inventory',
        display_name: 'Inventory',
        settings: { low_stock_threshold: 5 },
      }
      const newSettings = { low_stock_threshold: 10 }
      mockApiClient.patch.mockResolvedValue(mockModule)

      const result = await updateModuleSettings('inventory', newSettings)

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/api/v1/modules/inventory/settings',
        newSettings
      )
      expect(result).toEqual(mockModule)
    })

    it('handles empty settings object', async () => {
      const mockModule = { name: 'inventory', settings: {} }
      mockApiClient.patch.mockResolvedValue(mockModule)

      await updateModuleSettings('inventory', {})

      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/api/v1/modules/inventory/settings',
        {}
      )
    })

    it('handles complex settings', async () => {
      const mockModule = {
        name: 'inventory',
        settings: {
          alerts: { enabled: true, email: 'test@example.com' },
          thresholds: [10, 20, 30],
        },
      }
      const newSettings = {
        alerts: { enabled: true, email: 'test@example.com' },
        thresholds: [10, 20, 30],
      }
      mockApiClient.patch.mockResolvedValue(mockModule)

      const result = await updateModuleSettings('inventory', newSettings)

      expect(result.settings).toEqual(newSettings)
    })

    it('propagates API errors', async () => {
      mockApiClient.patch.mockRejectedValue(new Error('Forbidden'))

      await expect(
        updateModuleSettings('inventory', { test: true })
      ).rejects.toThrow('Forbidden')
    })
  })
})
