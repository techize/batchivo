/**
 * Orders List Page
 *
 * Displays customer orders from sales channels.
 */

import { OrderList } from '@/components/orders/OrderList'
import { AppLayout } from '@/components/layout/AppLayout'

export function Orders() {
  return (
    <AppLayout>
      <OrderList />
    </AppLayout>
  )
}
