/**
 * PrinterDashboard — live fleet monitoring page.
 *
 * Features:
 * - Fleet summary: 4 stat cards (Printing/Idle/Error/Offline)
 * - Grid view with cards grouped by status (Printing→Paused→Error→Idle→Offline)
 * - Table view toggle (reuses existing PrinterList)
 * - WebSocket for live updates, REST fallback at 15 s
 * - View toggle persisted to localStorage
 */

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LayoutGrid, List, Printer as PrinterIcon, WifiOff, Plus } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { listPrinters, listPrinterModels } from '@/lib/api/printers'
import { usePrinterWebSocket } from '@/hooks/usePrinterWebSocket'
import { PrinterFleetSummary } from './PrinterFleetSummary'
import { PrinterStatusGroup } from './PrinterStatusGroup'
import { PrinterCardSkeleton } from './PrinterCardSkeleton'
import { PrinterList } from './PrinterList'
import type { PrinterLiveState, PrinterModelInfo } from '@/types/printer'

const VIEW_STORAGE_KEY = 'batchivo_printer_view'
const STATUS_ORDER: Array<PrinterLiveState['status']> = [
  'printing',
  'paused',
  'error',
  'idle',
  'offline',
]
const GROUP_TITLES: Record<string, string> = {
  printing: 'Printing',
  paused:   'Paused',
  error:    'Error',
  idle:     'Idle',
  offline:  'Offline',
}

function useViewToggle() {
  const [view, setView] = useState<'grid' | 'table'>(() => {
    try { return (localStorage.getItem(VIEW_STORAGE_KEY) as 'grid' | 'table') || 'grid' }
    catch { return 'grid' }
  })
  const toggle = (v: 'grid' | 'table') => {
    setView(v)
    try { localStorage.setItem(VIEW_STORAGE_KEY, v) } catch { /* ignore storage errors */ }
  }
  return { view, toggle }
}

export function PrinterDashboard() {
  const { view, toggle } = useViewToggle()

  // Live state from WebSocket
  const { printers: wsPrinters, connected: wsConnected } = usePrinterWebSocket()

  // REST fallback — polls every 15 s; also provides printer IDs + model list
  const { data: restData, isLoading } = useQuery({
    queryKey: ['printers', 'all'],
    queryFn: () => listPrinters({ is_active: true, limit: 200 }),
    refetchInterval: 15_000,
  })

  const { data: modelList = [] } = useQuery({
    queryKey: ['printer-models'],
    queryFn: listPrinterModels,
    staleTime: Infinity,
  })

  // Build lookup: model_key → PrinterModelInfo
  const modelInfoMap = useMemo<Record<string, PrinterModelInfo>>(() => {
    return Object.fromEntries(modelList.map((m) => [m.model_key, m]))
  }, [modelList])

  // Use WS state when connected; convert REST printers to live state shape as fallback
  const restPrinters = useMemo(() => restData?.printers ?? [], [restData?.printers])
  const liveStates: PrinterLiveState[] = useMemo(() => {
    if (wsPrinters.length > 0) return wsPrinters
    // Fallback: construct minimal live state from REST data
    return restPrinters.map((p) => ({
      id: p.id,
      name: p.name,
      model: p.model,
      status: 'offline' as const,
      job_name: null,
      progress_percent: null,
      eta_seconds: null,
      last_seen_at: null,
      ams_slots: [],
      active_toolhead: null,
    }))
  }, [wsPrinters, restPrinters])

  // Build id-index: printer.id → printer.id (for navigation)
  const printerIds = useMemo<Record<string, string>>(() => {
    return Object.fromEntries(restPrinters.map((p) => [p.id, p.id]))
  }, [restPrinters])

  // Group live states by status
  const grouped = useMemo(() => {
    const map: Record<string, PrinterLiveState[]> = {}
    for (const s of STATUS_ORDER) map[s] = []
    for (const p of liveStates) {
      const bucket = map[p.status] ?? (map[p.status] = [])
      bucket.push(p)
    }
    return map
  }, [liveStates])

  const allOffline =
    liveStates.length > 0 && liveStates.every((p) => p.status === 'offline')

  // Loading skeleton
  if (isLoading && liveStates.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Printer Dashboard</h1>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <PrinterCardSkeleton key={i} />
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <PrinterCardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  // Empty state
  if (!isLoading && liveStates.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Printer Dashboard</h1>
        </div>
        <div className="flex h-64 flex-col items-center justify-center text-center gap-4">
          <PrinterIcon className="h-16 w-16 text-muted-foreground/30" />
          <div>
            <p className="text-lg font-semibold">No printers yet</p>
            <p className="text-muted-foreground mt-1">Add your first printer to start monitoring your fleet.</p>
          </div>
          <Button asChild>
            <Link to="/printers">
              <Plus className="mr-2 h-4 w-4" />
              Add your first printer
            </Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Printer Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            {liveStates.length} printer{liveStates.length !== 1 ? 's' : ''}{' '}
            {wsConnected ? '· Live' : '· Polling'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={view === 'grid' ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggle('grid')}
          >
            <LayoutGrid className="h-4 w-4" />
            <span className="ml-2 hidden sm:inline">Grid</span>
          </Button>
          <Button
            variant={view === 'table' ? 'default' : 'outline'}
            size="sm"
            onClick={() => toggle('table')}
          >
            <List className="h-4 w-4" />
            <span className="ml-2 hidden sm:inline">Table</span>
          </Button>
        </div>
      </div>

      {/* All-offline banner */}
      {allOffline && (
        <Alert className="border-amber-200 bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:border-amber-800 dark:text-amber-200">
          <WifiOff className="h-4 w-4" />
          <AlertDescription>
            All printers are currently offline. Check your network connections.
          </AlertDescription>
        </Alert>
      )}

      {/* Fleet summary */}
      <PrinterFleetSummary printers={liveStates} />

      {/* Grid view */}
      {view === 'grid' && (
        <div className="space-y-8">
          {STATUS_ORDER.map((status) => (
            <PrinterStatusGroup
              key={status}
              title={GROUP_TITLES[status]}
              groupKey={status}
              printers={grouped[status] ?? []}
              printerIds={printerIds}
              modelInfoMap={modelInfoMap}
              collapsible={status !== 'printing'}
            />
          ))}
        </div>
      )}

      {/* Table view */}
      {view === 'table' && <PrinterList />}
    </div>
  )
}
