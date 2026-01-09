/**
 * Authentication utilities and types for JWT-based auth
 */

// API base URL - matches api.ts pattern
const API_BASE_URL = import.meta.env.VITE_API_URL || ''
const API_V1_PREFIX = '/api/v1'
const TOKEN_STORAGE_KEY = 'nozzly_auth_tokens'
const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000 // 5 minutes

export interface User {
  id: string
  email: string
  name: string
  tenant_id: string
  tenant_name: string
  is_platform_admin: boolean
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresAt: number
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  full_name?: string
  tenant_name?: string
}

/**
 * Register a new user
 */
export async function register(data: RegisterData): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE_URL}${API_V1_PREFIX}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Registration failed')
  }

  const tokens = await response.json()
  const authTokens = normalizeTokens(tokens)
  setAuthTokens(authTokens)
  return authTokens
}

/**
 * Login with email and password
 */
export async function login(credentials: LoginCredentials): Promise<AuthTokens> {
  const response = await fetch(`${API_BASE_URL}${API_V1_PREFIX}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Login failed')
  }

  const tokens = await response.json()
  const authTokens = normalizeTokens(tokens)
  setAuthTokens(authTokens)
  return authTokens
}

/**
 * Logout current user
 */
export async function logout(): Promise<void> {
  try {
    const tokens = getAuthTokens()
    if (tokens) {
      await fetch(`${API_BASE_URL}${API_V1_PREFIX}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.accessToken}`,
        },
      })
    }
  } catch (error) {
    console.error('Logout error:', error)
  } finally {
    clearAuthTokens()
  }
}

/**
 * Refresh access token using refresh token
 */
export async function refreshAccessToken(): Promise<AuthTokens | null> {
  const tokens = getAuthTokens()
  if (!tokens || !tokens.refreshToken) {
    return null
  }

  try {
    const response = await fetch(`${API_BASE_URL}${API_V1_PREFIX}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: tokens.refreshToken,
      }),
    })

    if (!response.ok) {
      clearAuthTokens()
      return null
    }

    const newTokens = await response.json()
    const authTokens = normalizeTokens(newTokens)
    setAuthTokens(authTokens)
    return authTokens
  } catch (error) {
    console.error('Token refresh error:', error)
    clearAuthTokens()
    return null
  }
}

/** Raw token response from API */
interface TokenApiResponse {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
}

/**
 * Normalize token response to AuthTokens format
 */
function normalizeTokens(tokens: TokenApiResponse): AuthTokens {
  // Calculate expiration time (default to 30 minutes if not provided)
  const expiresIn = tokens.expires_in || 1800 // 30 minutes in seconds
  const expiresAt = Date.now() + (expiresIn * 1000)

  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    tokenType: tokens.token_type || 'bearer',
    expiresAt,
  }
}

/**
 * Store auth tokens in sessionStorage (survives page refresh, cleared on tab close)
 */
export function setAuthTokens(tokens: AuthTokens): void {
  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens))
  } catch (error) {
    console.error('Failed to store auth tokens:', error)
  }
}

/**
 * Get auth tokens from sessionStorage
 * Note: This is synchronous. Token refresh happens in axios interceptor.
 */
export function getAuthTokens(): AuthTokens | null {
  try {
    const stored = sessionStorage.getItem(TOKEN_STORAGE_KEY)
    if (!stored) return null

    const tokens: AuthTokens = JSON.parse(stored)
    return tokens
  } catch (error) {
    console.error('Failed to retrieve auth tokens:', error)
    return null
  }
}

/**
 * Clear auth tokens from sessionStorage
 */
export function clearAuthTokens(): void {
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch (error) {
    console.error('Failed to clear auth tokens:', error)
  }
}

/**
 * Check if access token is expired
 */
export function isTokenExpired(tokens: AuthTokens | null): boolean {
  if (!tokens) return true
  return tokens.expiresAt <= Date.now()
}

/**
 * Check if access token is about to expire (within threshold)
 */
export function isTokenExpiringSoon(tokens: AuthTokens | null): boolean {
  if (!tokens) return true
  return tokens.expiresAt - Date.now() < TOKEN_REFRESH_THRESHOLD
}

/**
 * Get authorization header with current access token
 */
export function getAuthHeader(): string | null {
  const tokens = getAuthTokens()
  if (!tokens) return null
  return `${tokens.tokenType} ${tokens.accessToken}`
}

/**
 * Create an authenticated fetch wrapper
 */
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const tokens = getAuthTokens()

  if (!tokens) {
    throw new Error('Not authenticated')
  }

  // Refresh token if expired
  if (isTokenExpired(tokens)) {
    const refreshed = await refreshAccessToken()
    if (!refreshed) {
      throw new Error('Session expired')
    }
  }

  const headers = new Headers(options.headers)
  headers.set('Authorization', getAuthHeader() || '')

  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Request a password reset email
 */
export async function requestPasswordReset(email: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${API_V1_PREFIX}/auth/forgot-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to request password reset')
  }
}

/**
 * Reset password with token
 */
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${API_V1_PREFIX}/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to reset password')
  }
}
