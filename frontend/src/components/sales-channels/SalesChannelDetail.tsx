/**
 * SalesChannelDetail Component
 *
 * Displays full sales channel information including fee structure.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Edit, Loader2, Trash2, Store, DollarSign, Percent, Calendar, AlertTriangle } from 'lucide-react'

import {
  getSalesChannel,
  deleteSalesChannel,
  getPlatformDisplayName,
  getPlatformColor,
} from '@/lib/api/sales-channels'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardHeader } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

interface SalesChannelDetailProps {
  channelId: string
}

function StatCard({
  label,
  value,
  subValue,
  icon: Icon,
}: {
  label: string
  value: string
  subValue?: string
  icon?: React.ElementType
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {Icon && <Icon className="h-4 w-4" />}
        {label}
      </div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      {subValue && <div className="text-xs text-muted-foreground mt-1">{subValue}</div>}
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string | React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export function SalesChannelDetail({ channelId }: SalesChannelDetailProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  const { data: channel, isLoading, error } = useQuery({
    queryKey: ['sales-channel', channelId],
    queryFn: () => getSalesChannel(channelId),
  })

  const deleteMutation = useMutation({
    mutationFn: (permanent: boolean) => deleteSalesChannel(channelId, permanent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-channels'] })
      setDeleteDialogOpen(false)
      navigate({ to: '/sales-channels' })
    },
  })

  const formatCurrency = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    return `£${numValue.toFixed(2)}`
  }

  const formatPercentage = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    return `${numValue.toFixed(1)}%`
  }

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3">Loading channel...</span>
      </div>
    )
  }

  if (error || !channel) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading channel</p>
          <p className="text-sm text-muted-foreground">
            {error ? (error as Error).message : 'Channel not found'}
          </p>
        </div>
      </div>
    )
  }

  // Calculate example fee for a £20 sale
  const exampleSale = 20
  const feePercentage = parseFloat(channel.fee_percentage || '0')
  const feeFixed = parseFloat(channel.fee_fixed || '0')
  const totalFee = (exampleSale * feePercentage / 100) + feeFixed
  const netAmount = exampleSale - totalFee

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/sales-channels">
                <ArrowLeft className="mr-1 h-4 w-4" />
                Sales Channels
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{channel.name}</h1>
          <div className="flex items-center gap-2 mt-2">
            <Badge
              variant="outline"
              className={
                channel.is_active
                  ? 'bg-green-500/10 text-green-600 border-green-200'
                  : 'bg-gray-500/10 text-gray-500 border-gray-200'
              }
            >
              {channel.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Badge variant="outline" className={getPlatformColor(channel.platform_type)}>
              {getPlatformDisplayName(channel.platform_type)}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/sales-channels/$channelId/edit" params={{ channelId }}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="icon">
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Channel</AlertDialogTitle>
                <AlertDialogDescription>
                  Choose how to handle this sales channel:
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="space-y-3 py-4">
                <Button
                  variant="outline"
                  className="w-full justify-start h-auto py-3"
                  onClick={() => deleteMutation.mutate(false)}
                  disabled={deleteMutation.isPending}
                >
                  <div className="text-left">
                    <div className="font-medium">Deactivate</div>
                    <div className="text-sm text-muted-foreground">
                      Sets is_active to false. Channel can be reactivated later.
                    </div>
                  </div>
                </Button>
                <Button
                  variant="destructive"
                  className="w-full justify-start h-auto py-3"
                  onClick={() => deleteMutation.mutate(true)}
                  disabled={deleteMutation.isPending}
                >
                  <AlertTriangle className="mr-2 h-4 w-4 flex-shrink-0" />
                  <div className="text-left">
                    <div className="font-medium">Permanently Delete</div>
                    <div className="text-sm opacity-90">
                      Removes from database. This cannot be undone.
                    </div>
                  </div>
                </Button>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
              </AlertDialogFooter>
              {deleteMutation.isPending && (
                <div className="absolute inset-0 flex items-center justify-center bg-background/80">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              )}
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Fee Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Percent}
          label="Fee Percentage"
          value={formatPercentage(channel.fee_percentage)}
          subValue="Per sale"
        />
        <StatCard
          icon={DollarSign}
          label="Fixed Fee"
          value={formatCurrency(channel.fee_fixed)}
          subValue="Per sale"
        />
        <StatCard
          icon={Calendar}
          label="Monthly Cost"
          value={formatCurrency(channel.monthly_cost)}
          subValue="Subscription/booth fee"
        />
        <StatCard
          icon={Store}
          label="Example (£20 sale)"
          value={formatCurrency(netAmount)}
          subValue={`After ${formatCurrency(totalFee)} fees`}
        />
      </div>

      {/* Channel Details Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Store className="h-5 w-5" />
            Channel Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <DetailItem label="Name" value={channel.name} />
          <DetailItem
            label="Platform"
            value={
              <Badge variant="outline" className={getPlatformColor(channel.platform_type)}>
                {getPlatformDisplayName(channel.platform_type)}
              </Badge>
            }
          />
          <DetailItem
            label="Status"
            value={
              <Badge
                variant="outline"
                className={
                  channel.is_active
                    ? 'bg-green-500/10 text-green-600 border-green-200'
                    : 'bg-gray-500/10 text-gray-500 border-gray-200'
                }
              >
                {channel.is_active ? 'Active' : 'Inactive'}
              </Badge>
            }
          />

          <div className="pt-3 mt-3 border-t grid grid-cols-2 gap-4 text-xs text-muted-foreground">
            <div>
              <span>Created</span>
              <p className="font-medium text-foreground">
                {new Date(channel.created_at).toLocaleDateString()}
              </p>
            </div>
            <div>
              <span>Last Updated</span>
              <p className="font-medium text-foreground">
                {new Date(channel.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Fee Calculator Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Fee Calculator
          </CardTitle>
          <CardDescription>
            See how fees affect different sale amounts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[10, 20, 30, 50].map((saleAmount) => {
              const fee = (saleAmount * feePercentage / 100) + feeFixed
              const net = saleAmount - fee
              const feePercent = (fee / saleAmount) * 100

              return (
                <div key={saleAmount} className="rounded-lg border p-3 text-center">
                  <div className="text-sm text-muted-foreground">
                    {formatCurrency(saleAmount)} sale
                  </div>
                  <div className="text-lg font-bold mt-1">{formatCurrency(net)}</div>
                  <div className="text-xs text-muted-foreground">
                    -{formatCurrency(fee)} ({feePercent.toFixed(1)}%)
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
