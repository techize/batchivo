/**
 * SpoolUsageHistory Component
 *
 * Displays production runs that used a specific spool with usage statistics
 * and remaining life estimation.
 */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { format, parseISO, subDays } from 'date-fns'
import {
  ArrowUpRight,
  Calendar,
  ChevronDown,
  ChevronUp,
  Loader2,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { listProductionRuns } from '@/lib/api/production-runs'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { ProductionRunDetail, ProductionRunMaterial } from '@/types/production-run'

interface SpoolUsageHistoryProps {
  spoolId: string
  currentWeight: number
  initialWeight: number
}

type DateRangeOption = '30d' | '90d' | 'all'

interface SpoolUsageRecord {
  run: ProductionRunDetail
  material: ProductionRunMaterial
}

export function SpoolUsageHistory({
  spoolId,
  currentWeight,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  initialWeight,
}: SpoolUsageHistoryProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [dateRange, setDateRange] = useState<DateRangeOption>('90d')

  // Fetch production runs
  const { data, isLoading, error } = useQuery({
    queryKey: ['production-runs-for-spool', spoolId, dateRange],
    queryFn: () => {
      const startDate =
        dateRange === 'all'
          ? undefined
          : format(subDays(new Date(), parseInt(dateRange)), 'yyyy-MM-dd')
      return listProductionRuns({
        start_date: startDate,
        limit: 500,
      })
    },
    enabled: isOpen,
  })

  // Filter runs that used this spool
  const spoolUsage = useMemo<SpoolUsageRecord[]>(() => {
    if (!data?.runs) return []

    const records: SpoolUsageRecord[] = []

    data.runs.forEach((run) => {
      const runDetail = run as ProductionRunDetail
      const material = runDetail.materials?.find((m) => m.spool_id === spoolId)
      if (material) {
        records.push({ run: runDetail, material })
      }
    })

    return records.sort(
      (a, b) => new Date(b.run.started_at).getTime() - new Date(a.run.started_at).getTime()
    )
  }, [data?.runs, spoolId])

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (spoolUsage.length === 0) {
      return {
        totalRuns: 0,
        totalEstimatedUsage: 0,
        totalActualUsage: 0,
        averageVariance: 0,
        averageUsagePerRun: 0,
        estimatedRunsRemaining: null as number | null,
      }
    }

    const totalRuns = spoolUsage.length
    const totalEstimatedUsage = spoolUsage.reduce(
      (sum, { material }) => sum + material.estimated_total_weight,
      0
    )
    const totalActualUsage = spoolUsage.reduce(
      (sum, { material }) => sum + material.actual_total_weight,
      0
    )
    const averageVariance =
      spoolUsage.reduce((sum, { material }) => sum + material.variance_percentage, 0) / totalRuns
    const averageUsagePerRun = totalActualUsage / totalRuns

    // Estimate remaining runs based on average usage
    const estimatedRunsRemaining =
      averageUsagePerRun > 0 ? Math.floor(currentWeight / averageUsagePerRun) : null

    return {
      totalRuns,
      totalEstimatedUsage,
      totalActualUsage,
      averageVariance,
      averageUsagePerRun,
      estimatedRunsRemaining,
    }
  }, [spoolUsage, currentWeight])

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" className="w-full justify-between h-auto py-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Production Usage
            </span>
            {spoolUsage.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {spoolUsage.length} runs
              </Badge>
            )}
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="space-y-4 pt-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">Loading usage history...</span>
          </div>
        ) : error ? (
          <div className="text-center py-4 text-sm text-destructive">
            Error loading usage history
          </div>
        ) : (
          <>
            {/* Date filter */}
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <Select value={dateRange} onValueChange={(v) => setDateRange(v as DateRangeOption)}>
                <SelectTrigger className="w-[140px] h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="90d">Last 90 days</SelectItem>
                  <SelectItem value="all">All time</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Summary stats */}
            {summaryStats.totalRuns > 0 && (
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="bg-muted/50 rounded-md p-2 text-center">
                  <p className="text-xs text-muted-foreground">Total Used</p>
                  <p className="font-semibold">{summaryStats.totalActualUsage.toFixed(0)}g</p>
                </div>
                <div className="bg-muted/50 rounded-md p-2 text-center">
                  <p className="text-xs text-muted-foreground">Avg/Run</p>
                  <p className="font-semibold">{summaryStats.averageUsagePerRun.toFixed(0)}g</p>
                </div>
                <div className="bg-muted/50 rounded-md p-2 text-center">
                  <p className="text-xs text-muted-foreground">Est. Runs Left</p>
                  <p className="font-semibold">
                    {summaryStats.estimatedRunsRemaining !== null
                      ? `~${summaryStats.estimatedRunsRemaining}`
                      : '—'}
                  </p>
                </div>
              </div>
            )}

            {/* Usage table */}
            {spoolUsage.length === 0 ? (
              <div className="text-center py-4 text-sm text-muted-foreground">
                No production runs found using this spool
              </div>
            ) : (
              <div className="rounded-md border max-h-[300px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Run</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-right">Est.</TableHead>
                      <TableHead className="text-right">Actual</TableHead>
                      <TableHead className="text-right">Var.</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {spoolUsage.map(({ run, material }) => (
                      <TableRow key={run.id}>
                        <TableCell className="font-mono text-sm">
                          <Link
                            to="/production-runs/$runId"
                            params={{ runId: run.id }}
                            className="hover:underline flex items-center gap-1"
                          >
                            {run.run_number}
                            <ArrowUpRight className="h-3 w-3" />
                          </Link>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {format(parseISO(run.started_at), 'MMM d')}
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          {material.estimated_total_weight.toFixed(0)}g
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          {material.actual_total_weight.toFixed(0)}g
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          <span
                            className={`flex items-center justify-end gap-1 ${
                              material.variance_percentage > 0
                                ? 'text-red-600'
                                : material.variance_percentage < 0
                                ? 'text-green-600'
                                : ''
                            }`}
                          >
                            {material.variance_percentage > 0 ? (
                              <TrendingUp className="h-3 w-3" />
                            ) : material.variance_percentage < 0 ? (
                              <TrendingDown className="h-3 w-3" />
                            ) : null}
                            {material.variance_percentage > 0 ? '+' : ''}
                            {material.variance_percentage.toFixed(0)}%
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
