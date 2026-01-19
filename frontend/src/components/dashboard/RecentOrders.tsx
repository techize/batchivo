/**
 * Recent Orders Panel
 *
 * Displays the most recent orders with quick status indicators
 * and navigation to full order details.
 */

import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { ShoppingBag, Clock, Truck, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getOrders, type Order } from '@/lib/api/orders'
import { useCurrency } from '@/hooks/useCurrency';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  shipped: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  delivered: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  refunded: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Clock className="h-3 w-3" />,
  processing: <RefreshCw className="h-3 w-3" />,
  shipped: <Truck className="h-3 w-3" />,
  delivered: <CheckCircle className="h-3 w-3" />,
  cancelled: <XCircle className="h-3 w-3" />,
  refunded: <RefreshCw className="h-3 w-3" />,
};

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

interface OrderCardProps {
  order: Order;
  formatCurrency: (value: string | number) => string;
}

function OrderCard({ order, formatCurrency }: OrderCardProps) {
  return (
    <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Link
            to="/orders/$orderId"
            params={{ orderId: order.id }}
            className="font-medium text-primary hover:underline"
          >
            {order.order_number}
          </Link>
          <Badge className={`${STATUS_COLORS[order.status]} flex items-center gap-1`}>
            {STATUS_ICONS[order.status]}
            {order.status}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground truncate mt-1">
          {order.customer_name} • {order.items.length} item{order.items.length !== 1 ? 's' : ''}
        </p>
      </div>
      <div className="ml-4 text-right">
        <p className="font-medium">{formatCurrency(order.total)}</p>
        <p className="text-xs text-muted-foreground">{formatRelativeTime(order.created_at)}</p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-40" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-3 w-12" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function RecentOrders() {
  const { formatCurrency } = useCurrency();
  const { data, isLoading, error } = useQuery({
    queryKey: ['orders', { limit: 5 }],
    queryFn: () => getOrders({ limit: 5 }),
  });

  const pendingCount = data?.data?.filter(o => o.status === 'pending' || o.status === 'processing').length || 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ShoppingBag className="h-5 w-5" />
              Recent Orders
            </CardTitle>
            <CardDescription>
              {pendingCount > 0
                ? `${pendingCount} order${pendingCount !== 1 ? 's' : ''} need attention`
                : 'Latest customer orders'}
            </CardDescription>
          </div>
          <Link to="/orders">
            <Button variant="outline" size="sm">
              View All
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <LoadingSkeleton />
        ) : error ? (
          <div className="text-center py-6 text-muted-foreground">
            <p>Failed to load orders</p>
          </div>
        ) : !data?.data?.length ? (
          <div className="text-center py-6 text-muted-foreground">
            <ShoppingBag className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No orders yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data.data.map((order) => (
              <OrderCard key={order.id} order={order} formatCurrency={formatCurrency} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
