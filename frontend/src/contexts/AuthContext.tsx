/**
 * Authentication context provider
 * Manages user authentication state and provides auth methods
 */

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { AuthState } from '@/lib/auth'
import { getAuthTokens, clearAuthTokens, isTokenExpired } from '@/lib/auth'
import { api } from '@/lib/api'

interface AuthContextType extends AuthState {
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  })

  // Check for existing session on mount
  useEffect(() => {
    checkAuthStatus()
  }, [])

  /**
   * Check if user has valid auth tokens and fetch user info
   */
  async function checkAuthStatus() {
    try {
      const tokens = getAuthTokens()

      if (!tokens || isTokenExpired(tokens)) {
        setAuthState({ user: null, isAuthenticated: false, isLoading: false })
        return
      }

      // Fetch current user from backend using axios api (with interceptor)
      const response = await api.get('/api/v1/users/me')
      const data = response.data

      setAuthState({
        user: data,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      console.error('Failed to check auth status:', error)
      clearAuthTokens()
      setAuthState({ user: null, isAuthenticated: false, isLoading: false })
    }
  }

  /**
   * Logout user and clear tokens
   */
  async function logout() {
    try {
      // Call logout endpoint (server-side session cleanup)
      await api.post('/api/v1/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuthTokens()
      setAuthState({ user: null, isAuthenticated: false, isLoading: false })
      window.location.href = '/login'
    }
  }

  /**
   * Refresh user data from backend
   */
  async function refreshUser() {
    await checkAuthStatus()
  }

  const value: AuthContextType = {
    ...authState,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to access auth context
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
