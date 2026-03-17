/**
 * PrinterCard — live status card for a single printer.
 *
 * Shows:
 * - Name + status badge in header
 * - Job name + progress bar + ETA (printing/paused only)
 * - AMS slot row (Bambu only: has_ams=true)
 * - Toolhead badge (U1 only: has_toolhead_changer=true)
 * - Action strip: Pause | FilamentChange | Details (only Details wired in Sprint 1)
 * - Overflow '…' menu with Cancel (requires confirm dialog)
 */

import { useState } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Pause, Droplets, Info, MoreHorizontal, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PrinterStatusBadge } from './PrinterStatusBadge'
import { AMSSlotIndicator } from './AMSSlotIndicator'
import { ToolheadBadge } from './ToolheadBadge'
import type { PrinterLiveState, PrinterModelInfo } from '@/types/printer'
import { useNavigate } from '@tanstack/react-router'

const PROGRESS_COLOUR: Record<string, string> = {
  printing: 'bg-blue-500',
  paused:   'bg-amber-500',
  error:    'bg-red-500',
}

function formatEta(seconds: number | null | undefined): string | null {
  if (!seconds || seconds <= 0) return null
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

interface PrinterCardProps {
  printer: PrinterLiveState
  modelInfo?: PrinterModelInfo | null
  printerId: string
}

export function PrinterCard({ printer, modelInfo }: PrinterCardProps) {
  const navigate = useNavigate()
  const [cancelOpen, setCancelOpen] = useState(false)

  const isActive = printer.status === 'printing' || printer.status === 'paused'
  const showAms = modelInfo?.has_ams && printer.ams_slots.length > 0
  const showToolhead = modelInfo?.has_toolhead_changer

  const progressColour = PROGRESS_COLOUR[printer.status] ?? 'bg-muted'
  const progress = printer.progress_percent ?? 0
  const etaStr = formatEta(printer.eta_seconds)

  const isOffline = printer.status === 'offline'

  return (
    <TooltipProvider>
      <Card className={cn('flex flex-col', isOffline && 'opacity-60')}>
        {/* Header */}
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <span className="font-semibold text-sm leading-tight truncate pr-2">
            {printer.name}
          </span>
          <PrinterStatusBadge status={printer.status} />
        </CardHeader>

        <CardContent className="flex flex-col gap-3 pt-0 flex-1">
          {/* Job info — only shown when printing or paused */}
          {isActive && (
            <div className="space-y-1.5">
              {printer.job_name && (
                <p className="text-xs text-muted-foreground truncate" title={printer.job_name}>
                  {printer.job_name}
                </p>
              )}
              {/* Progress bar */}
              <div className="flex items-center gap-2">
                <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                  <div
                    className={cn('h-full rounded-full transition-all', progressColour)}
                    style={{ width: `${Math.min(100, progress)}%` }}
                  />
                </div>
                <span className="text-xs tabular-nums text-muted-foreground w-10 text-right">
                  {progress.toFixed(0)}%
                </span>
              </div>
              {etaStr && (
                <p className="text-xs text-muted-foreground text-right">
                  ETA: {etaStr}
                </p>
              )}
            </div>
          )}

          {/* Last seen for offline printers */}
          {isOffline && printer.last_seen_at && (
            <p className="text-xs text-muted-foreground">
              Last seen: {new Date(printer.last_seen_at).toLocaleString()}
            </p>
          )}

          {/* AMS slots */}
          {showAms && (
            <AMSSlotIndicator slots={printer.ams_slots} />
          )}

          {/* Toolhead badges */}
          {showToolhead && (
            <ToolheadBadge activeToolhead={printer.active_toolhead} />
          )}

          {/* Action strip */}
          <div className="flex items-center justify-between pt-1 mt-auto">
            <div className="flex items-center gap-1">
              {/* Pause — disabled in Sprint 1 */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" disabled className="h-8 w-8 p-0">
                    <Pause className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Coming soon</TooltipContent>
              </Tooltip>

              {/* Filament change — disabled in Sprint 1 */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="sm" disabled className="h-8 w-8 p-0">
                    <Droplets className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Coming soon</TooltipContent>
              </Tooltip>

              {/* Details — wired */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => navigate({ to: '/printers' })}
                  >
                    <Info className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>View details</TooltipContent>
              </Tooltip>
            </div>

            {/* Overflow menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                  <span className="sr-only">More actions</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => setCancelOpen(true)}
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  Cancel print
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>

      {/* Cancel confirmation dialog */}
      <AlertDialog open={cancelOpen} onOpenChange={setCancelOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel print?</AlertDialogTitle>
            <AlertDialogDescription>
              This will stop the current print on <strong>{printer.name}</strong>. This action cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep printing</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive hover:bg-destructive/90"
              onClick={() => {
                // Sprint 1: cancel not yet wired to API
                setCancelOpen(false)
              }}
            >
              Cancel print
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </TooltipProvider>
  )
}
