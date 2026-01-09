/**
 * Sales Channels Page
 *
 * List page for all sales channels.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { SalesChannelList } from '@/components/sales-channels/SalesChannelList'

export function SalesChannels() {
  return (
    <AppLayout>
      <SalesChannelList />
    </AppLayout>
  )
}
