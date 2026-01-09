/**
 * Order Detail Page
 *
 * Displays full details of a single order.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { OrderDetail } from '@/components/orders/OrderDetail'

export function OrderDetailPage() {
  return (
    <AppLayout>
      <OrderDetail />
    </AppLayout>
  )
}
