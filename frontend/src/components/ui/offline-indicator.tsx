/**
 * Offline Status Indicator
 *
 * Shows network status and pending sync count to users.
 * Provides feedback about offline mode and data synchronization.
 */

import { WifiOff, CloudOff, RefreshCw, Check } from 'lucide-react'
import { useOfflineIndicator } from '@/hooks/useOfflineSpools'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface OfflineIndicatorProps {
  className?: string
  showLabel?: boolean
  onSync?: () => void
  isSyncing?: boolean
}

export function OfflineIndicator({
  className,
  showLabel = false,
  onSync,
  isSyncing = false,
}: OfflineIndicatorProps) {
  const { isOnline, pendingCount, hasPendingChanges } = useOfflineIndicator()

  // Don't show anything if online with no pending changes
  if (isOnline && !hasPendingChanges) {
    return null
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {!isOnline && (
        <Badge
          variant="secondary"
          className="gap-1.5 bg-amber-500/10 text-amber-600 border-amber-200"
          title="You're offline. Changes will sync when you reconnect."
        >
          <WifiOff className="h-3 w-3" />
          {showLabel && 'Offline'}
        </Badge>
      )}

      {hasPendingChanges && (
        <Badge
          variant="outline"
          className="gap-1.5"
          title={`${pendingCount} change${pendingCount !== 1 ? 's' : ''} waiting to sync`}
        >
          <CloudOff className="h-3 w-3" />
          {pendingCount} pending
        </Badge>
      )}

      {isOnline && hasPendingChanges && onSync && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onSync}
          disabled={isSyncing}
          className="h-7 px-2"
          title="Sync pending changes"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isSyncing && 'animate-spin')} />
        </Button>
      )}
    </div>
  )
}

/**
 * Compact version for status bars or headers
 */
export function OfflineStatusBadge({ className }: { className?: string }) {
  const { isOnline, hasPendingChanges, pendingCount } = useOfflineIndicator()

  if (isOnline && !hasPendingChanges) {
    return null
  }

  if (!isOnline) {
    return (
      <Badge variant="secondary" className={cn('gap-1 bg-amber-500/10 text-amber-600', className)}>
        <WifiOff className="h-3 w-3" />
        Offline
      </Badge>
    )
  }

  return (
    <Badge variant="outline" className={cn('gap-1', className)}>
      <CloudOff className="h-3 w-3" />
      {pendingCount} pending
    </Badge>
  )
}

/**
 * Full-width banner for offline mode
 */
export function OfflineBanner({
  className,
  onSync,
  isSyncing,
}: {
  className?: string
  onSync?: () => void
  isSyncing?: boolean
}) {
  const { isOnline, hasPendingChanges, pendingCount } = useOfflineIndicator()

  if (isOnline && !hasPendingChanges) {
    return null
  }

  return (
    <div
      className={cn(
        'flex items-center justify-between px-4 py-2 text-sm',
        !isOnline
          ? 'bg-amber-50 border-b border-amber-200 text-amber-800'
          : 'bg-blue-50 border-b border-blue-200 text-blue-800',
        className
      )}
    >
      <div className="flex items-center gap-2">
        {!isOnline ? (
          <>
            <WifiOff className="h-4 w-4" />
            <span>You're offline. Changes will be saved locally and synced when you reconnect.</span>
          </>
        ) : (
          <>
            <CloudOff className="h-4 w-4" />
            <span>{pendingCount} change{pendingCount !== 1 ? 's' : ''} waiting to sync.</span>
          </>
        )}
      </div>

      {isOnline && onSync && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onSync}
          disabled={isSyncing}
          className="h-7"
        >
          {isSyncing ? (
            <>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              Syncing...
            </>
          ) : (
            <>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Sync now
            </>
          )}
        </Button>
      )}
    </div>
  )
}

/**
 * Sync success toast content
 */
export function SyncSuccessContent() {
  return (
    <div className="flex items-center gap-2">
      <Check className="h-4 w-4 text-green-500" />
      <span>Changes synced successfully</span>
    </div>
  )
}
