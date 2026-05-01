/**
 * OrderCreateForm Component
 *
 * Form for creating manual admin orders.
 */

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { AlertCircle, Loader2, Plus, Trash2 } from 'lucide-react'

import { createOrder, type CreateOrderRequest } from '@/lib/api/orders'
import { listProducts, type Product } from '@/lib/api/products'
import { listSalesChannels } from '@/lib/api/sales-channels'
import { useCurrency } from '@/hooks/useCurrency'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'

type OrderLine = {
  product_id: string
  quantity: string
  unit_price: string
}

const emptyLine = (): OrderLine => ({
  product_id: '',
  quantity: '1',
  unit_price: '',
})

function toMoney(value: string): number {
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? Math.round(parsed * 100) / 100 : 0
}

function toQuantity(value: string): number {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1
}

function productLabel(product: Product): string {
  return `${product.sku} - ${product.name}`
}

export function OrderCreateForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { formatCurrency } = useCurrency()

  const [customerEmail, setCustomerEmail] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [addressLine1, setAddressLine1] = useState('')
  const [addressLine2, setAddressLine2] = useState('')
  const [city, setCity] = useState('')
  const [county, setCounty] = useState('')
  const [postcode, setPostcode] = useState('')
  const [country, setCountry] = useState('United Kingdom')
  const [shippingMethod, setShippingMethod] = useState('')
  const [shippingCost, setShippingCost] = useState('0.00')
  const [salesChannelId, setSalesChannelId] = useState('')
  const [paymentStatus, setPaymentStatus] = useState<'pending' | 'completed'>('completed')
  const [paymentReference, setPaymentReference] = useState('')
  const [customerNotes, setCustomerNotes] = useState('')
  const [internalNotes, setInternalNotes] = useState('')
  const [lines, setLines] = useState<OrderLine[]>([emptyLine()])

  const productsQuery = useQuery({
    queryKey: ['products', 'order-create'],
    queryFn: () => listProducts({ skip: 0, limit: 100, is_active: true }),
  })

  const channelsQuery = useQuery({
    queryKey: ['sales-channels', 'order-create'],
    queryFn: () => listSalesChannels({ skip: 0, limit: 100, is_active: true }),
  })

  const products = productsQuery.data?.products ?? []
  const channels = channelsQuery.data?.channels ?? []

  const subtotal = useMemo(
    () => lines.reduce((sum, line) => sum + toMoney(line.unit_price) * toQuantity(line.quantity), 0),
    [lines],
  )
  const total = subtotal + toMoney(shippingCost)

  const mutation = useMutation({
    mutationFn: (data: CreateOrderRequest) => createOrder(data),
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['orderCounts'] })
      navigate({ to: '/orders/$orderId', params: { orderId: order.id } })
    },
  })

  const updateLine = (index: number, values: Partial<OrderLine>) => {
    setLines((current) =>
      current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...values } : line)),
    )
  }

  const removeLine = (index: number) => {
    setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))
  }

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    mutation.mutate({
      customer_email: customerEmail.trim(),
      customer_name: customerName.trim(),
      customer_phone: customerPhone.trim() || undefined,
      shipping_address_line1: addressLine1.trim(),
      shipping_address_line2: addressLine2.trim() || undefined,
      shipping_city: city.trim(),
      shipping_county: county.trim() || undefined,
      shipping_postcode: postcode.trim(),
      shipping_country: country.trim(),
      shipping_method: shippingMethod.trim(),
      shipping_cost: toMoney(shippingCost),
      sales_channel_id: salesChannelId,
      payment_provider: 'manual',
      payment_status: paymentStatus,
      payment_id: paymentReference.trim() || undefined,
      customer_notes: customerNotes.trim() || undefined,
      internal_notes: internalNotes.trim() || undefined,
      items: lines.map((line) => ({
        product_id: line.product_id,
        quantity: toQuantity(line.quantity),
        unit_price: toMoney(line.unit_price),
      })),
    })
  }

  const isLoading = productsQuery.isLoading || channelsQuery.isLoading
  const loadError = productsQuery.error || channelsQuery.error
  const canSubmit = !isLoading && products.length > 0 && channels.length > 0 && !mutation.isPending

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (loadError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>Unable to load products or sales channels.</AlertDescription>
      </Alert>
    )
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      {mutation.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Unable to create order. Check the details and try again.</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Customer</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="customer-email">Customer email</Label>
                <Input
                  id="customer-email"
                  type="email"
                  value={customerEmail}
                  onChange={(event) => setCustomerEmail(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="customer-name">Customer name</Label>
                <Input
                  id="customer-name"
                  value={customerName}
                  onChange={(event) => setCustomerName(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="customer-phone">Customer phone</Label>
                <Input
                  id="customer-phone"
                  value={customerPhone}
                  onChange={(event) => setCustomerPhone(event.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Shipping</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="address-line-1">Address line 1</Label>
                <Input
                  id="address-line-1"
                  value={addressLine1}
                  onChange={(event) => setAddressLine1(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="address-line-2">Address line 2</Label>
                <Input
                  id="address-line-2"
                  value={addressLine2}
                  onChange={(event) => setAddressLine2(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  value={city}
                  onChange={(event) => setCity(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="county">County</Label>
                <Input id="county" value={county} onChange={(event) => setCounty(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="postcode">Postcode</Label>
                <Input
                  id="postcode"
                  value={postcode}
                  onChange={(event) => setPostcode(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="country">Country</Label>
                <Input
                  id="country"
                  value={country}
                  onChange={(event) => setCountry(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="shipping-method">Shipping method</Label>
                <Input
                  id="shipping-method"
                  value={shippingMethod}
                  onChange={(event) => setShippingMethod(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="shipping-cost">Shipping cost</Label>
                <Input
                  id="shipping-cost"
                  type="number"
                  min="0"
                  step="0.01"
                  value={shippingCost}
                  onChange={(event) => setShippingCost(event.target.value)}
                  required
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <CardTitle>Items</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={() => setLines([...lines, emptyLine()])}>
                <Plus className="mr-2 h-4 w-4" />
                Add Item
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {lines.map((line, index) => (
                <div key={index} className="grid gap-4 rounded-md border p-4 md:grid-cols-[1fr_120px_140px_auto]">
                  <div className="space-y-2">
                    <Label htmlFor={`product-${index}`}>Product</Label>
                    <Select value={line.product_id} onValueChange={(value) => updateLine(index, { product_id: value })}>
                      <SelectTrigger id={`product-${index}`} aria-label="Product">
                        <SelectValue placeholder="Select product" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map((product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {productLabel(product)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`quantity-${index}`}>Quantity</Label>
                    <Input
                      id={`quantity-${index}`}
                      type="number"
                      min="1"
                      value={line.quantity}
                      onChange={(event) => updateLine(index, { quantity: event.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`unit-price-${index}`}>Unit price</Label>
                    <Input
                      id={`unit-price-${index}`}
                      type="number"
                      min="0"
                      step="0.01"
                      value={line.unit_price}
                      onChange={(event) => updateLine(index, { unit_price: event.target.value })}
                      required
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeLine(index)}
                      disabled={lines.length === 1}
                      aria-label="Remove item"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Payment</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="sales-channel">Sales channel</Label>
                <Select value={salesChannelId} onValueChange={setSalesChannelId} required>
                  <SelectTrigger id="sales-channel" aria-label="Sales channel">
                    <SelectValue placeholder="Select sales channel" />
                  </SelectTrigger>
                  <SelectContent>
                    {channels.map((channel) => (
                      <SelectItem key={channel.id} value={channel.id}>
                        {channel.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="payment-status">Payment status</Label>
                <Select value={paymentStatus} onValueChange={(value) => setPaymentStatus(value as 'pending' | 'completed')}>
                  <SelectTrigger id="payment-status" aria-label="Payment status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="payment-reference">Payment reference</Label>
                <Input
                  id="payment-reference"
                  value={paymentReference}
                  onChange={(event) => setPaymentReference(event.target.value)}
                  placeholder="Cash receipt, bank transfer, or external reference"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="customer-notes">Customer notes</Label>
                <Textarea
                  id="customer-notes"
                  value={customerNotes}
                  onChange={(event) => setCustomerNotes(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="internal-notes">Internal notes</Label>
                <Textarea
                  id="internal-notes"
                  value={internalNotes}
                  onChange={(event) => setInternalNotes(event.target.value)}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit lg:sticky lg:top-6">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span>{formatCurrency(subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Shipping</span>
              <span>{formatCurrency(toMoney(shippingCost))}</span>
            </div>
            <Separator />
            <div className="flex justify-between text-lg font-semibold">
              <span>Total</span>
              <span>{formatCurrency(total)}</span>
            </div>
            <Button type="submit" className="w-full" disabled={!canSubmit}>
              {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Order
            </Button>
          </CardContent>
        </Card>
      </div>
    </form>
  )
}
