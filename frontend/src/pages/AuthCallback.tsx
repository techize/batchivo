/**
 * Auth callback page - no longer needed with JWT auth
 * Redirects to login
 */

import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'

export function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    // Redirect to login since this page is no longer used
    navigate({ to: '/login' })
  }, [navigate])

  return null
}
