/**
 * Impersonation Hook
 *
 * Manages impersonation state and token handling for platform admins.
 */

import { useState, useCallback, useEffect } from 'react'
import { setAuthTokens, getAuthTokens, type AuthTokens } from '@/lib/auth'
import { useImpersonateTenant } from './usePlatformAdmin'
import { useAuth } from '@/contexts/AuthContext'

const IMPERSONATION_KEY = 'nozzly_impersonation_state'
const ORIGINAL_TOKENS_KEY = 'nozzly_original_tokens'

interface ImpersonationState {
  isImpersonating: boolean
  originalTenantId: string | null
  originalTenantName: string | null
  impersonatedTenantId: string | null
  impersonatedTenantName: string | null
}

/**
 * Hook to manage impersonation state and actions
 */
export function useImpersonation() {
  const { refreshUser } = useAuth()
  const impersonateMutation = useImpersonateTenant()

  const [impersonationState, setImpersonationState] = useState<ImpersonationState>(() => {
    // Load initial state from sessionStorage
    try {
      const stored = sessionStorage.getItem(IMPERSONATION_KEY)
      if (stored) {
        return JSON.parse(stored)
      }
    } catch (e) {
      console.error('Failed to load impersonation state:', e)
    }
    return {
      isImpersonating: false,
      originalTenantId: null,
      originalTenantName: null,
      impersonatedTenantId: null,
      impersonatedTenantName: null,
    }
  })

  // Persist state to sessionStorage
  useEffect(() => {
    try {
      sessionStorage.setItem(IMPERSONATION_KEY, JSON.stringify(impersonationState))
    } catch (e) {
      console.error('Failed to save impersonation state:', e)
    }
  }, [impersonationState])

  /**
   * Start impersonating a tenant
   */
  const startImpersonation = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    async (tenantId: string, tenantName: string) => {
      // Save original tokens
      const originalTokens = getAuthTokens()
      if (!originalTokens) {
        throw new Error('Not authenticated')
      }

      try {
        // Store original tokens
        sessionStorage.setItem(ORIGINAL_TOKENS_KEY, JSON.stringify(originalTokens))

        // Get impersonation token
        const response = await impersonateMutation.mutateAsync(tenantId)

        // Set new tokens (expires in 1 hour for impersonation)
        const newTokens: AuthTokens = {
          accessToken: response.access_token,
          refreshToken: originalTokens.refreshToken, // Keep original refresh token
          tokenType: response.token_type,
          expiresAt: Date.now() + 60 * 60 * 1000, // 1 hour
        }
        setAuthTokens(newTokens)

        // Update impersonation state
        setImpersonationState({
          isImpersonating: true,
          originalTenantId: originalTokens.accessToken, // We don't have tenant ID from tokens, this is a placeholder
          originalTenantName: null, // Will be filled from user context
          impersonatedTenantId: response.tenant_id,
          impersonatedTenantName: response.tenant_name,
        })

        // Refresh user data to get new tenant context
        await refreshUser()

        return response
      } catch (error) {
        // Restore original tokens on error
        sessionStorage.removeItem(ORIGINAL_TOKENS_KEY)
        throw error
      }
    },
    [impersonateMutation, refreshUser]
  )

  /**
   * Stop impersonating and return to original tenant
   */
  const stopImpersonation = useCallback(async () => {
    try {
      // Restore original tokens
      const storedTokens = sessionStorage.getItem(ORIGINAL_TOKENS_KEY)
      if (storedTokens) {
        const originalTokens: AuthTokens = JSON.parse(storedTokens)
        setAuthTokens(originalTokens)
        sessionStorage.removeItem(ORIGINAL_TOKENS_KEY)
      }

      // Clear impersonation state
      setImpersonationState({
        isImpersonating: false,
        originalTenantId: null,
        originalTenantName: null,
        impersonatedTenantId: null,
        impersonatedTenantName: null,
      })

      // Refresh user data to get original tenant context
      await refreshUser()
    } catch (error) {
      console.error('Failed to stop impersonation:', error)
      throw error
    }
  }, [refreshUser])

  return {
    ...impersonationState,
    startImpersonation,
    stopImpersonation,
    isLoading: impersonateMutation.isPending,
    error: impersonateMutation.error,
  }
}
