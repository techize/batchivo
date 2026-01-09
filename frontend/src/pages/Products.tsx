/**
 * Products List Page
 *
 * Displays the product catalog with filtering and pagination.
 */

import { ProductList } from '@/components/products/ProductList'
import { AppLayout } from '@/components/layout/AppLayout'

export function Products() {
  return (
    <AppLayout>
      <ProductList />
    </AppLayout>
  )
}
