/**
 * Variance Dashboard - Comprehensive view of production run variance data
 * Combines charts, filters, statistics, and export functionality
 */

import { useState, useMemo } from 'react'
import { format, subDays, startOfMonth, endOfMonth, subMonths } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Download,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
  LineChart as LineChartIcon,
  RefreshCw,
} from 'lucide-react'
import { EstimatedActualLineChart } from './EstimatedActualLineChart'
import { VarianceByProductChart } from './VarianceByProductChart'
import {
  calculateVarianceStats,
  filterRunsByDateRange,
  runsToCSV,
  statsToCSV,
  downloadCSV,
  getHighVarianceProducts,
  type HighVarianceProduct,
} from '@/utils/chartDataUtils'
import type { ProductionRunDetail } from '@/types/production-run'

type DateRangePreset = '7d' | '30d' | '90d' | 'thisMonth' | 'lastMonth' | 'all'

interface DateRange {
  start?: Date
  end?: Date
  label: string
}

function getDateRange(preset: DateRangePreset): DateRange {
  const now = new Date()

  switch (preset) {
    case '7d':
      return { start: subDays(now, 7), end: now, label: 'Last 7 days' }
    case '30d':
      return { start: subDays(now, 30), end: now, label: 'Last 30 days' }
    case '90d':
      return { start: subDays(now, 90), end: now, label: 'Last 90 days' }
    case 'thisMonth':
      return {
        start: startOfMonth(now),
        end: endOfMonth(now),
        label: 'This month',
      }
    case 'lastMonth': {
      const lastMonth = subMonths(now, 1)
      return {
        start: startOfMonth(lastMonth),
        end: endOfMonth(lastMonth),
        label: 'Last month',
      }
    }
    case 'all':
    default:
      return { label: 'All time' }
  }
}

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: 'positive' | 'negative' | 'neutral'
}

function StatCard({ title, value, subtitle, icon, trend }: StatCardProps) {
  const trendColor =
    trend === 'positive'
      ? 'text-green-500'
      : trend === 'negative'
      ? 'text-red-500'
      : 'text-muted-foreground'

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className={`text-2xl font-bold ${trendColor}`}>{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
            )}
          </div>
          <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface HighVarianceTableProps {
  products: HighVarianceProduct[]
}

function HighVarianceTable({ products }: HighVarianceTableProps) {
  if (products.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No high variance products found
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-3 px-2 font-medium">Product</th>
            <th className="text-left py-3 px-2 font-medium">SKU</th>
            <th className="text-right py-3 px-2 font-medium">Avg Variance</th>
            <th className="text-right py-3 px-2 font-medium">Runs</th>
            <th className="text-center py-3 px-2 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.modelId} className="border-b hover:bg-muted/50">
              <td className="py-3 px-2">
                <span className="font-medium">{product.modelName}</span>
              </td>
              <td className="py-3 px-2 text-muted-foreground">
                {product.modelSku}
              </td>
              <td className="py-3 px-2 text-right">
                <span
                  className={
                    product.averageVariancePercent > 15
                      ? 'text-red-500 font-medium'
                      : product.averageVariancePercent > 5
                      ? 'text-amber-500'
                      : 'text-green-500'
                  }
                >
                  {product.averageVariancePercent.toFixed(1)}%
                </span>
              </td>
              <td className="py-3 px-2 text-right text-muted-foreground">
                {product.runCount}
              </td>
              <td className="py-3 px-2 text-center">
                <Badge
                  variant={
                    product.recommendation === 'update'
                      ? 'destructive'
                      : product.recommendation === 'review'
                      ? 'secondary'
                      : 'outline'
                  }
                >
                  {product.recommendation === 'update'
                    ? 'Update BOM'
                    : product.recommendation === 'review'
                    ? 'Review'
                    : 'OK'}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface VarianceDashboardProps {
  runs: ProductionRunDetail[]
  isLoading?: boolean
  onRefresh?: () => void
  className?: string
}

export function VarianceDashboard({
  runs,
  isLoading = false,
  onRefresh,
  className,
}: VarianceDashboardProps) {
  const [dateRange, setDateRange] = useState<DateRangePreset>('30d')
  const [activeTab, setActiveTab] = useState('overview')

  // Filter runs by date range
  const filteredRuns = useMemo(() => {
    const range = getDateRange(dateRange)
    return filterRunsByDateRange(runs, range.start, range.end)
  }, [runs, dateRange])

  // Calculate statistics
  const stats = useMemo(
    () => calculateVarianceStats(filteredRuns),
    [filteredRuns]
  )

  // Get high variance products
  const highVarianceProducts = useMemo(
    () => getHighVarianceProducts(filteredRuns, 10),
    [filteredRuns]
  )

  // Export handlers
  function handleExportRuns() {
    const csv = runsToCSV(filteredRuns)
    const filename = `variance-runs-${format(new Date(), 'yyyy-MM-dd')}.csv`
    downloadCSV(csv, filename)
  }

  function handleExportStats() {
    const range = getDateRange(dateRange)
    const csv = statsToCSV(stats, { start: range.start, end: range.end })
    const filename = `variance-report-${format(new Date(), 'yyyy-MM-dd')}.csv`
    downloadCSV(csv, filename)
  }

  if (isLoading) {
    return (
      <div className={className}>
        <div className="grid gap-4 md:grid-cols-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-[300px] w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentRange = getDateRange(dateRange)

  return (
    <div className={className}>
      {/* Header with filters and export */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Variance Analysis
          </h2>
          <p className="text-muted-foreground">
            {currentRange.label} &middot; {stats.completedRuns} completed runs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={dateRange}
            onValueChange={(v) => setDateRange(v as DateRangePreset)}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="thisMonth">This month</SelectItem>
              <SelectItem value="lastMonth">Last month</SelectItem>
              <SelectItem value="all">All time</SelectItem>
            </SelectContent>
          </Select>
          {onRefresh && (
            <Button variant="outline" size="icon" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}
          <Button variant="outline" onClick={handleExportStats}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <StatCard
          title="Average Variance"
          value={`${stats.averageVariancePercent > 0 ? '+' : ''}${stats.averageVariancePercent.toFixed(1)}%`}
          subtitle={`${stats.averageVarianceGrams.toFixed(0)}g average`}
          icon={
            stats.averageVariancePercent > 5 ? (
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            ) : (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            )
          }
          trend={
            Math.abs(stats.averageVariancePercent) > 10
              ? 'negative'
              : Math.abs(stats.averageVariancePercent) < 5
              ? 'positive'
              : 'neutral'
          }
        />
        <StatCard
          title="Over Estimate"
          value={stats.runsOverEstimate}
          subtitle={`${((stats.runsOverEstimate / stats.completedRuns) * 100 || 0).toFixed(0)}% of runs`}
          icon={<TrendingUp className="h-5 w-5 text-red-500" />}
          trend={stats.runsOverEstimate > stats.runsUnderEstimate ? 'negative' : 'neutral'}
        />
        <StatCard
          title="Under Estimate"
          value={stats.runsUnderEstimate}
          subtitle={`${((stats.runsUnderEstimate / stats.completedRuns) * 100 || 0).toFixed(0)}% of runs`}
          icon={<TrendingDown className="h-5 w-5 text-green-500" />}
          trend={stats.runsUnderEstimate > stats.runsOverEstimate ? 'positive' : 'neutral'}
        />
        <StatCard
          title="Total Material"
          value={`${(stats.totalActualGrams / 1000).toFixed(1)}kg`}
          subtitle={`Est: ${(stats.totalEstimatedGrams / 1000).toFixed(1)}kg`}
          icon={<BarChart3 className="h-5 w-5 text-primary" />}
        />
      </div>

      {/* Tabs for different views */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="overview" className="gap-2">
            <LineChartIcon className="h-4 w-4" />
            Trend
          </TabsTrigger>
          <TabsTrigger value="products" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            By Product
          </TabsTrigger>
          <TabsTrigger value="table" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            High Variance
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <EstimatedActualLineChart
            runs={filteredRuns}
            title="Estimated vs Actual Usage"
            description="Material usage comparison over time"
          />
        </TabsContent>

        <TabsContent value="products">
          <VarianceByProductChart
            runs={filteredRuns}
            title="Variance by Product"
            description="Products with highest estimation variance"
            maxProducts={10}
          />
        </TabsContent>

        <TabsContent value="table">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-medium">
                  Products Needing BOM Review
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Products with consistently inaccurate material estimates
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={handleExportRuns}>
                <Download className="h-4 w-4 mr-2" />
                Export Runs
              </Button>
            </CardHeader>
            <CardContent>
              <HighVarianceTable products={highVarianceProducts} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
