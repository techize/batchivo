/**
 * Product Detail Page
 *
 * Displays full product information with BOM, components, and cost breakdown.
 */

import { ProductDetail } from '@/components/products/ProductDetail'
import { AppLayout } from '@/components/layout/AppLayout'
import { useParams } from '@tanstack/react-router'

export function ProductDetailPage() {
  const { productId } = useParams({ from: '/products/$productId' })

  return (
    <AppLayout>
      <ProductDetail productId={productId} />
    </AppLayout>
  )
}
