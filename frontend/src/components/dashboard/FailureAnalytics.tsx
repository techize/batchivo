/**
 * Failure Analytics Panel
 *
 * Displays failure breakdown by reason including:
 * - Pie chart of failure reasons
 * - Most common failures list
 * - Failure rate stat
 */

import { useQuery } from '@tanstack/react-query';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  getFailureAnalytics,
  formatFailureReason,
  getFailureReasonColor,
  type FailureAnalytics as FailureAnalyticsType,
} from '@/lib/api/dashboard';

function FailurePieChart({ data }: { data: FailureAnalyticsType }) {
  const chartData = data.failure_by_reason.map((d) => ({
    name: formatFailureReason(d.reason),
    value: d.count,
    color: getFailureReasonColor(d.reason),
  }));

  if (chartData.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
        No failures to display
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
          }}
          formatter={(value: number, name: string) => [value, name]}
        />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          formatter={(value) => (
            <span className="text-xs text-foreground">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function TopFailuresList({ data }: { data: FailureAnalyticsType }) {
  if (data.most_common_failures.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 mt-4">
      <h4 className="text-sm font-medium text-muted-foreground">Most Common</h4>
      <div className="space-y-1.5">
        {data.most_common_failures.slice(0, 3).map((failure) => (
          <div
            key={failure.reason}
            className="flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getFailureReasonColor(failure.reason) }}
              />
              <span>{formatFailureReason(failure.reason)}</span>
            </div>
            <Badge variant="outline" className="text-xs">
              {failure.count} ({failure.percentage.toFixed(0)}%)
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FailureAnalyticsPanel() {
  const { data, isLoading, error } = useQuery<FailureAnalyticsType>({
    queryKey: ['dashboard', 'failure-analytics', 30],
    queryFn: () => getFailureAnalytics(30),
    refetchInterval: 60000,
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Failure Analytics</CardTitle>
            <CardDescription>Last 30 days</CardDescription>
          </div>
          {data && (
            <div className="text-right">
              <div className="text-2xl font-bold text-coral">
                {data.failure_rate.toFixed(1)}%
              </div>
              <div className="text-xs text-muted-foreground">
                {data.total_failures} failures
              </div>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-[200px] w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Failed to load failure analytics
          </p>
        ) : data ? (
          data.total_failures > 0 ? (
            <>
              <FailurePieChart data={data} />
              <TopFailuresList data={data} />
            </>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <div className="text-4xl mb-2">🎉</div>
              <p className="text-sm">No failures in the last 30 days!</p>
            </div>
          )
        ) : null}
      </CardContent>
    </Card>
  );
}
