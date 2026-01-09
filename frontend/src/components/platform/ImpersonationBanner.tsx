/**
 * Impersonation Banner
 *
 * Displayed when a platform admin is impersonating a tenant.
 * Shows which tenant is being impersonated and provides a way to stop.
 */

import { useImpersonation } from '@/hooks/useImpersonation'
import { Button } from '@/components/ui/button'
import { AlertTriangle, X } from 'lucide-react'

export function ImpersonationBanner() {
  const { isImpersonating, impersonatedTenantName, stopImpersonation, isLoading } = useImpersonation()

  if (!isImpersonating) {
    return null
  }

  const handleStopImpersonation = async () => {
    try {
      await stopImpersonation()
    } catch (error) {
      console.error('Failed to stop impersonation:', error)
    }
  }

  return (
    <div className="bg-amber-500 text-amber-950 px-4 py-2">
      <div className="container mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span className="text-sm font-medium">
            You are impersonating:{' '}
            <strong>{impersonatedTenantName || 'Unknown Tenant'}</strong>
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleStopImpersonation}
          disabled={isLoading}
          className="bg-amber-600 border-amber-700 text-amber-950 hover:bg-amber-700"
        >
          <X className="h-4 w-4 mr-1" />
          Stop Impersonating
        </Button>
      </div>
    </div>
  )
}
