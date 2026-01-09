/**
 * Module Guard Component
 *
 * Protects routes that belong to tenant-specific modules.
 * Shows 404 if the current tenant doesn't have access to the module.
 */

import { useLocation } from '@tanstack/react-router'
import { useRouteAccess } from '@/hooks/useModules'
import { NotFound } from '@/pages/NotFound'
import { Loader2 } from 'lucide-react'

interface ModuleGuardProps {
  children: React.ReactNode
  /**
   * Optional: Override the path to check.
   * If not provided, uses current location.
   */
  path?: string
}

export function ModuleGuard({ children, path: pathOverride }: ModuleGuardProps) {
  const location = useLocation()
  const currentPath = pathOverride || location.pathname
  const { isAllowed, isLoading } = useRouteAccess(currentPath)

  // Show loading spinner while checking access
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  // Show 404 if not allowed
  if (!isAllowed) {
    return (
      <NotFound
        title="Module Not Available"
        message="This feature is not available for your account type. Please contact support if you believe this is an error."
        showLayout={true}
      />
    )
  }

  return <>{children}</>
}
