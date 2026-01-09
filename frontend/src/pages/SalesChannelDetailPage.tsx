/**
 * Sales Channel Detail Page
 *
 * Page for viewing sales channel details.
 */

import { useParams } from '@tanstack/react-router'

import { AppLayout } from '@/components/layout/AppLayout'
import { SalesChannelDetail } from '@/components/sales-channels/SalesChannelDetail'

export function SalesChannelDetailPage() {
  const { channelId } = useParams({ from: '/sales-channels/$channelId' })

  return (
    <AppLayout>
      <SalesChannelDetail channelId={channelId} />
    </AppLayout>
  )
}
