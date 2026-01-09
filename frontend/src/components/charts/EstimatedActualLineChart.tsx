/**
 * Line chart showing Estimated vs Actual values over time
 * Used for tracking production run accuracy trends
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { ChartContainer, CHART_COLORS } from './ChartContainer'
import type { ProductionRun } from '@/types/production-run'

interface ChartDataPoint {
  date: string
  dateLabel: string
  estimated: number
  actual: number
  variance: number
  variancePercent: number
  runNumber: string
}

interface EstimatedActualLineChartProps {
  runs: ProductionRun[]
  title?: string
  description?: string
  className?: string
}

function transformData(runs: ProductionRun[]): ChartDataPoint[] {
  return runs
    .filter(
      (run) =>
        run.status === 'completed' &&
        run.estimated_total_weight_grams != null &&
        run.actual_total_weight_grams != null
    )
    .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
    .map((run) => ({
      date: run.started_at,
      dateLabel: format(parseISO(run.started_at), 'MMM d'),
      estimated: run.estimated_total_weight_grams || 0,
      actual: run.actual_total_weight_grams || 0,
      variance: run.variance_grams || 0,
      variancePercent: run.variance_percentage || 0,
      runNumber: run.run_number,
    }))
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    name: string
    value: number
    color: string
    dataKey: string
  }>
  label?: string
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null

  const data = payload[0]?.payload as ChartDataPoint | undefined
  if (!data) return null

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="text-sm font-medium mb-2">
        Run #{data.runNumber} - {format(parseISO(data.date), 'MMM d, yyyy')}
      </p>
      <div className="space-y-1 text-sm">
        <div className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLORS.neutral }}
          />
          <span className="text-muted-foreground">Estimated:</span>
          <span className="font-medium">{data.estimated.toFixed(1)}g</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLORS.primary }}
          />
          <span className="text-muted-foreground">Actual:</span>
          <span className="font-medium">{data.actual.toFixed(1)}g</span>
        </div>
        <div className="flex items-center gap-2 pt-1 border-t">
          <span className="text-muted-foreground">Variance:</span>
          <span
            className={`font-medium ${
              data.variance > 0 ? 'text-red-500' : data.variance < 0 ? 'text-green-500' : ''
            }`}
          >
            {data.variance > 0 ? '+' : ''}
            {data.variance.toFixed(1)}g ({data.variancePercent.toFixed(1)}%)
          </span>
        </div>
      </div>
    </div>
  )
}

export function EstimatedActualLineChart({
  runs,
  title = 'Estimated vs Actual Usage',
  description = 'Material usage comparison over time',
  className,
}: EstimatedActualLineChartProps) {
  const data = transformData(runs)

  if (data.length === 0) {
    return (
      <ChartContainer title={title} description={description} className={className}>
        <div className="h-[300px] flex items-center justify-center text-muted-foreground">
          No completed runs with weight data available
        </div>
      </ChartContainer>
    )
  }

  return (
    <ChartContainer title={title} description={description} className={className}>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="dateLabel"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}g`}
              className="text-muted-foreground"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="top"
              height={36}
              formatter={(value) => <span className="text-sm">{value}</span>}
            />
            <Line
              type="monotone"
              dataKey="estimated"
              name="Estimated"
              stroke={CHART_COLORS.neutral}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual"
              stroke={CHART_COLORS.primary}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartContainer>
  )
}
