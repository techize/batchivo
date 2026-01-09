/**
 * Model Detail Page
 *
 * Displays full model information with BOM (materials), components, and cost breakdown.
 * Models are printed items with bill of materials.
 */

import { ModelDetail } from '@/components/models/ModelDetail'
import { AppLayout } from '@/components/layout/AppLayout'
import { useParams } from '@tanstack/react-router'

export function ModelDetailPage() {
  const { modelId } = useParams({ from: '/models/$modelId' })

  return (
    <AppLayout>
      <ModelDetail modelId={modelId} />
    </AppLayout>
  )
}
