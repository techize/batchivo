import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { apiClient, checkHealth } from './api'

// Mock axios
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  }
  return { default: mockAxios }
})

// Mock auth module
vi.mock('./auth', () => ({
  getAuthTokens: vi.fn(() => null),
  setAuthTokens: vi.fn(),
  isTokenExpired: vi.fn(() => false),
  clearAuthTokens: vi.fn(),
}))

const mockAxios = vi.mocked(axios)

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('get', () => {
    it('makes a GET request and returns data', async () => {
      const mockData = { id: 1, name: 'Test' }
      // @ts-expect-error - Mocking axios response
      mockAxios.get.mockResolvedValue({ data: mockData })

      const result = await apiClient.get('/test')

      expect(mockAxios.get).toHaveBeenCalledWith('/test', undefined)
      expect(result).toEqual(mockData)
    })

    it('passes config to GET request', async () => {
      const mockData = { id: 1 }
      const config = { params: { page: 1 } }
      // @ts-expect-error - Mocking axios response
      mockAxios.get.mockResolvedValue({ data: mockData })

      await apiClient.get('/test', config)

      expect(mockAxios.get).toHaveBeenCalledWith('/test', config)
    })

    it('throws on error', async () => {
      const error = new Error('Network error')
      mockAxios.get.mockRejectedValue(error)

      await expect(apiClient.get('/test')).rejects.toThrow('Network error')
    })
  })

  describe('post', () => {
    it('makes a POST request with data', async () => {
      const mockResponse = { id: 1, created: true }
      const postData = { name: 'New Item' }
      // @ts-expect-error - Mocking axios response
      mockAxios.post.mockResolvedValue({ data: mockResponse })

      const result = await apiClient.post('/items', postData)

      expect(mockAxios.post).toHaveBeenCalledWith('/items', postData, undefined)
      expect(result).toEqual(mockResponse)
    })

    it('handles POST without data', async () => {
      const mockResponse = { success: true }
      // @ts-expect-error - Mocking axios response
      mockAxios.post.mockResolvedValue({ data: mockResponse })

      await apiClient.post('/trigger')

      expect(mockAxios.post).toHaveBeenCalledWith('/trigger', undefined, undefined)
    })
  })

  describe('put', () => {
    it('makes a PUT request', async () => {
      const mockResponse = { id: 1, updated: true }
      const updateData = { name: 'Updated' }
      // @ts-expect-error - Mocking axios response
      mockAxios.put.mockResolvedValue({ data: mockResponse })

      const result = await apiClient.put('/items/1', updateData)

      expect(mockAxios.put).toHaveBeenCalledWith('/items/1', updateData, undefined)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('patch', () => {
    it('makes a PATCH request', async () => {
      const mockResponse = { id: 1, patched: true }
      const patchData = { status: 'active' }
      // @ts-expect-error - Mocking axios response
      mockAxios.patch.mockResolvedValue({ data: mockResponse })

      const result = await apiClient.patch('/items/1', patchData)

      expect(mockAxios.patch).toHaveBeenCalledWith('/items/1', patchData, undefined)
      expect(result).toEqual(mockResponse)
    })
  })

  describe('delete', () => {
    it('makes a DELETE request', async () => {
      const mockResponse = { deleted: true }
      // @ts-expect-error - Mocking axios response
      mockAxios.delete.mockResolvedValue({ data: mockResponse })

      const result = await apiClient.delete('/items/1')

      expect(mockAxios.delete).toHaveBeenCalledWith('/items/1', undefined)
      expect(result).toEqual(mockResponse)
    })
  })
})

describe('checkHealth', () => {
  it('calls the health endpoint', async () => {
    const mockHealth = { status: 'healthy', environment: 'production' }
    // @ts-expect-error - Mocking axios response
    mockAxios.get.mockResolvedValue({ data: mockHealth })

    const result = await checkHealth()

    expect(mockAxios.get).toHaveBeenCalledWith('/health', undefined)
    expect(result).toEqual(mockHealth)
  })
})
