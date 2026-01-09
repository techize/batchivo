/**
 * Printers Page
 *
 * List page for all 3D printers.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { PrinterList } from '@/components/printers/PrinterList'

export function Printers() {
  return (
    <AppLayout>
      <PrinterList />
    </AppLayout>
  )
}
