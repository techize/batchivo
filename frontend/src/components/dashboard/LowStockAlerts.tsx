/**
 * Low Stock Alerts Panel
 *
 * Displays spools that are running low on filament
 * with visual indicator of remaining percentage.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { getLowStockSpools, type LowStockSpool } from '@/lib/api/dashboard';
import { cn } from '@/lib/utils';

function SpoolAlertCard({ spool }: { spool: LowStockSpool }) {
  return (
    <div className="flex items-center gap-3 p-3 border rounded-lg">
      {/* Color swatch */}
      <div
        className="w-8 h-8 rounded-md border flex-shrink-0"
        style={{
          backgroundColor: spool.color_hex || '#cccccc',
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Link
            to="/inventory/$id"
            params={{ id: spool.id }}
            className="font-medium text-sm hover:text-primary hover:underline truncate"
          >
            {spool.spool_id}
          </Link>
          {spool.is_critical && (
            <Badge variant="destructive" className="text-xs">
              Critical
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          {spool.brand} {spool.color} ({spool.material_type})
        </p>
        <div className="flex items-center gap-2 mt-1.5">
          <Progress
            value={spool.percent_remaining}
            className={cn(
              'h-1.5 flex-1',
              spool.is_critical ? '[&>div]:bg-red-500' : '[&>div]:bg-amber-500'
            )}
          />
          <span
            className={cn(
              'text-xs font-medium',
              spool.is_critical ? 'text-red-600' : 'text-amber-600'
            )}
          >
            {spool.percent_remaining.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="text-right text-xs text-muted-foreground">
        <div>{spool.current_weight.toFixed(0)}g</div>
        <div className="text-[10px]">of {spool.initial_weight}g</div>
      </div>
    </div>
  );
}

function SpoolAlertSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3 border rounded-lg">
      <Skeleton className="w-8 h-8 rounded-md" />
      <div className="flex-1">
        <Skeleton className="h-4 w-24 mb-1" />
        <Skeleton className="h-3 w-32 mb-1.5" />
        <Skeleton className="h-1.5 w-full" />
      </div>
      <Skeleton className="h-8 w-12" />
    </div>
  );
}

export function LowStockAlerts() {
  const { data, isLoading, error } = useQuery<LowStockSpool[]>({
    queryKey: ['dashboard', 'low-stock'],
    queryFn: () => getLowStockSpools(10, 10),
    refetchInterval: 60000,
  });

  const criticalCount = data?.filter((s) => s.is_critical).length || 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="flex items-center gap-2">
            Low Stock Alerts
            {criticalCount > 0 && (
              <Badge variant="destructive" className="ml-1">
                {criticalCount} critical
              </Badge>
            )}
          </CardTitle>
          <CardDescription>Spools below 10% remaining</CardDescription>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/inventory">View Inventory</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <SpoolAlertSkeleton />
            <SpoolAlertSkeleton />
            <SpoolAlertSkeleton />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Failed to load low stock alerts
          </p>
        ) : data && data.length > 0 ? (
          <div className="space-y-2 max-h-[280px] overflow-y-auto">
            {data.map((spool) => (
              <SpoolAlertCard key={spool.id} spool={spool} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">All spools have adequate stock</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
