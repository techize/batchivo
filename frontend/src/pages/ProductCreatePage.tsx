/**
 * Product Create Page
 *
 * Page for creating new products.
 */

import { ProductForm } from '@/components/products/ProductForm'
import { AppLayout } from '@/components/layout/AppLayout'

export function ProductCreatePage() {
  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Create Product</h1>
          <p className="text-muted-foreground">Add a new product to your catalog</p>
        </div>
        <ProductForm mode="create" />
      </div>
    </AppLayout>
  )
}
