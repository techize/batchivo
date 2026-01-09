import { describe, it, expect, vi, beforeEach } from 'vitest'
import { skuApi } from './sku'
import { apiClient } from '../api'

// Mock the apiClient
vi.mock('../api', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

const mockApiClient = vi.mocked(apiClient)

describe('skuApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getNextSKU', () => {
    it('fetches next SKU for PROD entity type', async () => {
      const mockResponse = {
        next_sku: 'PROD-001',
        highest_existing: 0,
        entity_type: 'PROD',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await skuApi.getNextSKU('PROD')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/next/PROD')
      expect(result).toEqual(mockResponse)
    })

    it('fetches next SKU for MOD entity type', async () => {
      const mockResponse = {
        next_sku: 'MOD-015',
        highest_existing: 14,
        entity_type: 'MOD',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await skuApi.getNextSKU('MOD')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/next/MOD')
      expect(result).toEqual(mockResponse)
    })

    it('fetches next SKU for COM entity type', async () => {
      const mockResponse = {
        next_sku: 'COM-100',
        highest_existing: 99,
        entity_type: 'COM',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await skuApi.getNextSKU('COM')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/next/COM')
      expect(result).toEqual(mockResponse)
    })

    it('fetches next SKU for FIL entity type', async () => {
      const mockResponse = {
        next_sku: 'FIL-050',
        highest_existing: 49,
        entity_type: 'FIL',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await skuApi.getNextSKU('FIL')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/next/FIL')
      expect(result).toEqual(mockResponse)
    })

    it('propagates API errors', async () => {
      mockApiClient.get.mockRejectedValue(new Error('Network error'))

      await expect(skuApi.getNextSKU('PROD')).rejects.toThrow('Network error')
    })
  })

  describe('checkAvailability', () => {
    it('checks availability for a SKU', async () => {
      const mockResponse = {
        sku: 'PROD-001',
        available: true,
        entity_type: 'PROD',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await skuApi.checkAvailability('PROD', 'PROD-001')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/check/PROD/PROD-001')
      expect(result).toEqual(mockResponse)
    })

    it('returns unavailable for taken SKU', async () => {
      const mockResponse = {
        sku: 'PROD-001',
        available: false,
        entity_type: 'PROD',
        existing_entity_id: 'uuid-123',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await skuApi.checkAvailability('PROD', 'PROD-001')

      expect(result.available).toBe(false)
      expect(result.existing_entity_id).toBe('uuid-123')
    })

    it('encodes SKU with special characters', async () => {
      const mockResponse = {
        sku: 'PROD-001/A',
        available: true,
        entity_type: 'PROD',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      await skuApi.checkAvailability('PROD', 'PROD-001/A')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/check/PROD/PROD-001%2FA')
    })

    it('handles SKU with spaces', async () => {
      const mockResponse = {
        sku: 'PROD 001',
        available: true,
        entity_type: 'PROD',
      }
      mockApiClient.get.mockResolvedValue(mockResponse)

      await skuApi.checkAvailability('PROD', 'PROD 001')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/sku/check/PROD/PROD%20001')
    })

    it('propagates API errors', async () => {
      mockApiClient.get.mockRejectedValue(new Error('Server error'))

      await expect(skuApi.checkAvailability('PROD', 'TEST')).rejects.toThrow('Server error')
    })
  })
})
