/**
 * Performance Charts
 *
 * Displays performance metrics using Recharts:
 * - Success rate trend (line chart)
 * - Daily production (bar chart)
 * - Material usage (bar chart by color)
 */

import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { getPerformanceCharts, type PerformanceChartData } from '@/lib/api/dashboard';

function ChartSkeleton() {
  return (
    <div className="h-[300px] flex items-center justify-center">
      <Skeleton className="h-full w-full" />
    </div>
  );
}

function SuccessRateChart({ data }: { data: PerformanceChartData }) {
  const chartData = data.success_rate_trend.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }),
    'Success Rate': d.success_rate,
    Completed: d.completed,
    Failed: d.failed,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${value}%`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
          formatter={(value: number, name: string) => [
            name === 'Success Rate' ? `${value}%` : value,
            name,
          ]}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="Success Rate"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          dot={{ fill: 'hsl(var(--primary))' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function ProductionChart({ data }: { data: PerformanceChartData }) {
  const chartData = data.daily_production.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }),
    Completed: d.items_completed,
    Failed: d.items_failed,
    Runs: d.runs_completed,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
        />
        <Legend />
        <Bar dataKey="Completed" fill="#22c55e" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Failed" fill="#f56565" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function MaterialUsageChart({ data }: { data: PerformanceChartData }) {
  const chartData = data.material_usage
    .filter((d) => d.total_grams > 0)
    .sort((a, b) => b.total_grams - a.total_grams)
    .slice(0, 10)
    .map((d) => ({
      name: d.color || d.material_type,
      grams: Math.round(d.total_grams),
    }));

  if (chartData.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-muted-foreground">
        No material usage data for this period
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          type="number"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${value}g`}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
          formatter={(value: number) => [`${value}g`, 'Used']}
        />
        <Bar dataKey="grams" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function PerformanceCharts() {
  const { data, isLoading, error } = useQuery<PerformanceChartData>({
    queryKey: ['dashboard', 'performance-charts', 7],
    queryFn: () => getPerformanceCharts(7),
    refetchInterval: 60000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance</CardTitle>
        <CardDescription>Last 7 days</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ChartSkeleton />
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Failed to load performance data
          </p>
        ) : data ? (
          <Tabs defaultValue="success-rate">
            <TabsList className="mb-4">
              <TabsTrigger value="success-rate">Success Rate</TabsTrigger>
              <TabsTrigger value="production">Production</TabsTrigger>
              <TabsTrigger value="materials">Materials</TabsTrigger>
            </TabsList>
            <TabsContent value="success-rate">
              <SuccessRateChart data={data} />
            </TabsContent>
            <TabsContent value="production">
              <ProductionChart data={data} />
            </TabsContent>
            <TabsContent value="materials">
              <MaterialUsageChart data={data} />
            </TabsContent>
          </Tabs>
        ) : null}
      </CardContent>
    </Card>
  );
}
