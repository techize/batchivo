/**
 * ProductDetail Component
 *
 * Displays full product information including models composition,
 * per-channel pricing with profit calculations, and cost breakdown.
 * Products are sellable items composed of one or more Models.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import DOMPurify from 'dompurify'
import {
  ArrowLeft,
  Edit,
  Loader2,
  Trash2,
  Package,
  Layers,
  DollarSign,
  Calculator,
  ShoppingCart,
  TrendingUp,
  Clock,
  Box,
  ImageIcon,
  History,
} from 'lucide-react'

import {
  getProduct,
  deleteProduct,
  formatCurrency,
} from '@/lib/api/products'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { ProductModelsEditor } from './ProductModelsEditor'
import { ProductComponentsEditor } from './ProductComponentsEditor'
import { ProductPricingEditor } from './ProductPricingEditor'
import { ProductImagesEditor } from './ProductImagesEditor'
import { ProductCategoriesEditor } from './ProductCategoriesEditor'
import { ProductionHistoryTable } from './ProductionHistoryTable'

interface ProductDetailProps {
  productId: string
}

function StatCard({
  label,
  value,
  subValue,
  icon: Icon,
}: {
  label: string
  value: string
  subValue?: string
  icon?: React.ElementType
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {Icon && <Icon className="h-4 w-4" />}
        {label}
      </div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      {subValue && <div className="text-xs text-muted-foreground mt-1">{subValue}</div>}
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string | React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export function ProductDetail({ productId }: ProductDetailProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: product, isLoading, error } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => getProduct(productId),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteProduct(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      navigate({ to: '/products' })
    },
  })

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3">Loading product...</span>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading product</p>
          <p className="text-sm text-muted-foreground">
            {error ? (error as Error).message : 'Product not found'}
          </p>
        </div>
      </div>
    )
  }

  // Parse cost breakdown
  const costBreakdown = product.cost_breakdown
  const modelsCost = parseFloat(costBreakdown?.models_cost || '0')
  const childProductsCost = parseFloat(costBreakdown?.child_products_cost || '0')
  const packagingCost = parseFloat(costBreakdown?.packaging_cost || '0')
  const assemblyCost = parseFloat(costBreakdown?.assembly_cost || '0')
  const totalMakeCost = parseFloat(costBreakdown?.total_make_cost || '0')

  // Check if this is a bundle (has child products)
  const hasChildProducts = (product.child_products?.length || 0) > 0

  // Calculate suggested retail prices using common pricing formulas
  // 2.5x markup (150% profit margin) - common for handmade/craft items
  const recommendedPrice = totalMakeCost * 2.5
  // Alternative: 40% profit margin formula: cost / (1 - 0.40) = cost / 0.60
  const marginBasedPrice = totalMakeCost / 0.60
  // 3x markup for premium pricing
  const premiumPrice = totalMakeCost * 3.0

  // Find best pricing (highest margin)
  const activePricing = product.pricing?.filter((p) => p.is_active) || []
  const bestPricing = activePricing.reduce(
    (best, current) => {
      const currentMargin = parseFloat(current.margin_percentage || '0')
      const bestMargin = parseFloat(best?.margin_percentage || '0')
      return currentMargin > bestMargin ? current : best
    },
    activePricing[0] || null
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/products">
                <ArrowLeft className="mr-1 h-4 w-4" />
                Products
              </Link>
            </Button>
            <span>/</span>
            <span className="font-mono">{product.sku}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{product.name}</h1>
          <div className="flex items-center gap-2 mt-2">
            <Badge
              variant="outline"
              className={
                product.is_active
                  ? 'bg-green-500/10 text-green-600 border-green-200'
                  : 'bg-gray-500/10 text-gray-500 border-gray-200'
              }
            >
              {product.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Badge variant="outline">
              <Layers className="mr-1 h-3 w-3" />
              {product.models?.length || 0} models
            </Badge>
            {hasChildProducts && (
              <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-200">
                <Package className="mr-1 h-3 w-3" />
                {product.child_products?.length || 0} bundled
              </Badge>
            )}
            <Badge variant="outline">
              <ShoppingCart className="mr-1 h-3 w-3" />
              {activePricing.length} channels
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/products/$productId/edit" params={{ productId }}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="icon">
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Product</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete this product? This will set is_active to false.
                  This action can be reversed by editing the product.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => deleteMutation.mutate()}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Cost Breakdown Stats Grid */}
      <div className={`grid grid-cols-2 gap-4 ${hasChildProducts ? 'md:grid-cols-5' : 'md:grid-cols-4'}`}>
        <StatCard
          icon={Layers}
          label="Models Cost"
          value={formatCurrency(modelsCost)}
          subValue={`${product.models?.length || 0} model${product.models?.length !== 1 ? 's' : ''}`}
        />
        {hasChildProducts && (
          <StatCard
            icon={Package}
            label="Child Products"
            value={formatCurrency(childProductsCost)}
            subValue={`${product.child_products?.length || 0} product${product.child_products?.length !== 1 ? 's' : ''}`}
          />
        )}
        <StatCard
          icon={Box}
          label="Packaging"
          value={formatCurrency(packagingCost)}
        />
        <StatCard
          icon={Clock}
          label="Assembly"
          value={formatCurrency(assemblyCost)}
          subValue={`${product.assembly_minutes || 0} min @ £10/hr`}
        />
        <StatCard
          icon={Calculator}
          label="Total Make Cost"
          value={formatCurrency(totalMakeCost)}
        />
      </div>

      {/* Suggested Retail Pricing */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          icon={TrendingUp}
          label="Recommended Price"
          value={formatCurrency(recommendedPrice)}
          subValue="2.5× markup (150% margin)"
        />
        <StatCard
          label="Alternative Price"
          value={formatCurrency(marginBasedPrice)}
          subValue="40% profit margin"
        />
        <StatCard
          label="Premium Price"
          value={formatCurrency(premiumPrice)}
          subValue="3× markup (200% margin)"
        />
      </div>

      {/* Pricing Stats Grid */}
      {bestPricing && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon={DollarSign}
            label="Best Price"
            value={formatCurrency(bestPricing.list_price)}
            subValue={bestPricing.channel_name}
          />
          <StatCard
            icon={TrendingUp}
            label="Net Revenue"
            value={formatCurrency(bestPricing.net_revenue || '0')}
            subValue={`After ${bestPricing.platform_type} fees`}
          />
          <StatCard
            label="Profit"
            value={formatCurrency(bestPricing.profit || '0')}
            subValue="After all costs"
          />
          <StatCard
            label="Margin"
            value={`${parseFloat(bestPricing.margin_percentage || '0').toFixed(1)}%`}
            subValue="Profit margin"
          />
        </div>
      )}

      {/* Product Details Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Product Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {product.description && (
            <div className="pb-3 mb-3 border-b">
              <span className="text-sm text-muted-foreground">Description</span>
              <div
                className="mt-1 prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(product.description) }}
              />
            </div>
          )}

          <DetailItem label="SKU" value={<span className="font-mono">{product.sku}</span>} />
          <DetailItem label="Units in Stock" value={product.units_in_stock?.toString() || '0'} />
          <DetailItem
            label="Packaging"
            value={
              product.packaging_consumable_name ? (
                <span>
                  {product.packaging_consumable_name}
                  {product.packaging_quantity > 1 && ` ×${product.packaging_quantity}`}
                  <span className="text-muted-foreground ml-1">
                    ({formatCurrency(product.cost_breakdown?.packaging_cost || '0')})
                  </span>
                </span>
              ) : (
                formatCurrency(product.packaging_cost || '0')
              )
            }
          />
          <DetailItem
            label="Assembly Time"
            value={`${product.assembly_minutes || 0} minutes`}
          />

          <div className="pt-3 mt-3 border-t grid grid-cols-2 gap-4 text-xs text-muted-foreground">
            <div>
              <span>Created</span>
              <p className="font-medium text-foreground">
                {new Date(product.created_at).toLocaleDateString()}
              </p>
            </div>
            <div>
              <span>Last Updated</span>
              <p className="font-medium text-foreground">
                {new Date(product.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Product Images */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="h-5 w-5" />
            Product Images
          </CardTitle>
          <CardDescription>
            Images for shop display. First image is the primary (shown in listings).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProductImagesEditor productId={productId} />
        </CardContent>
      </Card>

      {/* Categories */}
      <ProductCategoriesEditor productId={productId} categories={product.categories || []} />

      {/* Models Composition */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            Models Composition
          </CardTitle>
          <CardDescription>
            Models that make up this product with quantities
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProductModelsEditor productId={productId} models={product.models || []} />
        </CardContent>
      </Card>

      {/* Child Products (Bundle Composition) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Bundled Products
          </CardTitle>
          <CardDescription>
            Other products included in this bundle (for sets and combos)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProductComponentsEditor productId={productId} components={product.child_products || []} />
        </CardContent>
      </Card>

      {/* Per-Channel Pricing */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Sales Channel Pricing
          </CardTitle>
          <CardDescription>
            Prices, fees, and profit by sales channel
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProductPricingEditor
            productId={productId}
            pricing={product.pricing || []}
            makeCost={totalMakeCost}
          />
        </CardContent>
      </Card>

      {/* Production History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Production History
          </CardTitle>
          <CardDescription>
            Production runs that include this product's models
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProductionHistoryTable
            productId={productId}
            modelIds={product.models?.map((m) => m.model_id) || []}
          />
        </CardContent>
      </Card>
    </div>
  )
}
