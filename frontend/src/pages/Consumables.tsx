/**
 * Consumables Inventory Page
 *
 * Displays the consumable inventory (magnets, inserts, hardware, etc.) with filtering and pagination.
 */

import { ConsumableList } from '@/components/inventory/ConsumableList'
import { AppLayout } from '@/components/layout/AppLayout'

export function Consumables() {
  return (
    <AppLayout>
      <ConsumableList />
    </AppLayout>
  )
}
