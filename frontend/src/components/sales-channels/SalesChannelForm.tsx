/**
 * SalesChannelForm Component
 *
 * Form for creating and editing sales channels.
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Loader2 } from 'lucide-react'

import {
  createSalesChannel,
  updateSalesChannel,
  getPlatformDisplayName,
  type SalesChannel,
  type SalesChannelCreateRequest,
  type SalesChannelUpdateRequest,
  type PlatformType,
} from '@/lib/api/sales-channels'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const PLATFORM_TYPES: PlatformType[] = [
  'fair',
  'online_shop',
  'shopify',
  'ebay',
  'etsy',
  'amazon',
  'other',
]

const salesChannelFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200, 'Name must be 200 characters or less'),
  platform_type: z.enum(['fair', 'online_shop', 'shopify', 'ebay', 'etsy', 'amazon', 'other']),
  fee_percentage: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, 'Must be a valid percentage')
    .optional()
    .default('0'),
  fee_fixed: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, 'Must be a valid amount')
    .optional()
    .default('0'),
  monthly_cost: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, 'Must be a valid amount')
    .optional()
    .default('0'),
  is_active: z.boolean().optional().default(true),
})

type SalesChannelFormValues = z.infer<typeof salesChannelFormSchema>

interface SalesChannelFormProps {
  channel?: SalesChannel
  mode: 'create' | 'edit'
}

export function SalesChannelForm({ channel, mode }: SalesChannelFormProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const form = useForm<SalesChannelFormValues>({
    resolver: zodResolver(salesChannelFormSchema),
    defaultValues: {
      name: channel?.name || '',
      platform_type: channel?.platform_type || 'other',
      fee_percentage: channel?.fee_percentage || '0',
      fee_fixed: channel?.fee_fixed || '0',
      monthly_cost: channel?.monthly_cost || '0',
      is_active: channel?.is_active ?? true,
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: SalesChannelCreateRequest) => createSalesChannel(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sales-channels'] })
      navigate({ to: '/sales-channels/$channelId', params: { channelId: data.id } })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: SalesChannelUpdateRequest) => updateSalesChannel(channel!.id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sales-channels'] })
      queryClient.invalidateQueries({ queryKey: ['sales-channel', channel!.id] })
      navigate({ to: '/sales-channels/$channelId', params: { channelId: data.id } })
    },
  })

  const onSubmit = (values: SalesChannelFormValues) => {
    const data = {
      name: values.name,
      platform_type: values.platform_type,
      fee_percentage: values.fee_percentage || '0',
      fee_fixed: values.fee_fixed || '0',
      monthly_cost: values.monthly_cost || '0',
      is_active: values.is_active,
    }

    if (mode === 'create') {
      createMutation.mutate(data)
    } else {
      updateMutation.mutate(data)
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  // Live fee preview
  const watchFeePercentage = form.watch('fee_percentage')
  const watchFeeFixed = form.watch('fee_fixed')
  const exampleSale = 20
  const feePercentage = parseFloat(watchFeePercentage || '0')
  const feeFixed = parseFloat(watchFeeFixed || '0')
  const totalFee = (exampleSale * feePercentage / 100) + feeFixed
  const netAmount = exampleSale - totalFee

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Channel Information</CardTitle>
            <CardDescription>Basic details about this sales channel</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Local Craft Fair" {...field} />
                    </FormControl>
                    <FormDescription>Display name for this channel</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="platform_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Platform Type</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select platform type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {PLATFORM_TYPES.map((type) => (
                          <SelectItem key={type} value={type}>
                            {getPlatformDisplayName(type)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>Type of sales platform</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
        </Card>

        {/* Fee Structure */}
        <Card>
          <CardHeader>
            <CardTitle>Fee Structure</CardTitle>
            <CardDescription>
              Configure fees for this channel. Total fee = (sale × percentage) + fixed fee.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <FormField
                control={form.control}
                name="fee_percentage"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fee Percentage (%)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" min="0" max="100" placeholder="0" {...field} />
                    </FormControl>
                    <FormDescription>Percentage of each sale</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="fee_fixed"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fixed Fee (£)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" min="0" placeholder="0.00" {...field} />
                    </FormControl>
                    <FormDescription>Fixed amount per sale</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="monthly_cost"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Monthly Cost (£)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" min="0" placeholder="0.00" {...field} />
                    </FormControl>
                    <FormDescription>Subscription/booth fee</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Fee Preview */}
            <div className="rounded-lg border bg-muted/50 p-4">
              <div className="text-sm font-medium mb-2">Fee Preview (£{exampleSale} sale)</div>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-xs text-muted-foreground">Total Fee</div>
                  <div className="font-semibold">£{totalFee.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Net Amount</div>
                  <div className="font-semibold text-green-600">£{netAmount.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Effective Rate</div>
                  <div className="font-semibold">{((totalFee / exampleSale) * 100).toFixed(1)}%</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Status - only show in edit mode */}
        {mode === 'edit' && (
          <Card>
            <CardContent className="pt-6">
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Active Status</FormLabel>
                      <FormDescription>
                        Inactive channels are hidden from pricing options
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              navigate({
                to: channel ? `/sales-channels/${channel.id}` : '/sales-channels',
              })
            }
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === 'create' ? 'Create Channel' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </Form>
  )
}
