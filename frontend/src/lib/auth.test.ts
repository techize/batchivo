import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  setAuthTokens,
  getAuthTokens,
  clearAuthTokens,
  isTokenExpired,
  isTokenExpiringSoon,
  getAuthHeader,
  login,
  logout,
  register,
  refreshAccessToken,
  requestPasswordReset,
  resetPassword,
} from './auth'

// Mock sessionStorage
const mockSessionStorage: Record<string, string> = {}
const sessionStorageMock = {
  getItem: vi.fn((key: string) => mockSessionStorage[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    mockSessionStorage[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete mockSessionStorage[key]
  }),
  clear: vi.fn(() => {
    Object.keys(mockSessionStorage).forEach(key => delete mockSessionStorage[key])
  }),
  length: 0,
  key: vi.fn(),
}

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
  writable: true,
})

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('Token Management', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorageMock.clear()
  })

  describe('setAuthTokens', () => {
    it('stores tokens in sessionStorage', () => {
      const tokens = {
        accessToken: 'test-access-token',
        refreshToken: 'test-refresh-token',
        tokenType: 'bearer',
        expiresAt: Date.now() + 3600000,
      }

      setAuthTokens(tokens)

      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        'batchivo_auth_tokens',
        JSON.stringify(tokens)
      )
    })
  })

  describe('getAuthTokens', () => {
    it('retrieves tokens from sessionStorage', () => {
      const tokens = {
        accessToken: 'test-access-token',
        refreshToken: 'test-refresh-token',
        tokenType: 'bearer',
        expiresAt: Date.now() + 3600000,
      }
      mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify(tokens)

      const result = getAuthTokens()

      expect(result).toEqual(tokens)
    })

    it('returns null when no tokens stored', () => {
      const result = getAuthTokens()

      expect(result).toBeNull()
    })

    it('handles invalid JSON gracefully', () => {
      mockSessionStorage['batchivo_auth_tokens'] = 'invalid-json'

      const result = getAuthTokens()

      expect(result).toBeNull()
    })
  })

  describe('clearAuthTokens', () => {
    it('removes tokens from sessionStorage', () => {
      mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify({ accessToken: 'test' })

      clearAuthTokens()

      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('batchivo_auth_tokens')
    })
  })
})

describe('Token Expiry', () => {
  describe('isTokenExpired', () => {
    it('returns true for null tokens', () => {
      expect(isTokenExpired(null)).toBe(true)
    })

    it('returns true for expired tokens', () => {
      const tokens = {
        accessToken: 'test',
        refreshToken: 'test',
        tokenType: 'bearer',
        expiresAt: Date.now() - 1000, // Expired 1 second ago
      }

      expect(isTokenExpired(tokens)).toBe(true)
    })

    it('returns false for valid tokens', () => {
      const tokens = {
        accessToken: 'test',
        refreshToken: 'test',
        tokenType: 'bearer',
        expiresAt: Date.now() + 3600000, // Expires in 1 hour
      }

      expect(isTokenExpired(tokens)).toBe(false)
    })
  })

  describe('isTokenExpiringSoon', () => {
    it('returns true for null tokens', () => {
      expect(isTokenExpiringSoon(null)).toBe(true)
    })

    it('returns true for tokens expiring within 5 minutes', () => {
      const tokens = {
        accessToken: 'test',
        refreshToken: 'test',
        tokenType: 'bearer',
        expiresAt: Date.now() + 2 * 60 * 1000, // Expires in 2 minutes
      }

      expect(isTokenExpiringSoon(tokens)).toBe(true)
    })

    it('returns false for tokens expiring after 5 minutes', () => {
      const tokens = {
        accessToken: 'test',
        refreshToken: 'test',
        tokenType: 'bearer',
        expiresAt: Date.now() + 10 * 60 * 1000, // Expires in 10 minutes
      }

      expect(isTokenExpiringSoon(tokens)).toBe(false)
    })
  })
})

describe('getAuthHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorageMock.clear()
  })

  it('returns null when no tokens', () => {
    expect(getAuthHeader()).toBeNull()
  })

  it('returns formatted authorization header', () => {
    const tokens = {
      accessToken: 'test-access-token',
      refreshToken: 'test-refresh-token',
      tokenType: 'bearer',
      expiresAt: Date.now() + 3600000,
    }
    mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify(tokens)

    expect(getAuthHeader()).toBe('bearer test-access-token')
  })
})

describe('Authentication Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorageMock.clear()
  })

  describe('login', () => {
    it('sends login request and stores tokens', async () => {
      const mockResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await login({ email: 'test@example.com', password: 'password' })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'test@example.com', password: 'password' }),
        })
      )
      expect(result.accessToken).toBe('new-access-token')
      expect(sessionStorageMock.setItem).toHaveBeenCalled()
    })

    it('throws on login failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Invalid credentials' }),
      })

      await expect(login({ email: 'test@example.com', password: 'wrong' }))
        .rejects.toThrow('Invalid credentials')
    })
  })

  describe('logout', () => {
    it('sends logout request and clears tokens', async () => {
      const tokens = {
        accessToken: 'test-access-token',
        refreshToken: 'test-refresh-token',
        tokenType: 'bearer',
        expiresAt: Date.now() + 3600000,
      }
      mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify(tokens)
      mockFetch.mockResolvedValueOnce({ ok: true })

      await logout()

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/logout',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Authorization': 'Bearer test-access-token' },
        })
      )
      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('batchivo_auth_tokens')
    })

    it('clears tokens even if logout request fails', async () => {
      const tokens = {
        accessToken: 'test-access-token',
        refreshToken: 'test-refresh-token',
        tokenType: 'bearer',
        expiresAt: Date.now() + 3600000,
      }
      mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify(tokens)
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await logout()

      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('batchivo_auth_tokens')
    })
  })

  describe('register', () => {
    it('sends register request and stores tokens', async () => {
      const mockResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await register({
        email: 'new@example.com',
        password: 'password123',
        full_name: 'Test User',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/register',
        expect.objectContaining({
          method: 'POST',
        })
      )
      expect(result.accessToken).toBe('new-access-token')
    })

    it('throws on registration failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Email already exists' }),
      })

      await expect(register({ email: 'existing@example.com', password: 'password' }))
        .rejects.toThrow('Email already exists')
    })
  })

  describe('refreshAccessToken', () => {
    it('refreshes token and stores new tokens', async () => {
      const oldTokens = {
        accessToken: 'old-access-token',
        refreshToken: 'refresh-token',
        tokenType: 'bearer',
        expiresAt: Date.now() - 1000,
      }
      mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify(oldTokens)

      const mockResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        expires_in: 3600,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await refreshAccessToken()

      expect(result?.accessToken).toBe('new-access-token')
      expect(sessionStorageMock.setItem).toHaveBeenCalled()
    })

    it('returns null when no tokens exist', async () => {
      const result = await refreshAccessToken()

      expect(result).toBeNull()
    })

    it('clears tokens on refresh failure', async () => {
      const oldTokens = {
        accessToken: 'old-access-token',
        refreshToken: 'refresh-token',
        tokenType: 'bearer',
        expiresAt: Date.now() - 1000,
      }
      mockSessionStorage['batchivo_auth_tokens'] = JSON.stringify(oldTokens)

      mockFetch.mockResolvedValueOnce({ ok: false })

      const result = await refreshAccessToken()

      expect(result).toBeNull()
      expect(sessionStorageMock.removeItem).toHaveBeenCalled()
    })
  })

  describe('requestPasswordReset', () => {
    it('sends password reset request', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true })

      await requestPasswordReset('user@example.com')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/forgot-password',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ email: 'user@example.com' }),
        })
      )
    })

    it('throws on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'User not found' }),
      })

      await expect(requestPasswordReset('unknown@example.com'))
        .rejects.toThrow('User not found')
    })
  })

  describe('resetPassword', () => {
    it('sends reset password request', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true })

      await resetPassword('reset-token-123', 'newpassword')

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/reset-password',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            token: 'reset-token-123',
            new_password: 'newpassword',
          }),
        })
      )
    })

    it('throws on invalid token', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Invalid or expired token' }),
      })

      await expect(resetPassword('bad-token', 'newpassword'))
        .rejects.toThrow('Invalid or expired token')
    })
  })
})
