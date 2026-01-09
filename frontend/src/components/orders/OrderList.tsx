/**
 * OrderList Component
 *
 * Displays a paginated list of customer orders with status filtering,
 * search, date range filtering, and quick actions for shipping/delivery/cancel.
 */

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import {
  Loader2,
  Package,
  Truck,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Eye,
  ChevronLeft,
  ChevronRight,
  Search,
  Download,
  Calendar,
  X,
} from 'lucide-react'

import { getOrders, shipOrder, deliverOrder, cancelOrder, type Order } from '@/lib/api/orders'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'


const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  shipped: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  delivered: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  refunded: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <Clock className="h-3 w-3" />,
  processing: <RefreshCw className="h-3 w-3" />,
  shipped: <Truck className="h-3 w-3" />,
  delivered: <CheckCircle className="h-3 w-3" />,
  cancelled: <XCircle className="h-3 w-3" />,
  refunded: <RefreshCw className="h-3 w-3" />,
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(amount)
}

function exportToCSV(orders: Order[]) {
  const headers = [
    'Order Number',
    'Status',
    'Customer Name',
    'Customer Email',
    'Items',
    'Subtotal',
    'Shipping',
    'Total',
    'Shipping Address',
    'Tracking Number',
    'Created At',
  ]

  const rows = orders.map(order => [
    order.order_number,
    order.status,
    order.customer_name,
    order.customer_email,
    order.items.map(i => `${i.quantity}x ${i.product_name}`).join('; '),
    order.subtotal.toFixed(2),
    order.shipping_cost.toFixed(2),
    order.total.toFixed(2),
    [
      order.shipping_address_line1,
      order.shipping_address_line2,
      order.shipping_city,
      order.shipping_postcode,
      order.shipping_country,
    ].filter(Boolean).join(', '),
    order.tracking_number || '',
    new Date(order.created_at).toISOString(),
  ])

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')),
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `orders-${new Date().toISOString().split('T')[0]}.csv`
  link.click()
}

export function OrderList() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [shipDialogOpen, setShipDialogOpen] = useState(false)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [trackingNumber, setTrackingNumber] = useState('')
  const [trackingUrl, setTrackingUrl] = useState('')
  const [cancelReason, setCancelReason] = useState('')

  const queryClient = useQueryClient()

  // Debounced search - use useMemo to avoid recreating the value on every render
  const debouncedSearch = useMemo(() => searchQuery, [searchQuery])

  const { data, isLoading, error } = useQuery({
    queryKey: ['orders', {
      status: statusFilter === 'all' ? undefined : statusFilter,
      search: debouncedSearch || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
    }],
    queryFn: () => getOrders({
      status: statusFilter === 'all' ? undefined : statusFilter,
      search: debouncedSearch || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
      limit: 20,
    }),
  })

  const shipMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { tracking_number?: string; tracking_url?: string } }) =>
      shipOrder(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['orderCounts'] })
      setShipDialogOpen(false)
      setSelectedOrder(null)
      setTrackingNumber('')
      setTrackingUrl('')
    },
  })

  const deliverMutation = useMutation({
    mutationFn: (id: string) => deliverOrder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['orderCounts'] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      cancelOrder(id, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['orderCounts'] })
      setCancelDialogOpen(false)
      setSelectedOrder(null)
      setCancelReason('')
    },
  })

  const handleShip = (order: Order) => {
    setSelectedOrder(order)
    setShipDialogOpen(true)
  }

  const confirmShip = () => {
    if (selectedOrder) {
      shipMutation.mutate({
        id: selectedOrder.id,
        data: {
          tracking_number: trackingNumber || undefined,
          tracking_url: trackingUrl || undefined,
        },
      })
    }
  }

  const handleDeliver = (order: Order) => {
    deliverMutation.mutate(order.id)
  }

  const handleCancel = (order: Order) => {
    setSelectedOrder(order)
    setCancelDialogOpen(true)
  }

  const confirmCancel = () => {
    if (selectedOrder) {
      cancelMutation.mutate({
        id: selectedOrder.id,
        reason: cancelReason || undefined,
      })
    }
  }

  const handleExportCSV = () => {
    if (data?.data) {
      exportToCSV(data.data)
    }
  }

  const clearFilters = () => {
    setSearchQuery('')
    setDateFrom('')
    setDateTo('')
    setStatusFilter('all')
    setPage(1)
  }

  const hasActiveFilters = searchQuery || dateFrom || dateTo || statusFilter !== 'all'

  const statusCounts = {
    pending: data?.data?.filter(o => o.status === 'pending').length || 0,
    processing: data?.data?.filter(o => o.status === 'processing').length || 0,
    shipped: data?.data?.filter(o => o.status === 'shipped').length || 0,
  }

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading orders</p>
          <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Orders</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} orders • {statusCounts.pending} pending • {statusCounts.shipped} shipped
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExportCSV}
          disabled={!data?.data?.length}
        >
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4">
            {/* Search and Status Filter Row */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search orders, customers..."
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
                  className="pl-9"
                />
              </div>
              <Select value={statusFilter} onValueChange={(value) => { setStatusFilter(value); setPage(1) }}>
                <SelectTrigger className="w-full sm:w-[180px]">
                  <SelectValue placeholder="All orders" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Orders</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="shipped">Shipped</SelectItem>
                  <SelectItem value="delivered">Delivered</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                  <SelectItem value="refunded">Refunded</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date Range Filter Row */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Date range:</span>
              </div>
              <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center">
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
                  className="w-full sm:w-auto"
                />
                <span className="hidden text-muted-foreground sm:inline">to</span>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
                  className="w-full sm:w-auto"
                />
                {hasActiveFilters && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearFilters}
                    className="text-muted-foreground"
                  >
                    <X className="mr-1 h-3 w-3" />
                    Clear filters
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-[400px] items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : !data?.data?.length ? (
            <div className="flex h-[200px] flex-col items-center justify-center gap-2">
              <Package className="h-12 w-12 text-muted-foreground/50" />
              <p className="text-lg font-medium">No orders found</p>
              <p className="text-sm text-muted-foreground">
                {hasActiveFilters
                  ? 'Try adjusting your filters'
                  : 'Orders will appear here when customers complete purchases'}
              </p>
            </div>
          ) : (
            <>
              <div className="-mx-6 px-6 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Order</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.data.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell className="font-medium">
                          {order.order_number}
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{order.customer_name}</div>
                            <div className="text-sm text-muted-foreground">{order.customer_email}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {order.items.length} item{order.items.length !== 1 ? 's' : ''}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {order.items.slice(0, 2).map(i => i.product_name).join(', ')}
                            {order.items.length > 2 && '...'}
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(order.total)}
                        </TableCell>
                        <TableCell>
                          <Badge className={`${STATUS_COLORS[order.status]} flex w-fit items-center gap-1`}>
                            {STATUS_ICONS[order.status]}
                            {order.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(order.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link to="/orders/$orderId" params={{ orderId: order.id }}>
                              <Button variant="ghost" size="sm">
                                <Eye className="mr-1 h-3 w-3" />
                                View
                              </Button>
                            </Link>
                            {(order.status === 'pending' || order.status === 'processing') && (
                              <>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleShip(order)}
                                  disabled={shipMutation.isPending}
                                >
                                  <Truck className="mr-1 h-3 w-3" />
                                  Ship
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleCancel(order)}
                                  disabled={cancelMutation.isPending}
                                  className="text-destructive hover:text-destructive"
                                >
                                  <XCircle className="mr-1 h-3 w-3" />
                                  Cancel
                                </Button>
                              </>
                            )}
                            {order.status === 'shipped' && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleDeliver(order)}
                                disabled={deliverMutation.isPending}
                              >
                                <CheckCircle className="mr-1 h-3 w-3" />
                                Delivered
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {data.total > 20 && (
                <div className="flex items-center justify-between pt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {Math.ceil(data.total / 20)}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => p + 1)}
                      disabled={!data.has_more}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Ship Dialog */}
      <Dialog open={shipDialogOpen} onOpenChange={setShipDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ship Order {selectedOrder?.order_number}</DialogTitle>
            <DialogDescription>
              Mark this order as shipped. You can optionally add tracking information.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="tracking-number">Tracking Number (optional)</Label>
              <Input
                id="tracking-number"
                placeholder="e.g., RM123456789GB"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tracking-url">Tracking URL (optional)</Label>
              <Input
                id="tracking-url"
                placeholder="e.g., https://www.royalmail.com/track/..."
                value={trackingUrl}
                onChange={(e) => setTrackingUrl(e.target.value)}
              />
            </div>
            {selectedOrder && (
              <div className="rounded-lg bg-muted p-3 text-sm">
                <p className="font-medium">Shipping to:</p>
                <p>{selectedOrder.customer_name}</p>
                <p>{selectedOrder.shipping_address_line1}</p>
                {selectedOrder.shipping_address_line2 && <p>{selectedOrder.shipping_address_line2}</p>}
                <p>{selectedOrder.shipping_city}, {selectedOrder.shipping_postcode}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShipDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmShip} disabled={shipMutation.isPending}>
              {shipMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Mark as Shipped
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cancel Order Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Order {selectedOrder?.order_number}</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel this order? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="cancel-reason">Reason for cancellation (optional)</Label>
              <Textarea
                id="cancel-reason"
                placeholder="e.g., Customer requested cancellation"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
              />
            </div>
            {selectedOrder && (
              <div className="rounded-lg bg-muted p-3 text-sm">
                <p className="font-medium">Order details:</p>
                <p>Customer: {selectedOrder.customer_name}</p>
                <p>Total: {formatCurrency(selectedOrder.total)}</p>
                <p>Items: {selectedOrder.items.length}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
              Keep Order
            </Button>
            <Button
              variant="destructive"
              onClick={confirmCancel}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Cancel Order
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
