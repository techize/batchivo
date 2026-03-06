/**
 * StatusDot — animated dot indicating printer status.
 */

import { cn } from '@/lib/utils'
import type { PrinterStatus } from '@/types/printer'

const DOT_CLASSES: Record<PrinterStatus, string> = {
  printing: 'bg-blue-500 animate-pulse',
  paused:   'bg-amber-500',
  error:    'bg-red-500',
  idle:     'bg-green-500',
  offline:  'bg-gray-400',
}

interface StatusDotProps {
  status: PrinterStatus
  className?: string
}

export function StatusDot({ status, className }: StatusDotProps) {
  return (
    <span
      className={cn('inline-block h-2 w-2 rounded-full', DOT_CLASSES[status], className)}
      aria-hidden="true"
    />
  )
}
