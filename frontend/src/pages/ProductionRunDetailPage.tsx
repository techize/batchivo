/**
 * Production Run Detail Page
 *
 * Detailed view of a single production run
 */

import { useParams } from '@tanstack/react-router'
import { ProductionRunDetail } from '@/components/production-runs/ProductionRunDetail'
import { AppLayout } from '@/components/layout/AppLayout'

export function ProductionRunDetailPage() {
  const { runId } = useParams({ from: '/production-runs/$runId' })

  return (
    <AppLayout>
      <ProductionRunDetail runId={runId} />
    </AppLayout>
  )
}
