/**
 * Designers Page
 *
 * List page for managing licensed designers.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { DesignerList } from '@/components/designers/DesignerList'

export function Designers() {
  return (
    <AppLayout>
      <DesignerList />
    </AppLayout>
  )
}
