/**
 * Dashboard Summary Cards
 *
 * Displays key metrics in a grid of cards including:
 * - Active prints
 * - Completed/Failed/Cancelled today
 * - Low stock alerts
 * - 7-day success rate
 */

import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Ban,
  AlertTriangle,
  TrendingUp,
  Trash2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getDashboardSummary, type DashboardSummary } from '@/lib/api/dashboard';
import { cn } from '@/lib/utils';

interface SummaryCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  description?: string;
  trend?: 'up' | 'down' | 'neutral';
  iconBgColor?: string;
}

function SummaryCard({
  title,
  value,
  icon,
  description,
  iconBgColor = 'bg-primary/10',
}: SummaryCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className={cn('rounded-md p-2', iconBgColor)}>{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8 rounded-md" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16 mb-1" />
        <Skeleton className="h-3 w-32" />
      </CardContent>
    </Card>
  );
}

export function SummaryCards() {
  const { data, isLoading, error } = useQuery<DashboardSummary>({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => getDashboardSummary(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 7 }).map((_, i) => (
          <SummaryCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="col-span-full">
          <CardContent className="py-4 text-center text-muted-foreground">
            Failed to load dashboard summary
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <SummaryCard
        title="Active Prints"
        value={data.active_prints}
        icon={<Activity className="h-4 w-4 text-blue-600" />}
        iconBgColor="bg-blue-100 dark:bg-blue-900/30"
        description="Currently in progress"
      />
      <SummaryCard
        title="Completed Today"
        value={data.completed_today}
        icon={<CheckCircle2 className="h-4 w-4 text-green-600" />}
        iconBgColor="bg-green-100 dark:bg-green-900/30"
        description="Finished prints"
      />
      <SummaryCard
        title="Failed Today"
        value={data.failed_today}
        icon={<XCircle className="h-4 w-4 text-red-600" />}
        iconBgColor="bg-red-100 dark:bg-red-900/30"
        description="Print failures"
      />
      <SummaryCard
        title="Cancelled Today"
        value={data.cancelled_today}
        icon={<Ban className="h-4 w-4 text-gray-600" />}
        iconBgColor="bg-gray-100 dark:bg-gray-900/30"
        description="User cancelled"
      />
      <SummaryCard
        title="Low Stock"
        value={data.low_stock_count}
        icon={<AlertTriangle className="h-4 w-4 text-amber-600" />}
        iconBgColor="bg-amber-100 dark:bg-amber-900/30"
        description="Spools below 10%"
      />
      <SummaryCard
        title="7-Day Success Rate"
        value={`${data.success_rate_7d}%`}
        icon={<TrendingUp className="h-4 w-4 text-emerald-600" />}
        iconBgColor="bg-emerald-100 dark:bg-emerald-900/30"
        description="Completed / (Completed + Failed)"
      />
      <SummaryCard
        title="7-Day Waste"
        value={`${data.total_waste_7d_grams.toFixed(0)}g`}
        icon={<Trash2 className="h-4 w-4 text-rose-600" />}
        iconBgColor="bg-rose-100 dark:bg-rose-900/30"
        description="Material wasted from failures"
      />
    </div>
  );
}
