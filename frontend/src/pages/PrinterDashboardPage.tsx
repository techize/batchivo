/**
 * PrinterDashboardPage — live fleet monitoring page.
 *
 * Route: /dashboard/printers
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { PrinterDashboard } from '@/components/printers/PrinterDashboard'

export function PrinterDashboardPage() {
  return (
    <AppLayout>
      <PrinterDashboard />
    </AppLayout>
  )
}
