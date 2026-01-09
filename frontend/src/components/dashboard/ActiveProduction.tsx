/**
 * Active Production Panel
 *
 * Displays currently running production runs with key details
 * and quick link to full production run detail.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Clock, Printer, Package } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getActiveProduction, type ActiveProductionRun } from '@/lib/api/dashboard';
import { formatDuration } from '@/lib/api/production-runs';

function ActiveRunCard({ run }: { run: ActiveProductionRun }) {
  const startTime = new Date(run.started_at);
  const elapsedMs = Date.now() - startTime.getTime();
  const elapsedHours = elapsedMs / 3600000;

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Link
            to="/production-runs/$id"
            params={{ id: run.id }}
            className="font-medium text-primary hover:underline"
          >
            {run.run_number}
          </Link>
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            In Progress
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground truncate mt-1">
          {run.products_summary}
        </p>
        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
          {run.printer_name && (
            <span className="flex items-center gap-1">
              <Printer className="h-3 w-3" />
              {run.printer_name}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Package className="h-3 w-3" />
            {run.total_quantity} items
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDuration(elapsedHours)} elapsed
          </span>
        </div>
      </div>
      <div className="ml-4 text-right">
        {run.estimated_print_time_hours && (
          <div className="text-sm">
            <span className="text-muted-foreground">Est: </span>
            <span className="font-medium">{formatDuration(run.estimated_print_time_hours)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ActiveRunSkeleton() {
  return (
    <div className="p-4 border rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-20" />
      </div>
      <Skeleton className="h-4 w-48 mb-2" />
      <div className="flex gap-4">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
  );
}

export function ActiveProduction() {
  const { data, isLoading, error } = useQuery<ActiveProductionRun[]>({
    queryKey: ['dashboard', 'active-production'],
    queryFn: getActiveProduction,
    refetchInterval: 30000,
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Active Production</CardTitle>
          <CardDescription>Currently running prints</CardDescription>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/production-runs" search={{ status_filter: 'in_progress' }}>
            View All
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <ActiveRunSkeleton />
            <ActiveRunSkeleton />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Failed to load active production
          </p>
        ) : data && data.length > 0 ? (
          <div className="space-y-3">
            {data.map((run) => (
              <ActiveRunCard key={run.id} run={run} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Printer className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No active prints</p>
            <Button variant="link" size="sm" asChild className="mt-2">
              <Link to="/production-runs/new">Start a new print</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
