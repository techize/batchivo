/**
 * Dashboard page - main app interface (protected route)
 */

import { SpoolList } from '@/components/inventory/SpoolList'
import { AppLayout } from '@/components/layout/AppLayout'

export function Dashboard() {
  return (
    <AppLayout>
      <SpoolList />
    </AppLayout>
  )
}
