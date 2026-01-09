/**
 * Models List Page
 *
 * Displays the model catalog (printed items with BOM) with filtering and pagination.
 */

import { ModelList } from '@/components/models/ModelList'
import { AppLayout } from '@/components/layout/AppLayout'

export function Models() {
  return (
    <AppLayout>
      <ModelList />
    </AppLayout>
  )
}
