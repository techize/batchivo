import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useNextSKU, useSKUAvailability, useSKUWithValidation } from './useSKU'
import { createWrapper } from '@/test/test-utils'

// Mock the SKU API
vi.mock('@/lib/api/sku', () => ({
  skuApi: {
    getNextSKU: vi.fn(),
    checkAvailability: vi.fn(),
  },
}))

import { skuApi } from '@/lib/api/sku'

const mockSkuApi = vi.mocked(skuApi)

describe('useNextSKU', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches the next SKU for an entity type', async () => {
    mockSkuApi.getNextSKU.mockResolvedValue({
      next_sku: 'PROD-001',
      highest_existing: 0,
      entity_type: 'PROD',
    })

    const { result } = renderHook(() => useNextSKU('PROD'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.nextSKU).toBe('PROD-001')
    expect(result.current.highestExisting).toBe(0)
    expect(mockSkuApi.getNextSKU).toHaveBeenCalledWith('PROD')
  })

  it('returns incremented SKU when existing products exist', async () => {
    mockSkuApi.getNextSKU.mockResolvedValue({
      next_sku: 'PROD-043',
      highest_existing: 42,
      entity_type: 'PROD',
    })

    const { result } = renderHook(() => useNextSKU('PROD'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.nextSKU).toBe('PROD-043')
    expect(result.current.highestExisting).toBe(42)
  })

  it('does not fetch when disabled', async () => {
    const { result } = renderHook(() => useNextSKU('MOD', false), {
      wrapper: createWrapper(),
    })

    // Should not be loading when disabled
    expect(result.current.isLoading).toBe(false)
    expect(mockSkuApi.getNextSKU).not.toHaveBeenCalled()
  })

  it('handles API errors', async () => {
    mockSkuApi.getNextSKU.mockRejectedValue(new Error('API Error'))

    const { result } = renderHook(() => useNextSKU('PROD'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
    })

    expect(result.current.nextSKU).toBeUndefined()
  })

  it('supports different entity types', async () => {
    mockSkuApi.getNextSKU.mockResolvedValue({
      next_sku: 'FIL-005',
      highest_existing: 4,
      entity_type: 'FIL',
    })

    const { result } = renderHook(() => useNextSKU('FIL'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.nextSKU).toBe('FIL-005')
    expect(mockSkuApi.getNextSKU).toHaveBeenCalledWith('FIL')
  })
})

describe('useSKUAvailability', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('checks SKU availability successfully', async () => {
    mockSkuApi.checkAvailability.mockResolvedValue({
      sku: 'PROD-001',
      available: true,
      entity_type: 'PROD',
    })

    const { result } = renderHook(() => useSKUAvailability('PROD'), {
      wrapper: createWrapper(),
    })

    const checkResult = await result.current.checkSKU('PROD-001')

    expect(checkResult.available).toBe(true)
    expect(checkResult.sku).toBe('PROD-001')
    expect(mockSkuApi.checkAvailability).toHaveBeenCalledWith('PROD', 'PROD-001')
  })

  it('returns unavailable for taken SKUs', async () => {
    mockSkuApi.checkAvailability.mockResolvedValue({
      sku: 'PROD-001',
      available: false,
      entity_type: 'PROD',
      existing_entity_id: 'uuid-123',
    })

    const { result } = renderHook(() => useSKUAvailability('PROD'), {
      wrapper: createWrapper(),
    })

    const checkResult = await result.current.checkSKU('PROD-001')

    expect(checkResult.available).toBe(false)
    expect(checkResult.existing_entity_id).toBe('uuid-123')
  })

  it('handles check errors', async () => {
    mockSkuApi.checkAvailability.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useSKUAvailability('PROD'), {
      wrapper: createWrapper(),
    })

    await expect(result.current.checkSKU('PROD-001')).rejects.toThrow('Network error')
  })

  it('can reset mutation state', async () => {
    mockSkuApi.checkAvailability.mockResolvedValue({
      sku: 'PROD-001',
      available: true,
      entity_type: 'PROD',
    })

    const { result } = renderHook(() => useSKUAvailability('PROD'), {
      wrapper: createWrapper(),
    })

    await result.current.checkSKU('PROD-001')

    // Wait for mutation to complete and result to be available
    await waitFor(() => {
      expect(result.current.lastResult).toBeTruthy()
    })

    result.current.reset()

    await waitFor(() => {
      expect(result.current.lastResult).toBeUndefined()
    })
  })
})

describe('useSKUWithValidation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('combines next SKU and availability checking', async () => {
    mockSkuApi.getNextSKU.mockResolvedValue({
      next_sku: 'MOD-010',
      highest_existing: 9,
      entity_type: 'MOD',
    })

    mockSkuApi.checkAvailability.mockResolvedValue({
      sku: 'MOD-005',
      available: true,
      entity_type: 'MOD',
    })

    const { result } = renderHook(() => useSKUWithValidation('MOD'), {
      wrapper: createWrapper(),
    })

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.isLoadingNextSKU).toBe(false)
    })

    expect(result.current.nextSKU).toBe('MOD-010')
    expect(result.current.highestExisting).toBe(9)

    // Check availability
    const checkResult = await result.current.checkSKU('MOD-005')
    expect(checkResult.available).toBe(true)
  })

  it('exposes combined loading state', async () => {
    mockSkuApi.getNextSKU.mockImplementation(() => new Promise(() => {})) // Never resolves

    const { result } = renderHook(() => useSKUWithValidation('COM'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.isLoadingNextSKU).toBe(true)
  })
})
