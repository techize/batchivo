/**
 * Activity Feed
 *
 * Shows recent inventory transactions and activity
 * across the system.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import {
  ShoppingCart,
  Printer,
  RefreshCw,
  ArrowLeftRight,
  Undo2,
  Trash2,
  Scale,
  Activity,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  getRecentActivity,
  formatTransactionType,
  formatWeightChange,
  timeAgo,
  type RecentActivityItem,
} from '@/lib/api/dashboard';
import { cn } from '@/lib/utils';

const transactionIcons: Record<string, React.ReactNode> = {
  PURCHASE: <ShoppingCart className="h-4 w-4" />,
  USAGE: <Printer className="h-4 w-4" />,
  ADJUSTMENT: <RefreshCw className="h-4 w-4" />,
  TRANSFER: <ArrowLeftRight className="h-4 w-4" />,
  RETURN: <Undo2 className="h-4 w-4" />,
  WASTE: <Trash2 className="h-4 w-4" />,
  COUNT: <Scale className="h-4 w-4" />,
};

const transactionColors: Record<string, string> = {
  PURCHASE: 'text-green-600 bg-green-100 dark:bg-green-900/30',
  USAGE: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30',
  ADJUSTMENT: 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30',
  TRANSFER: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30',
  RETURN: 'text-cyan-600 bg-cyan-100 dark:bg-cyan-900/30',
  WASTE: 'text-red-600 bg-red-100 dark:bg-red-900/30',
  COUNT: 'text-gray-600 bg-gray-100 dark:bg-gray-900/30',
};

function ActivityItem({ item }: { item: RecentActivityItem }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <div
        className={cn(
          'rounded-full p-2 mt-0.5',
          transactionColors[item.transaction_type] || transactionColors.COUNT
        )}
      >
        {transactionIcons[item.transaction_type] || <Activity className="h-4 w-4" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {formatTransactionType(item.transaction_type)}
          </Badge>
          <span
            className={cn(
              'text-sm font-medium',
              item.weight_change >= 0 ? 'text-green-600' : 'text-red-600'
            )}
          >
            {formatWeightChange(item.weight_change)}
          </span>
        </div>
        <p className="text-sm text-muted-foreground mt-0.5 truncate">
          {item.description}
        </p>
        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
          {item.spool_id && (
            <Link
              to="/inventory/$id"
              params={{ id: item.spool_id }}
              className="hover:text-primary hover:underline"
            >
              {item.spool_id}
              {item.spool_color && ` (${item.spool_color})`}
            </Link>
          )}
          {item.run_number && (
            <>
              <span>•</span>
              <Link
                to="/production-runs/$id"
                params={{ id: item.production_run_id! }}
                className="hover:text-primary hover:underline"
              >
                {item.run_number}
              </Link>
            </>
          )}
        </div>
      </div>
      <div className="text-xs text-muted-foreground whitespace-nowrap">
        {timeAgo(item.created_at)}
      </div>
    </div>
  );
}

function ActivitySkeleton() {
  return (
    <div className="flex items-start gap-3 py-2">
      <Skeleton className="h-8 w-8 rounded-full" />
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-5 w-12" />
        </div>
        <Skeleton className="h-4 w-48 mb-1" />
        <Skeleton className="h-3 w-24" />
      </div>
      <Skeleton className="h-3 w-12" />
    </div>
  );
}

export function ActivityFeed() {
  const { data, isLoading, error } = useQuery<RecentActivityItem[]>({
    queryKey: ['dashboard', 'recent-activity'],
    queryFn: () => getRecentActivity(15),
    refetchInterval: 30000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Latest inventory transactions</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="divide-y">
            <ActivitySkeleton />
            <ActivitySkeleton />
            <ActivitySkeleton />
            <ActivitySkeleton />
            <ActivitySkeleton />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Failed to load activity feed
          </p>
        ) : data && data.length > 0 ? (
          <div className="divide-y max-h-[400px] overflow-y-auto">
            {data.map((item) => (
              <ActivityItem key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No recent activity</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
