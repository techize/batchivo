/**
 * Platform Admin Guard
 *
 * Route guard that ensures only platform admins can access certain routes.
 * Redirects non-admins to the dashboard.
 */

import { ReactNode } from 'react'
import { Navigate } from '@tanstack/react-router'
import { useAuth } from '@/contexts/AuthContext'
import { Loader2, ShieldAlert } from 'lucide-react'

interface PlatformAdminGuardProps {
  children: ReactNode
}

export function PlatformAdminGuard({ children }: PlatformAdminGuardProps) {
  const { user, isLoading, isAuthenticated } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }

  if (!user?.is_platform_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <ShieldAlert className="w-16 h-16 mx-auto text-destructive" />
          <h1 className="text-2xl font-bold">Access Denied</h1>
          <p className="text-muted-foreground max-w-md">
            You do not have platform administrator access. Please contact support if you
            believe this is an error.
          </p>
          <a
            href="/dashboard"
            className="inline-block mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
