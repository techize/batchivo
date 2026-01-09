/**
 * Production Run Create Page
 *
 * Page for creating a new production run using multi-step wizard
 */

import { CreateRunWizard } from '@/components/production-runs/CreateRunWizard'
import { AppLayout } from '@/components/layout/AppLayout'

export function ProductionRunCreatePage() {
  return (
    <AppLayout>
      <CreateRunWizard />
    </AppLayout>
  )
}
