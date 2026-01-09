/**
 * Product Edit Page
 *
 * Page for editing existing products (basic info).
 * Model composition and pricing are managed on the detail page.
 */

import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from '@tanstack/react-router'
import { Loader2, ArrowLeft } from 'lucide-react'

import { getProduct } from '@/lib/api/products'
import { ProductForm } from '@/components/products/ProductForm'
import { AppLayout } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'

export function ProductEditPage() {
  const { productId } = useParams({ from: '/products/$productId/edit' })

  const { data: product, isLoading, error } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => getProduct(productId),
  })

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      </AppLayout>
    )
  }

  if (error || !product) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-[400px]">
          <div className="text-center">
            <p className="text-lg font-semibold text-destructive">Error loading product</p>
            <p className="text-sm text-muted-foreground">
              {error ? (error as Error).message : 'Product not found'}
            </p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/products/$productId" params={{ productId }}>
                <ArrowLeft className="mr-1 h-4 w-4" />
                Back to Product
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Edit Product</h1>
          <p className="text-muted-foreground">
            Update basic product information. To manage models or pricing, return to the product detail page.
          </p>
        </div>

        {/* Product Information Form */}
        <ProductForm mode="edit" product={product} />
      </div>
    </AppLayout>
  )
}
