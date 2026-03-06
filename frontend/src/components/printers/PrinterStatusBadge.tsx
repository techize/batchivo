/**
 * PrinterStatusBadge — coloured badge showing printer status.
 */

import { Badge } from '@/components/ui/badge'
import { StatusDot } from './StatusDot'
import type { PrinterStatus } from '@/types/printer'

const BADGE_CLASSES: Record<PrinterStatus, string> = {
  printing: 'bg-blue-500/10 text-blue-700 border-blue-200',
  paused:   'bg-amber-500/10 text-amber-600 border-amber-200',
  error:    'bg-red-500/10 text-red-600 border-red-200',
  idle:     'bg-green-500/10 text-green-600 border-green-200',
  offline:  'bg-gray-500/10 text-gray-500 border-gray-200',
}

const STATUS_LABELS: Record<PrinterStatus, string> = {
  printing: 'Printing',
  paused:   'Paused',
  error:    'Error',
  idle:     'Idle',
  offline:  'Offline',
}

interface PrinterStatusBadgeProps {
  status: PrinterStatus
}

export function PrinterStatusBadge({ status }: PrinterStatusBadgeProps) {
  return (
    <Badge variant="outline" className={BADGE_CLASSES[status]}>
      <StatusDot status={status} className="mr-1.5" />
      {STATUS_LABELS[status]}
    </Badge>
  )
}
