import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import {
  useOfflineSpools,
  useOfflineSpool,
  useOfflineMaterialTypes,
  useOfflineIndicator,
} from './useOfflineSpools'

// Mock the spools API
vi.mock('@/lib/api/spools', () => ({
  spoolsApi: {
    list: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  materialTypesApi: {
    list: vi.fn(),
  },
}))

// Mock IndexedDB functions
vi.mock('@/lib/db/indexeddb', () => ({
  isIndexedDBAvailable: vi.fn(),
  getSpools: vi.fn(),
  getSpool: vi.fn(),
  saveSpools: vi.fn(),
  saveSpool: vi.fn(),
  deleteSpool: vi.fn(),
  getAllMaterialTypes: vi.fn(),
  saveMaterialTypes: vi.fn(),
  addToSyncQueue: vi.fn(),
  getSyncQueue: vi.fn(),
  getSyncQueueCount: vi.fn(),
  removeFromSyncQueue: vi.fn(),
  updateSyncItemError: vi.fn(),
}))

import { spoolsApi, materialTypesApi } from '@/lib/api/spools'
import {
  isIndexedDBAvailable,
  getSpools,
  getSpool,
  saveSpools,
  saveSpool,
  deleteSpool,
  getAllMaterialTypes,
  saveMaterialTypes,
  addToSyncQueue,
  getSyncQueue,
  getSyncQueueCount,
  removeFromSyncQueue,
  updateSyncItemError,
} from '@/lib/db/indexeddb'

const mockSpoolsApi = vi.mocked(spoolsApi)
const mockMaterialTypesApi = vi.mocked(materialTypesApi)
const mockIsIndexedDBAvailable = vi.mocked(isIndexedDBAvailable)
const mockGetSpools = vi.mocked(getSpools)
const mockGetSpool = vi.mocked(getSpool)
const mockSaveSpools = vi.mocked(saveSpools)
const mockSaveSpool = vi.mocked(saveSpool)
const mockDeleteSpool = vi.mocked(deleteSpool)
const mockGetAllMaterialTypes = vi.mocked(getAllMaterialTypes)
const mockSaveMaterialTypes = vi.mocked(saveMaterialTypes)
const mockAddToSyncQueue = vi.mocked(addToSyncQueue)
const mockGetSyncQueue = vi.mocked(getSyncQueue)
const mockGetSyncQueueCount = vi.mocked(getSyncQueueCount)
const mockRemoveFromSyncQueue = vi.mocked(removeFromSyncQueue)
const mockUpdateSyncItemError = vi.mocked(updateSyncItemError)

// Sample test data
const mockSpool = {
  id: 'spool-1',
  spool_id: 'SPOOL-001',
  material_type_id: 'mat-1',
  material_type_name: 'PLA',
  brand: 'TestBrand',
  color: 'Red',
  is_active: true,
  initial_weight_grams: 1000,
  current_weight_grams: 800,
  cost_per_gram: 0.025,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockSpoolsList = {
  spools: [mockSpool],
  total: 1,
  page: 1,
  page_size: 50,
}

const mockMaterialType = {
  id: 'mat-1',
  code: 'PLA',
  name: 'PLA',
  description: 'Polylactic Acid',
  density: 1.24,
  print_temp_min: 190,
  print_temp_max: 220,
  bed_temp_min: 50,
  bed_temp_max: 60,
}

// Helper to create wrapper with QueryClient
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

// Track event listeners
let onlineListeners: Array<() => void> = []
let offlineListeners: Array<() => void> = []

describe('useOfflineSpools', () => {
  let queryClient: QueryClient
  let originalOnLine: boolean

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = createTestQueryClient()
    onlineListeners = []
    offlineListeners = []

    // Store original value
    originalOnLine = navigator.onLine

    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      value: true,
      writable: true,
      configurable: true,
    })

    // Mock window event listeners
    vi.spyOn(window, 'addEventListener').mockImplementation((event, handler) => {
      if (event === 'online') onlineListeners.push(handler as () => void)
      if (event === 'offline') offlineListeners.push(handler as () => void)
    })
    vi.spyOn(window, 'removeEventListener').mockImplementation((event, handler) => {
      if (event === 'online') {
        onlineListeners = onlineListeners.filter((h) => h !== handler)
      }
      if (event === 'offline') {
        offlineListeners = offlineListeners.filter((h) => h !== handler)
      }
    })

    // Default mocks
    mockIsIndexedDBAvailable.mockReturnValue(true)
    mockGetSyncQueueCount.mockResolvedValue(0)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    // Restore original value
    Object.defineProperty(navigator, 'onLine', {
      value: originalOnLine,
      writable: true,
      configurable: true,
    })
  })

  describe('useOfflineSpools hook', () => {
    it('returns sync status with correct initial values', () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.syncStatus.isOnline).toBe(true)
      expect(result.current.syncStatus.isSyncing).toBe(false)
      expect(result.current.syncStatus.pendingCount).toBe(0)
      expect(result.current.syncStatus.lastSyncedAt).toBeNull()
      expect(result.current.syncStatus.syncError).toBeNull()
    })

    it('sets up online/offline event listeners', () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      expect(window.addEventListener).toHaveBeenCalledWith('online', expect.any(Function))
      expect(window.addEventListener).toHaveBeenCalledWith('offline', expect.any(Function))
    })

    it('exposes triggerSync function', () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      expect(typeof result.current.triggerSync).toBe('function')
    })

    it('starts in loading state', () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isLoading).toBe(true)
    })

    it('fetches from network when online', async () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSpoolsApi.list).toHaveBeenCalled()
      expect(result.current.data).toEqual(mockSpoolsList)
    })

    it('caches data to IndexedDB after network fetch', async () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSaveSpools).toHaveBeenCalledWith(mockSpoolsList.spools)
    })

    it('updates lastSyncedAt after successful fetch', async () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.syncStatus.lastSyncedAt).not.toBeNull()
    })
  })

  describe('useOfflineSpool hook', () => {
    it('does not fetch when id is null', () => {
      const { result } = renderHook(() => useOfflineSpool(null), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(mockSpoolsApi.get).not.toHaveBeenCalled()
    })

    it('provides isOnline status', () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isOnline).toBe(true)
    })

    it('provides mutation functions', () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      expect(typeof result.current.updateSpool).toBe('function')
      expect(typeof result.current.deleteSpool).toBe('function')
    })

    it('provides isUpdating state initially as false', () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isUpdating).toBe(false)
    })

    it('provides isDeleting state initially as false', () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isDeleting).toBe(false)
    })

    it('fetches spool from network when online', async () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSpoolsApi.get).toHaveBeenCalledWith('spool-1')
      expect(result.current.data).toEqual(mockSpool)
    })

    it('caches spool to IndexedDB after fetch', async () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSaveSpool).toHaveBeenCalled()
    })

    it('updates spool when online', async () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)
      mockSpoolsApi.update.mockResolvedValue({ ...mockSpool, color: 'Blue' })

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.updateSpool({ color: 'Blue' })
      })

      await waitFor(() => {
        expect(mockSpoolsApi.update).toHaveBeenCalledWith('spool-1', { color: 'Blue' })
      })
    })

    it('deletes spool when online', async () => {
      mockSpoolsApi.get.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)
      mockSpoolsApi.delete.mockResolvedValue(undefined)
      mockDeleteSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.deleteSpool()
      })

      await waitFor(() => {
        expect(mockSpoolsApi.delete).toHaveBeenCalledWith('spool-1')
      })
    })
  })

  describe('useOfflineMaterialTypes hook', () => {
    it('sets up online/offline event listeners', () => {
      mockMaterialTypesApi.list.mockResolvedValue([mockMaterialType])
      mockSaveMaterialTypes.mockResolvedValue(undefined)

      renderHook(() => useOfflineMaterialTypes(), {
        wrapper: createWrapper(queryClient),
      })

      expect(window.addEventListener).toHaveBeenCalledWith('online', expect.any(Function))
      expect(window.addEventListener).toHaveBeenCalledWith('offline', expect.any(Function))
    })

    it('fetches material types from network when online', async () => {
      mockMaterialTypesApi.list.mockResolvedValue([mockMaterialType])
      mockSaveMaterialTypes.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineMaterialTypes(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockMaterialTypesApi.list).toHaveBeenCalled()
      expect(result.current.data).toEqual([mockMaterialType])
    })

    it('caches material types to IndexedDB after fetch', async () => {
      mockMaterialTypesApi.list.mockResolvedValue([mockMaterialType])
      mockSaveMaterialTypes.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineMaterialTypes(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSaveMaterialTypes).toHaveBeenCalledWith([mockMaterialType])
    })
  })

  describe('useOfflineIndicator hook', () => {
    it('returns online status', () => {
      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isOnline).toBe(true)
    })

    it('returns initial pending count as 0', () => {
      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.pendingCount).toBe(0)
    })

    it('returns hasPendingChanges as false initially', () => {
      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.hasPendingChanges).toBe(false)
    })

    it('cleans up event listeners on unmount', () => {
      const { unmount } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      unmount()

      expect(window.removeEventListener).toHaveBeenCalledWith('online', expect.any(Function))
      expect(window.removeEventListener).toHaveBeenCalledWith('offline', expect.any(Function))
    })

    it('handles IndexedDB not available', () => {
      mockIsIndexedDBAvailable.mockReturnValue(false)

      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isOnline).toBe(true)
      expect(result.current.pendingCount).toBe(0)
    })

    it('responds to offline event', async () => {
      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isOnline).toBe(true)

      act(() => {
        offlineListeners.forEach((listener) => listener())
      })

      expect(result.current.isOnline).toBe(false)
    })

    it('responds to online event', async () => {
      // Start offline
      Object.defineProperty(navigator, 'onLine', { value: false })

      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      expect(result.current.isOnline).toBe(false)

      act(() => {
        onlineListeners.forEach((listener) => listener())
      })

      expect(result.current.isOnline).toBe(true)
    })

    it('updates pending count from IndexedDB', async () => {
      mockGetSyncQueueCount.mockResolvedValue(5)

      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => {
        expect(result.current.pendingCount).toBe(5)
      })
    })

    it('calculates hasPendingChanges based on count', async () => {
      mockGetSyncQueueCount.mockResolvedValue(3)

      const { result } = renderHook(() => useOfflineIndicator(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => {
        expect(result.current.hasPendingChanges).toBe(true)
      })
    })
  })

  describe('offline scenarios', () => {
    beforeEach(() => {
      Object.defineProperty(navigator, 'onLine', { value: false })
    })

    it('useOfflineSpools uses IndexedDB cache when offline', async () => {
      mockGetSpools.mockResolvedValue([mockSpool])

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSpoolsApi.list).not.toHaveBeenCalled()
      expect(mockGetSpools).toHaveBeenCalled()
      expect(result.current.data?.spools).toEqual([mockSpool])
    })

    it('useOfflineSpools passes filter params to IndexedDB', async () => {
      mockGetSpools.mockResolvedValue([mockSpool])
      const params = { is_active: true, material_type_id: 'mat-1', search: 'test' }

      renderHook(() => useOfflineSpools(params), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => {
        expect(mockGetSpools).toHaveBeenCalledWith({
          isActive: true,
          materialTypeId: 'mat-1',
          search: 'test',
        })
      })
    })

    it('useOfflineSpool uses IndexedDB cache when offline', async () => {
      mockGetSpool.mockResolvedValue(mockSpool)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockSpoolsApi.get).not.toHaveBeenCalled()
      expect(mockGetSpool).toHaveBeenCalledWith('spool-1')
    })

    it('useOfflineSpool queues updates for sync when offline', async () => {
      mockGetSpool.mockResolvedValue(mockSpool)
      mockSaveSpool.mockResolvedValue(undefined)
      mockAddToSyncQueue.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.updateSpool({ color: 'Blue' })
      })

      await waitFor(() => {
        expect(mockAddToSyncQueue).toHaveBeenCalledWith('spool', 'spool-1', 'update', {
          color: 'Blue',
        })
      })
    })

    it('useOfflineSpool queues deletes for sync when offline', async () => {
      mockGetSpool.mockResolvedValue(mockSpool)
      mockAddToSyncQueue.mockResolvedValue(undefined)
      mockDeleteSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.deleteSpool()
      })

      await waitFor(() => {
        expect(mockAddToSyncQueue).toHaveBeenCalledWith('spool', 'spool-1', 'delete', null)
      })
    })

    it('useOfflineMaterialTypes uses IndexedDB cache when offline', async () => {
      mockGetAllMaterialTypes.mockResolvedValue([mockMaterialType])

      const { result } = renderHook(() => useOfflineMaterialTypes(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockMaterialTypesApi.list).not.toHaveBeenCalled()
      expect(mockGetAllMaterialTypes).toHaveBeenCalled()
    })
  })

  describe('error scenarios', () => {
    it('falls back to IndexedDB when network fails', async () => {
      mockSpoolsApi.list.mockRejectedValue(new Error('Network error'))
      mockGetSpools.mockResolvedValue([mockSpool])

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockGetSpools).toHaveBeenCalled()
      expect(result.current.data?.spools).toEqual([mockSpool])
    })

    it('useOfflineSpool falls back to cache on network error', async () => {
      mockSpoolsApi.get.mockRejectedValue(new Error('Network error'))
      mockGetSpool.mockResolvedValue(mockSpool)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockGetSpool).toHaveBeenCalledWith('spool-1')
    })

    it('useOfflineMaterialTypes falls back to cache on network error', async () => {
      mockMaterialTypesApi.list.mockRejectedValue(new Error('Network error'))
      mockGetAllMaterialTypes.mockResolvedValue([mockMaterialType])

      const { result } = renderHook(() => useOfflineMaterialTypes(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockGetAllMaterialTypes).toHaveBeenCalled()
    })

    it('throws error when offline and no cache available', async () => {
      Object.defineProperty(navigator, 'onLine', { value: false })
      mockIsIndexedDBAvailable.mockReturnValue(false)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('No network and no cached data available')
    })

    it('useOfflineSpool throws when spool not in cache', async () => {
      Object.defineProperty(navigator, 'onLine', { value: false })
      mockGetSpool.mockResolvedValue(undefined)

      const { result } = renderHook(() => useOfflineSpool('spool-1'), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('Spool not found')
    })

    it('useOfflineMaterialTypes throws when no cache available', async () => {
      Object.defineProperty(navigator, 'onLine', { value: false })
      mockGetAllMaterialTypes.mockResolvedValue([])

      const { result } = renderHook(() => useOfflineMaterialTypes(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isError).toBe(true))

      expect(result.current.error?.message).toBe('No material types available')
    })
  })

  describe('sync functionality', () => {
    it('triggerSync calls getSyncQueue when online', async () => {
      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)
      mockGetSyncQueue.mockResolvedValue([])

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.triggerSync()
      })

      expect(mockGetSyncQueue).toHaveBeenCalled()
    })

    it('processes update operations in sync queue', async () => {
      const syncItem = {
        id: 'sync-1',
        entityType: 'spool' as const,
        entityId: 'spool-1',
        operation: 'update' as const,
        data: { color: 'Blue' },
        createdAt: '2024-01-01T00:00:00Z',
        retryCount: 0,
      }

      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)
      mockGetSyncQueue.mockResolvedValue([syncItem])
      mockSpoolsApi.update.mockResolvedValue({ ...mockSpool, color: 'Blue' })
      mockRemoveFromSyncQueue.mockResolvedValue(undefined)
      mockGetSyncQueueCount.mockResolvedValue(0)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.triggerSync()
      })

      await waitFor(() => {
        expect(mockSpoolsApi.update).toHaveBeenCalledWith('spool-1', { color: 'Blue' })
        expect(mockRemoveFromSyncQueue).toHaveBeenCalledWith('sync-1')
      })
    })

    it('processes delete operations in sync queue', async () => {
      const syncItem = {
        id: 'sync-1',
        entityType: 'spool' as const,
        entityId: 'spool-1',
        operation: 'delete' as const,
        data: null,
        createdAt: '2024-01-01T00:00:00Z',
        retryCount: 0,
      }

      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)
      mockGetSyncQueue.mockResolvedValue([syncItem])
      mockSpoolsApi.delete.mockResolvedValue(undefined)
      mockRemoveFromSyncQueue.mockResolvedValue(undefined)
      mockGetSyncQueueCount.mockResolvedValue(0)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.triggerSync()
      })

      await waitFor(() => {
        expect(mockSpoolsApi.delete).toHaveBeenCalledWith('spool-1')
        expect(mockRemoveFromSyncQueue).toHaveBeenCalledWith('sync-1')
      })
    })

    it('skips sync items that exceed max retries', async () => {
      const syncItem = {
        id: 'sync-1',
        entityType: 'spool' as const,
        entityId: 'spool-1',
        operation: 'update' as const,
        data: { color: 'Blue' },
        createdAt: '2024-01-01T00:00:00Z',
        retryCount: 3, // MAX_SYNC_RETRIES
      }

      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)
      mockGetSyncQueue.mockResolvedValue([syncItem])
      mockGetSyncQueueCount.mockResolvedValue(1)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.triggerSync()
      })

      // Should not call update for items at max retries
      expect(mockSpoolsApi.update).not.toHaveBeenCalled()
    })

    it('updates sync item error on failure', async () => {
      const syncItem = {
        id: 'sync-1',
        entityType: 'spool' as const,
        entityId: 'spool-1',
        operation: 'update' as const,
        data: { color: 'Blue' },
        createdAt: '2024-01-01T00:00:00Z',
        retryCount: 0,
      }

      mockSpoolsApi.list.mockResolvedValue(mockSpoolsList)
      mockSaveSpools.mockResolvedValue(undefined)
      mockGetSyncQueue.mockResolvedValue([syncItem])
      mockSpoolsApi.update.mockRejectedValue(new Error('API Error'))
      mockUpdateSyncItemError.mockResolvedValue(undefined)
      mockGetSyncQueueCount.mockResolvedValue(1)

      const { result } = renderHook(() => useOfflineSpools(), {
        wrapper: createWrapper(queryClient),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      await act(async () => {
        result.current.triggerSync()
      })

      await waitFor(() => {
        expect(mockUpdateSyncItemError).toHaveBeenCalledWith('sync-1', 'API Error')
      })
    })
  })
})
