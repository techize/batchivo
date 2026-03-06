/**
 * PrinterFleetSummary — 4 stat cards showing Printing/Idle/Error/Offline counts.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Printer as PrinterIcon, Play, AlertCircle, WifiOff } from 'lucide-react'
import type { PrinterLiveState } from '@/types/printer'

function StatCard({
  title,
  value,
  icon,
  colorClass,
}: {
  title: string
  value: number
  icon: React.ReactNode
  colorClass: string
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`rounded-md p-2 ${colorClass}`}>{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}

interface PrinterFleetSummaryProps {
  printers: PrinterLiveState[]
}

export function PrinterFleetSummary({ printers }: PrinterFleetSummaryProps) {
  const printing = printers.filter((p) => p.status === 'printing' || p.status === 'paused').length
  const idle = printers.filter((p) => p.status === 'idle').length
  const error = printers.filter((p) => p.status === 'error').length
  const offline = printers.filter((p) => p.status === 'offline').length

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Printing"
        value={printing}
        icon={<Play className="h-4 w-4 text-blue-600" />}
        colorClass="bg-blue-100 dark:bg-blue-900/30"
      />
      <StatCard
        title="Idle"
        value={idle}
        icon={<PrinterIcon className="h-4 w-4 text-green-600" />}
        colorClass="bg-green-100 dark:bg-green-900/30"
      />
      <StatCard
        title="Error"
        value={error}
        icon={<AlertCircle className="h-4 w-4 text-red-600" />}
        colorClass="bg-red-100 dark:bg-red-900/30"
      />
      <StatCard
        title="Offline"
        value={offline}
        icon={<WifiOff className="h-4 w-4 text-gray-500" />}
        colorClass="bg-gray-100 dark:bg-gray-900/30"
      />
    </div>
  )
}
