/**
 * OrderDetail Component
 *
 * Displays full details of a single order including customer info,
 * shipping address, items, and order timeline.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from '@tanstack/react-router'
import { useState } from 'react'
import {
  ArrowLeft,
  Package,
  Truck,
  CheckCircle,
  Clock,
  RefreshCw,
  XCircle,
  Mail,
  Phone,
  MapPin,
  CreditCard,
  Loader2,
  ExternalLink,
} from 'lucide-react'

import { getOrder, shipOrder, deliverOrder, updateOrder } from '@/lib/api/orders'
import { useCurrency } from '@/hooks/useCurrency'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
  pending: <Clock className="h-4 w-4" />,
  processing: <RefreshCw className="h-4 w-4" />,
  shipped: <Truck className="h-4 w-4" />,
  delivered: <CheckCircle className="h-4 w-4" />,
  cancelled: <XCircle className="h-4 w-4" />,
  refunded: <RefreshCw className="h-4 w-4" />,
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

export function OrderDetail() {
  const { orderId } = useParams({ from: '/orders/$orderId' })
  const queryClient = useQueryClient()
  const { formatCurrency } = useCurrency()

  const [shipDialogOpen, setShipDialogOpen] = useState(false)
  const [trackingNumber, setTrackingNumber] = useState('')
  const [trackingUrl, setTrackingUrl] = useState('')
  const [notesDialogOpen, setNotesDialogOpen] = useState(false)
  const [internalNotes, setInternalNotes] = useState('')

  const { data: order, isLoading, error } = useQuery({
    queryKey: ['order', orderId],
    queryFn: () => getOrder(orderId),
  })

  const shipMutation = useMutation({
    mutationFn: (data: { tracking_number?: string; tracking_url?: string }) =>
      shipOrder(orderId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      setShipDialogOpen(false)
      setTrackingNumber('')
      setTrackingUrl('')
    },
  })

  const deliverMutation = useMutation({
    mutationFn: () => deliverOrder(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: { internal_notes?: string }) => updateOrder(orderId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] })
      setNotesDialogOpen(false)
    },
  })

  const handleShip = () => {
    shipMutation.mutate({
      tracking_number: trackingNumber || undefined,
      tracking_url: trackingUrl || undefined,
    })
  }

  const handleSaveNotes = () => {
    updateMutation.mutate({ internal_notes: internalNotes })
  }

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading order</p>
          <p className="text-sm text-muted-foreground">{(error as Error)?.message || 'Order not found'}</p>
          <Link to="/orders">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Orders
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link to="/orders">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Order {order.order_number}</h2>
            <p className="text-muted-foreground">
              Placed on {formatDate(order.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={`${STATUS_COLORS[order.status]} flex items-center gap-1 text-sm px-3 py-1`}>
            {STATUS_ICONS[order.status]}
            {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Order Items */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Order Items
              </CardTitle>
              <CardDescription>
                {order.items.length} item{order.items.length !== 1 ? 's' : ''} in this order
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="divide-y">
                {order.items.map((item) => (
                  <div key={item.id} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex justify-between">
                      <div>
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-sm text-muted-foreground">
                          SKU: {item.product_sku || 'N/A'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatCurrency(item.total_price)}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.quantity} × {formatCurrency(item.unit_price)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span>{formatCurrency(order.subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Shipping ({order.shipping_method})</span>
                  <span>{order.shipping_cost === 0 ? 'Free' : formatCurrency(order.shipping_cost)}</span>
                </div>
                <div className="flex justify-between font-medium text-lg pt-2 border-t">
                  <span>Total</span>
                  <span>{formatCurrency(order.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Customer & Shipping */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Customer Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Customer</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{order.customer_name}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Mail className="h-4 w-4" />
                  <a href={`mailto:${order.customer_email}`} className="hover:underline">
                    {order.customer_email}
                  </a>
                </div>
                {order.customer_phone && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Phone className="h-4 w-4" />
                    <a href={`tel:${order.customer_phone}`} className="hover:underline">
                      {order.customer_phone}
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Shipping Address */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  Shipping Address
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm space-y-1">
                  <p>{order.customer_name}</p>
                  <p>{order.shipping_address_line1}</p>
                  {order.shipping_address_line2 && <p>{order.shipping_address_line2}</p>}
                  <p>{order.shipping_city}{order.shipping_county && `, ${order.shipping_county}`}</p>
                  <p>{order.shipping_postcode}</p>
                  <p>{order.shipping_country}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tracking Info (if shipped) */}
          {(order.status === 'shipped' || order.status === 'delivered') && order.tracking_number && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Truck className="h-4 w-4" />
                  Tracking Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-mono text-lg">{order.tracking_number}</p>
                    {order.shipped_at && (
                      <p className="text-sm text-muted-foreground">
                        Shipped on {formatDate(order.shipped_at)}
                      </p>
                    )}
                  </div>
                  {order.tracking_url && (
                    <a href={order.tracking_url} target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" size="sm">
                        Track Package
                        <ExternalLink className="ml-2 h-4 w-4" />
                      </Button>
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {(order.status === 'pending' || order.status === 'processing') && (
                <Button
                  className="w-full"
                  onClick={() => setShipDialogOpen(true)}
                  disabled={shipMutation.isPending}
                >
                  <Truck className="mr-2 h-4 w-4" />
                  Mark as Shipped
                </Button>
              )}
              {order.status === 'shipped' && (
                <Button
                  className="w-full"
                  onClick={() => deliverMutation.mutate()}
                  disabled={deliverMutation.isPending}
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Mark as Delivered
                </Button>
              )}
              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setInternalNotes(order.internal_notes || '')
                  setNotesDialogOpen(true)
                }}
              >
                Edit Notes
              </Button>
            </CardContent>
          </Card>

          {/* Payment Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CreditCard className="h-4 w-4" />
                Payment
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Provider</span>
                <span className="capitalize">{order.payment_provider}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant="outline" className="capitalize">
                  {order.payment_status}
                </Badge>
              </div>
              {order.payment_id && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">ID</span>
                  <span className="font-mono text-xs truncate max-w-[150px]" title={order.payment_id}>
                    {order.payment_id}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Internal Notes */}
          {order.internal_notes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Internal Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap">{order.internal_notes}</p>
              </CardContent>
            </Card>
          )}

          {/* Customer Notes */}
          {order.customer_notes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Customer Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap">{order.customer_notes}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Ship Dialog */}
      <Dialog open={shipDialogOpen} onOpenChange={setShipDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ship Order {order.order_number}</DialogTitle>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShipDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleShip} disabled={shipMutation.isPending}>
              {shipMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Mark as Shipped
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Notes Dialog */}
      <Dialog open={notesDialogOpen} onOpenChange={setNotesDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Internal Notes</DialogTitle>
            <DialogDescription>
              Add notes for internal use. These won't be visible to customers.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Add internal notes..."
              value={internalNotes}
              onChange={(e) => setInternalNotes(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNotesDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveNotes} disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Notes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
