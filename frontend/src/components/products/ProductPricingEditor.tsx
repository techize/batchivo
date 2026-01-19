/**
 * ProductPricingEditor Component
 *
 * Editor for managing per-channel product pricing.
 * Shows prices, fees, and profit calculations by sales channel.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { Loader2, Plus, Trash2, TrendingUp, TrendingDown, Edit } from 'lucide-react'

import {
  addProductPricing,
  updateProductPricing,
  removeProductPricing,
  type ProductPricing,
} from '@/lib/api/products'
import { useCurrency } from '@/hooks/useCurrency'
import { listSalesChannels } from '@/lib/api/sales-channels'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Switch } from '@/components/ui/switch'

const pricingFormSchema = z.object({
  sales_channel_id: z.string().uuid('Must select a sales channel'),
  list_price: z.string().regex(/^\d+(\.\d{1,2})?$/, 'Must be a valid price (e.g., 19.99)'),
  is_active: z.boolean().default(true),
})

type PricingFormValues = z.infer<typeof pricingFormSchema>

interface ProductPricingEditorProps {
  productId: string
  pricing: ProductPricing[]
  makeCost: number
}

export function ProductPricingEditor({ productId, pricing, makeCost }: ProductPricingEditorProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingPricing, setEditingPricing] = useState<ProductPricing | null>(null)
  const queryClient = useQueryClient()
  const { formatCurrency } = useCurrency()

  // Fetch available sales channels
  const { data: salesChannelsData } = useQuery({
    queryKey: ['sales-channels', { limit: 100 }],
    queryFn: () => listSalesChannels({ limit: 100 }),
  })

  const form = useForm<PricingFormValues>({
    resolver: zodResolver(pricingFormSchema),
    defaultValues: {
      sales_channel_id: '',
      list_price: '',
      is_active: true,
    },
  })

  const addMutation = useMutation({
    mutationFn: (data: PricingFormValues) =>
      addProductPricing(productId, {
        sales_channel_id: data.sales_channel_id,
        list_price: data.list_price,
        is_active: data.is_active,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      form.reset()
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ pricingId, data }: { pricingId: string; data: Partial<PricingFormValues> }) =>
      updateProductPricing(productId, pricingId, {
        list_price: data.list_price,
        is_active: data.is_active,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      setEditingPricing(null)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (pricingId: string) => removeProductPricing(productId, pricingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  const onSubmit = (values: PricingFormValues) => {
    if (editingPricing) {
      updateMutation.mutate({
        pricingId: editingPricing.id,
        data: values,
      })
    } else {
      addMutation.mutate(values)
    }
  }

  const handleEdit = (pricingItem: ProductPricing) => {
    setEditingPricing(pricingItem)
    form.reset({
      sales_channel_id: pricingItem.sales_channel_id,
      list_price: pricingItem.list_price,
      is_active: pricingItem.is_active,
    })
    setDialogOpen(true)
  }

  const handleDialogClose = () => {
    setDialogOpen(false)
    setEditingPricing(null)
    form.reset()
  }

  const handleToggleActive = (pricingItem: ProductPricing) => {
    updateMutation.mutate({
      pricingId: pricingItem.id,
      data: { is_active: !pricingItem.is_active },
    })
  }

  // Filter out channels that already have pricing (unless editing)
  const existingChannelIds = pricing
    .filter((p) => p.id !== editingPricing?.id)
    .map((p) => p.sales_channel_id)
  const selectableChannels =
    salesChannelsData?.channels?.filter((c) => !existingChannelIds.includes(c.id)) || []

  // Calculate averages
  const activePricing = pricing.filter((p) => p.is_active)
  const avgProfit =
    activePricing.length > 0
      ? activePricing.reduce((sum, p) => sum + parseFloat(p.profit || '0'), 0) / activePricing.length
      : 0
  const avgMargin =
    activePricing.length > 0
      ? activePricing.reduce((sum, p) => sum + parseFloat(p.margin_percentage || '0'), 0) /
        activePricing.length
      : 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground space-x-4">
          <span>
            Make Cost: <span className="font-semibold">{formatCurrency(makeCost)}</span>
          </span>
          {activePricing.length > 0 && (
            <>
              <span>•</span>
              <span>
                Avg Profit: <span className="font-semibold">{formatCurrency(avgProfit)}</span>
              </span>
              <span>•</span>
              <span>
                Avg Margin: <span className="font-semibold">{avgMargin.toFixed(1)}%</span>
              </span>
            </>
          )}
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => !open && handleDialogClose()}>
          <DialogTrigger asChild>
            <Button size="sm" onClick={() => {
              setEditingPricing(null)
              form.reset({
                sales_channel_id: '',
                list_price: '',
                is_active: true,
              })
              setDialogOpen(true)
            }}>
              <Plus className="mr-2 h-4 w-4" />
              Add Pricing
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>
                {editingPricing ? 'Edit Pricing' : 'Add Channel Pricing'}
              </DialogTitle>
              <DialogDescription>
                {editingPricing
                  ? 'Update the price for this sales channel'
                  : 'Set a price for a new sales channel'}
              </DialogDescription>
            </DialogHeader>

            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="sales_channel_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sales Channel</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                        disabled={!!editingPricing}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Choose a channel..." />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {editingPricing ? (
                            <SelectItem value={editingPricing.sales_channel_id}>
                              {editingPricing.channel_name}
                            </SelectItem>
                          ) : selectableChannels.length === 0 ? (
                            <SelectItem value="none" disabled>
                              No channels available
                            </SelectItem>
                          ) : (
                            selectableChannels.map((channel) => (
                              <SelectItem key={channel.id} value={channel.id}>
                                {channel.name} ({channel.platform_type})
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="list_price"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>List Price (£)</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.01" min="0" placeholder="19.99" {...field} />
                      </FormControl>
                      <FormDescription>
                        The selling price on this channel
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="is_active"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                      <div className="space-y-0.5">
                        <FormLabel>Active</FormLabel>
                        <FormDescription>
                          Whether this pricing is currently active
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleDialogClose}
                    disabled={addMutation.isPending || updateMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={
                      addMutation.isPending ||
                      updateMutation.isPending ||
                      (!editingPricing && selectableChannels.length === 0)
                    }
                  >
                    {(addMutation.isPending || updateMutation.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {editingPricing ? 'Update' : 'Add Pricing'}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {!pricing || pricing.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          No pricing set yet. Click "Add Pricing" to set prices for sales channels.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Channel</TableHead>
              <TableHead className="w-[100px] text-right">List Price</TableHead>
              <TableHead className="w-[100px] text-right">Fees</TableHead>
              <TableHead className="w-[100px] text-right">Net Revenue</TableHead>
              <TableHead className="w-[100px] text-right">Profit</TableHead>
              <TableHead className="w-[80px] text-right">Margin</TableHead>
              <TableHead className="w-[60px] text-center">Active</TableHead>
              <TableHead className="w-[80px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pricing.map((pricingItem) => {
              const profit = parseFloat(pricingItem.profit || '0')
              const margin = parseFloat(pricingItem.margin_percentage || '0')
              const isProfitable = profit > 0

              return (
                <TableRow key={pricingItem.id} className={!pricingItem.is_active ? 'opacity-50' : ''}>
                  <TableCell>
                    <div className="space-y-0.5">
                      <div className="font-medium">{pricingItem.channel_name || 'Unknown Channel'}</div>
                      <div className="text-xs text-muted-foreground">
                        {pricingItem.platform_type}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    {formatCurrency(pricingItem.list_price)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">
                    -{formatCurrency(pricingItem.platform_fee || '0')}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(pricingItem.net_revenue || '0')}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className={`flex items-center justify-end gap-1 tabular-nums font-semibold ${
                      isProfitable ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {isProfitable ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {formatCurrency(profit)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge
                      variant="outline"
                      className={
                        margin >= 30
                          ? 'bg-green-500/10 text-green-600 border-green-200'
                          : margin >= 15
                            ? 'bg-yellow-500/10 text-yellow-600 border-yellow-200'
                            : 'bg-red-500/10 text-red-600 border-red-200'
                      }
                    >
                      {margin.toFixed(1)}%
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={pricingItem.is_active}
                      onCheckedChange={() => handleToggleActive(pricingItem)}
                      disabled={updateMutation.isPending}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(pricingItem)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="sm" disabled={removeMutation.isPending}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Remove Pricing</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to remove pricing for "{pricingItem.channel_name}"?
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction onClick={() => removeMutation.mutate(pricingItem.id)}>
                              Remove
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
