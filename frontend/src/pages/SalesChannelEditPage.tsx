/**
 * Sales Channel Edit Page
 *
 * Page for editing an existing sales channel.
 */

import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from '@tanstack/react-router'
import { Loader2, ArrowLeft } from 'lucide-react'

import { getSalesChannel } from '@/lib/api/sales-channels'
import { SalesChannelForm } from '@/components/sales-channels/SalesChannelForm'
import { AppLayout } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'

export function SalesChannelEditPage() {
  const { channelId } = useParams({ from: '/sales-channels/$channelId/edit' })

  const { data: channel, isLoading, error } = useQuery({
    queryKey: ['sales-channel', channelId],
    queryFn: () => getSalesChannel(channelId),
  })

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      </AppLayout>
    )
  }

  if (error || !channel) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-[400px]">
          <div className="text-center">
            <p className="text-lg font-semibold text-destructive">Error loading channel</p>
            <p className="text-sm text-muted-foreground">
              {error ? (error as Error).message : 'Channel not found'}
            </p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/sales-channels/$channelId" params={{ channelId }}>
                <ArrowLeft className="mr-1 h-4 w-4" />
                Back to Channel
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Edit Sales Channel</h1>
          <p className="text-muted-foreground">
            Update channel settings and fee structure
          </p>
        </div>

        {/* Form */}
        <SalesChannelForm mode="edit" channel={channel} />
      </div>
    </AppLayout>
  )
}
