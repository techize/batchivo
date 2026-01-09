/**
 * ProductionHistoryTable Component
 *
 * Displays production runs that include models from a specific product.
 * Shows run details, success rates, and cost variance.
 */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { format, parseISO, subDays } from 'date-fns'
import {
  ArrowUpRight,
  Calendar,
  CheckCircle,
  Clock,
  Loader2,
  TrendingDown,
  TrendingUp,
  XCircle,
} from 'lucide-react'
import { listProductionRuns, formatStatus, formatDuration } from '@/lib/api/production-runs'
import { formatCurrency } from '@/lib/api/products'
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
import type { ProductionRunDetail, ProductionRunStatus } from '@/types/production-run'

interface ProductionHistoryTableProps {
  productId: string
  modelIds: string[]
}

type DateRangeOption = '7d' | '30d' | '90d' | 'all'

interface ProductRunSummary {
  run: ProductionRunDetail
  itemQuantity: number
  successfulQuantity: number
  failedQuantity: number
  successRate: number
  estimatedCost: number
  actualCost: number
}

function getStatusBadgeVariant(status: ProductionRunStatus) {
  switch (status) {
    case 'completed':
      return 'success'
    case 'in_progress':
      return 'default'
    case 'failed':
      return 'destructive'
    case 'cancelled':
      return 'secondary'
    default:
      return 'secondary'
  }
}

function getStatusIcon(status: ProductionRunStatus) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-3 w-3" />
    case 'in_progress':
      return <Clock className="h-3 w-3" />
    case 'failed':
    case 'cancelled':
      return <XCircle className="h-3 w-3" />
    default:
      return null
  }
}

export function ProductionHistoryTable({ productId, modelIds }: ProductionHistoryTableProps) {
  const [dateRange, setDateRange] = useState<DateRangeOption>('30d')
  const [statusFilter, setStatusFilter] = useState<ProductionRunStatus | 'all'>('all')

  // Fetch all production runs (we filter client-side by model)
  const { data, isLoading, error } = useQuery({
    queryKey: ['production-runs-for-product', productId, dateRange],
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
  })

  // Filter and summarize runs containing this product's models
  const productRuns = useMemo<ProductRunSummary[]>(() => {
    if (!data?.runs || modelIds.length === 0) return []

    const modelIdSet = new Set(modelIds)

    return data.runs
      .filter((run) => {
        // Check if run has any items for this product's models
        const hasProductItems = (run as ProductionRunDetail).items?.some(
          (item) => item.model_id && modelIdSet.has(item.model_id)
        )
        // Apply status filter
        if (statusFilter !== 'all' && run.status !== statusFilter) {
          return false
        }
        return hasProductItems
      })
      .map((run) => {
        const runDetail = run as ProductionRunDetail
        // Get items for this product's models
        const productItems =
          runDetail.items?.filter((item) => item.model_id && modelIdSet.has(item.model_id)) || []

        const itemQuantity = productItems.reduce((sum, item) => sum + item.quantity, 0)
        const successfulQuantity = productItems.reduce(
          (sum, item) => sum + item.successful_quantity,
          0
        )
        const failedQuantity = productItems.reduce((sum, item) => sum + item.failed_quantity, 0)
        const successRate =
          itemQuantity > 0 ? (successfulQuantity / itemQuantity) * 100 : 0

        const estimatedCost = productItems.reduce(
          (sum, item) => sum + (item.estimated_total_cost || 0),
          0
        )

        // Calculate actual cost based on success rate and variance
        const varianceMultiplier = 1 + (runDetail.variance_percentage || 0) / 100
        const actualCost = estimatedCost * varianceMultiplier * (successRate / 100)

        return {
          run: runDetail,
          itemQuantity,
          successfulQuantity,
          failedQuantity,
          successRate,
          estimatedCost,
          actualCost,
        }
      })
      .sort((a, b) => new Date(b.run.started_at).getTime() - new Date(a.run.started_at).getTime())
  }, [data?.runs, modelIds, statusFilter])

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (productRuns.length === 0) {
      return {
        totalRuns: 0,
        totalQuantity: 0,
        averageSuccessRate: 0,
        totalEstimatedCost: 0,
        totalActualCost: 0,
        costVariance: 0,
      }
    }

    const totalRuns = productRuns.length
    const totalQuantity = productRuns.reduce((sum, pr) => sum + pr.itemQuantity, 0)
    const totalSuccessful = productRuns.reduce((sum, pr) => sum + pr.successfulQuantity, 0)
    const averageSuccessRate = totalQuantity > 0 ? (totalSuccessful / totalQuantity) * 100 : 0
    const totalEstimatedCost = productRuns.reduce((sum, pr) => sum + pr.estimatedCost, 0)
    const totalActualCost = productRuns.reduce((sum, pr) => sum + pr.actualCost, 0)
    const costVariance =
      totalEstimatedCost > 0
        ? ((totalActualCost - totalEstimatedCost) / totalEstimatedCost) * 100
        : 0

    return {
      totalRuns,
      totalQuantity,
      averageSuccessRate,
      totalEstimatedCost,
      totalActualCost,
      costVariance,
    }
  }, [productRuns])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading production history...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading production history</p>
        <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex gap-2">
          <Select value={dateRange} onValueChange={(v) => setDateRange(v as DateRangeOption)}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="all">All time</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as ProductionRunStatus | 'all')}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Summary stats */}
        <div className="flex gap-4 text-sm">
          <div className="text-center">
            <p className="text-muted-foreground">Runs</p>
            <p className="font-semibold">{summaryStats.totalRuns}</p>
          </div>
          <div className="text-center">
            <p className="text-muted-foreground">Units</p>
            <p className="font-semibold">{summaryStats.totalQuantity}</p>
          </div>
          <div className="text-center">
            <p className="text-muted-foreground">Success Rate</p>
            <p
              className={`font-semibold ${
                summaryStats.averageSuccessRate >= 90
                  ? 'text-green-600'
                  : summaryStats.averageSuccessRate >= 70
                  ? 'text-amber-600'
                  : 'text-red-600'
              }`}
            >
              {summaryStats.averageSuccessRate.toFixed(0)}%
            </p>
          </div>
          <div className="text-center">
            <p className="text-muted-foreground">Cost Variance</p>
            <p
              className={`font-semibold flex items-center gap-1 ${
                summaryStats.costVariance > 0 ? 'text-red-600' : 'text-green-600'
              }`}
            >
              {summaryStats.costVariance > 0 ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {summaryStats.costVariance > 0 ? '+' : ''}
              {summaryStats.costVariance.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* Table */}
      {productRuns.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-lg font-medium">No production runs found</p>
          <p className="text-sm mt-2">
            {modelIds.length === 0
              ? 'This product has no models assigned'
              : 'No production runs include this product yet'}
          </p>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run #</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Success</TableHead>
                <TableHead className="text-right">Est. Cost</TableHead>
                <TableHead className="text-right">Variance</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {productRuns.map(({ run, itemQuantity, successRate, estimatedCost }) => (
                <TableRow key={run.id}>
                  <TableCell className="font-mono font-medium">
                    <Link
                      to="/production-runs/$runId"
                      params={{ runId: run.id }}
                      className="hover:underline"
                    >
                      {run.run_number}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="text-sm">
                        {format(parseISO(run.started_at), 'MMM d, yyyy')}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {run.duration_hours ? formatDuration(run.duration_hours) : '—'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={getStatusBadgeVariant(run.status)} className="gap-1">
                      {getStatusIcon(run.status)}
                      {formatStatus(run.status)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{itemQuantity}</TableCell>
                  <TableCell className="text-right">
                    <span
                      className={
                        successRate >= 90
                          ? 'text-green-600'
                          : successRate >= 70
                          ? 'text-amber-600'
                          : 'text-red-600'
                      }
                    >
                      {successRate.toFixed(0)}%
                    </span>
                  </TableCell>
                  <TableCell className="text-right">{formatCurrency(estimatedCost)}</TableCell>
                  <TableCell className="text-right">
                    {run.variance_percentage != null ? (
                      <span
                        className={
                          Math.abs(run.variance_percentage) > 10
                            ? 'text-red-600 font-medium'
                            : Math.abs(run.variance_percentage) > 5
                            ? 'text-amber-600'
                            : 'text-muted-foreground'
                        }
                      >
                        {run.variance_percentage > 0 ? '+' : ''}
                        {run.variance_percentage.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" asChild>
                      <Link to="/production-runs/$runId" params={{ runId: run.id }}>
                        <ArrowUpRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
