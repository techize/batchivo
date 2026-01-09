/**
 * Bar chart showing variance by product/model
 * Helps identify products with consistently inaccurate estimates
 */

import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { ArrowUpDown } from 'lucide-react'
import { ChartContainer, CHART_COLORS } from './ChartContainer'
import type { ProductionRunDetail } from '@/types/production-run'

interface ProductVarianceData {
  productName: string
  productSku: string
  averageVariance: number
  averageVariancePercent: number
  runCount: number
  totalEstimated: number
  totalActual: number
}

interface VarianceByProductChartProps {
  runs: ProductionRunDetail[]
  title?: string
  description?: string
  className?: string
  maxProducts?: number
}

function aggregateByProduct(runs: ProductionRunDetail[]): ProductVarianceData[] {
  const productMap = new Map<
    string,
    {
      name: string
      sku: string
      variances: number[]
      variancePercents: number[]
      estimated: number
      actual: number
    }
  >()

  // Aggregate data by product across all runs
  runs
    .filter((run) => run.status === 'completed')
    .forEach((run) => {
      run.items.forEach((item) => {
        if (!item.model) return

        const key = item.model.id
        const existing = productMap.get(key)

        // Calculate item-level variance (simplified - using run-level data proportionally)
        const itemVariance = run.variance_grams
          ? (run.variance_grams * item.quantity) / run.items.reduce((sum, i) => sum + i.quantity, 0)
          : 0
        const itemVariancePercent = run.variance_percentage || 0

        if (existing) {
          existing.variances.push(itemVariance)
          existing.variancePercents.push(itemVariancePercent)
          existing.estimated += item.estimated_total_cost || 0
          existing.actual += item.estimated_total_cost || 0 // Approximate
        } else {
          productMap.set(key, {
            name: item.model.name,
            sku: item.model.sku,
            variances: [itemVariance],
            variancePercents: [itemVariancePercent],
            estimated: item.estimated_total_cost || 0,
            actual: item.estimated_total_cost || 0,
          })
        }
      })
    })

  // Calculate averages
  return Array.from(productMap.entries()).map(([, data]) => ({
    productName: data.name.length > 20 ? data.name.substring(0, 18) + '...' : data.name,
    productSku: data.sku,
    averageVariance:
      data.variances.reduce((sum, v) => sum + v, 0) / data.variances.length,
    averageVariancePercent:
      data.variancePercents.reduce((sum, v) => sum + v, 0) / data.variancePercents.length,
    runCount: data.variances.length,
    totalEstimated: data.estimated,
    totalActual: data.actual,
  }))
}

function getBarColor(variance: number): string {
  if (Math.abs(variance) < 5) return CHART_COLORS.positive // Low variance - good
  if (Math.abs(variance) < 15) return CHART_COLORS.warning // Medium variance
  return CHART_COLORS.negative // High variance - needs attention
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    payload: ProductVarianceData
  }>
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0].payload

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="text-sm font-medium mb-2">{data.productSku}</p>
      <p className="text-xs text-muted-foreground mb-2">{data.productName}</p>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Avg Variance:</span>
          <span
            className={`font-medium ${
              data.averageVariance > 0
                ? 'text-red-500'
                : data.averageVariance < 0
                ? 'text-green-500'
                : ''
            }`}
          >
            {data.averageVariance > 0 ? '+' : ''}
            {data.averageVariance.toFixed(1)}g
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Variance %:</span>
          <span className="font-medium">{data.averageVariancePercent.toFixed(1)}%</span>
        </div>
        <div className="flex justify-between gap-4 pt-1 border-t">
          <span className="text-muted-foreground">Runs:</span>
          <span className="font-medium">{data.runCount}</span>
        </div>
      </div>
    </div>
  )
}

type SortKey = 'variance' | 'name' | 'runs'

export function VarianceByProductChart({
  runs,
  title = 'Variance by Product',
  description = 'Products with highest estimation variance',
  className,
  maxProducts = 10,
}: VarianceByProductChartProps) {
  const [sortBy, setSortBy] = useState<SortKey>('variance')
  const [sortDesc, setSortDesc] = useState(true)

  const allData = aggregateByProduct(runs)

  // Sort data
  const sortedData = [...allData].sort((a, b) => {
    let comparison = 0
    switch (sortBy) {
      case 'variance':
        comparison = Math.abs(a.averageVariance) - Math.abs(b.averageVariance)
        break
      case 'name':
        comparison = a.productName.localeCompare(b.productName)
        break
      case 'runs':
        comparison = a.runCount - b.runCount
        break
    }
    return sortDesc ? -comparison : comparison
  })

  const data = sortedData.slice(0, maxProducts)

  function toggleSort(key: SortKey) {
    if (sortBy === key) {
      setSortDesc(!sortDesc)
    } else {
      setSortBy(key)
      setSortDesc(true)
    }
  }

  if (data.length === 0) {
    return (
      <ChartContainer title={title} description={description} className={className}>
        <div className="h-[300px] flex items-center justify-center text-muted-foreground">
          No product variance data available
        </div>
      </ChartContainer>
    )
  }

  return (
    <ChartContainer
      title={title}
      description={description}
      className={className}
      actions={
        <Button variant="ghost" size="sm" onClick={() => toggleSort('variance')}>
          <ArrowUpDown className="h-4 w-4 mr-1" />
          Sort
        </Button>
      }
    >
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 20, left: 80, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value > 0 ? '+' : ''}${value}%`}
              className="text-muted-foreground"
            />
            <YAxis
              type="category"
              dataKey="productName"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={75}
              className="text-muted-foreground"
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--muted))' }} />
            <ReferenceLine x={0} stroke="hsl(var(--border))" />
            <Bar dataKey="averageVariancePercent" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.averageVariancePercent)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-4 mt-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CHART_COLORS.positive }} />
          <span className="text-muted-foreground">&lt;5% (Good)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CHART_COLORS.warning }} />
          <span className="text-muted-foreground">5-15% (Review)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CHART_COLORS.negative }} />
          <span className="text-muted-foreground">&gt;15% (Update BOM)</span>
        </div>
      </div>
    </ChartContainer>
  )
}
