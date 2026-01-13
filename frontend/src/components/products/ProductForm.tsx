/**
 * ProductForm Component
 *
 * Form for creating and editing products (sellable items).
 * Products are composed of models with per-channel pricing.
 * Model composition and pricing are managed on the detail page.
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Loader2, Package, RefreshCw, X, Store, Star, Printer, Ruler, Scale, Clock } from 'lucide-react'

import { useNextSKU } from '@/hooks/useSKU'

import {
  createProduct,
  updateProduct,
  type ProductDetail,
  type ProductCreateRequest,
  type ProductUpdateRequest,
} from '@/lib/api/products'
import { consumablesApi } from '@/lib/api/consumables'
import { listDesigners } from '@/lib/api/designers'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { RichTextEditor } from '@/components/ui/rich-text-editor'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const productFormSchema = z.object({
  sku: z.string().min(1, 'SKU is required').max(100, 'SKU must be 100 characters or less'),
  name: z.string().min(1, 'Name is required').max(200, 'Name must be 200 characters or less'),
  description: z.string().optional(),
  packaging_cost: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, 'Must be a valid amount (e.g., 0.50)')
    .optional()
    .default('0'),
  packaging_consumable_id: z.string().optional(),
  packaging_quantity: z
    .string()
    .regex(/^\d+$/, 'Must be a valid number')
    .optional()
    .default('1'),
  assembly_minutes: z
    .string()
    .regex(/^\d+$/, 'Must be a valid number')
    .optional()
    .default('0'),
  units_in_stock: z
    .string()
    .regex(/^\d+$/, 'Must be a valid number')
    .optional()
    .default('0'),
  is_active: z.boolean().optional().default(true),
  // Shop display fields
  shop_visible: z.boolean().optional().default(false),
  shop_description: z.string().optional(),
  is_featured: z.boolean().optional().default(false),
  is_dragon: z.boolean().optional().default(false),
  feature_title: z.string().max(100, 'Must be 100 characters or less').optional(),
  backstory: z.string().optional(),
  print_to_order: z.boolean().optional().default(false),
  // Designer
  designer_id: z.string().optional(),
  // Product specifications
  weight_grams: z
    .string()
    .regex(/^\d*$/, 'Must be a valid number')
    .optional(),
  size_cm: z
    .string()
    .regex(/^\d*\.?\d*$/, 'Must be a valid number')
    .optional(),
  print_time_hours: z
    .string()
    .regex(/^\d*\.?\d*$/, 'Must be a valid number')
    .optional(),
})

type ProductFormValues = z.infer<typeof productFormSchema>

interface ProductFormProps {
  product?: ProductDetail
  mode: 'create' | 'edit'
}

export function ProductForm({ product, mode }: ProductFormProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Auto-generate SKU for new products
  const { nextSKU, isLoading: isLoadingSKU, refetch: refetchSKU } = useNextSKU('PROD', mode === 'create')

  // Fetch packaging consumables (category = packaging)
  const { data: packagingConsumables } = useQuery({
    queryKey: ['consumables', 'packaging'],
    queryFn: () => consumablesApi.list({ category: 'packaging', is_active: true, page_size: 100 }),
  })

  // Fetch designers for dropdown
  const { data: designersData } = useQuery({
    queryKey: ['designers'],
    queryFn: () => listDesigners({ limit: 100 }),
  })

  const form = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: {
      sku: product?.sku || '',
      name: product?.name || '',
      description: product?.description || '',
      packaging_cost: product?.packaging_cost || '0',
      packaging_consumable_id: product?.packaging_consumable_id || '',
      packaging_quantity: product?.packaging_quantity?.toString() || '1',
      assembly_minutes: product?.assembly_minutes?.toString() || '0',
      units_in_stock: product?.units_in_stock?.toString() || '0',
      is_active: product?.is_active ?? true,
      // Shop fields
      shop_visible: product?.shop_visible ?? false,
      shop_description: product?.shop_description || '',
      is_featured: product?.is_featured ?? false,
      is_dragon: product?.is_dragon ?? false,
      feature_title: product?.feature_title || '',
      backstory: product?.backstory || '',
      print_to_order: product?.print_to_order ?? false,
      // Designer
      designer_id: product?.designer_id || '',
      // Product specifications
      weight_grams: product?.weight_grams?.toString() || '',
      size_cm: product?.size_cm || '',
      print_time_hours: product?.print_time_hours || '',
    },
  })

  // Watch the packaging consumable field to show/hide quantity
  const selectedConsumableId = form.watch('packaging_consumable_id')

  // Auto-fill SKU when it's fetched (only in create mode)
  useEffect(() => {
    if (mode === 'create' && nextSKU && !form.getValues('sku')) {
      form.setValue('sku', nextSKU)
    }
  }, [mode, nextSKU, form])

  const createMutation = useMutation({
    mutationFn: (data: ProductCreateRequest) => createProduct(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      navigate({ to: '/products/$productId', params: { productId: data.id } })
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: ProductUpdateRequest) => updateProduct(product!.id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['product', product!.id] })
      navigate({ to: '/products/$productId', params: { productId: data.id } })
    },
  })

  const onSubmit = (values: ProductFormValues) => {
    const data = {
      sku: values.sku,
      name: values.name,
      description: values.description || undefined,
      packaging_cost: values.packaging_cost || '0',
      // Only include consumable if selected, send null to clear it
      packaging_consumable_id: values.packaging_consumable_id || (mode === 'edit' ? null : undefined),
      packaging_quantity: values.packaging_quantity ? parseInt(values.packaging_quantity) : 1,
      assembly_minutes: values.assembly_minutes ? parseInt(values.assembly_minutes) : 0,
      units_in_stock: values.units_in_stock ? parseInt(values.units_in_stock) : 0,
      is_active: values.is_active,
      // Shop display fields
      shop_visible: values.shop_visible,
      shop_description: values.shop_description || (mode === 'edit' ? null : undefined),
      is_featured: values.is_featured,
      is_dragon: values.is_dragon,
      feature_title: values.feature_title || (mode === 'edit' ? null : undefined),
      backstory: values.backstory || (mode === 'edit' ? null : undefined),
      print_to_order: values.print_to_order,
      // Designer
      designer_id: values.designer_id || (mode === 'edit' ? null : undefined),
      // Product specifications
      weight_grams: values.weight_grams ? parseInt(values.weight_grams) : (mode === 'edit' ? null : undefined),
      size_cm: values.size_cm || (mode === 'edit' ? null : undefined),
      print_time_hours: values.print_time_hours || (mode === 'edit' ? null : undefined),
    }

    if (mode === 'create') {
      createMutation.mutate(data)
    } else {
      updateMutation.mutate(data)
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Product identification and description
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="sku"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>SKU</FormLabel>
                    <FormControl>
                      <div className="flex gap-2">
                        <Input
                          placeholder={isLoadingSKU ? 'Loading...' : 'PROD-001'}
                          {...field}
                          disabled={mode === 'edit' || isLoadingSKU}
                        />
                        {mode === 'create' && (
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={() => refetchSKU()}
                            disabled={isLoadingSKU}
                            title="Generate new SKU"
                          >
                            <RefreshCw className={`h-4 w-4 ${isLoadingSKU ? 'animate-spin' : ''}`} />
                          </Button>
                        )}
                      </div>
                    </FormControl>
                    <FormDescription>
                      {mode === 'create'
                        ? 'Auto-generated, but you can edit it'
                        : 'Unique product identifier'}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Product name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <RichTextEditor
                      value={field.value || ''}
                      onChange={field.onChange}
                      placeholder="Product description..."
                    />
                  </FormControl>
                  <FormDescription>
                    Supports formatting: bold, italic, lists, and links
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        {/* Cost & Inventory */}
        <Card>
          <CardHeader>
            <CardTitle>Cost & Inventory</CardTitle>
            <CardDescription>
              Packaging, assembly time, and stock levels
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Packaging Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Package className="h-4 w-4" />
                Packaging
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <FormField
                  control={form.control}
                  name="packaging_consumable_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Packaging Consumable</FormLabel>
                      <div className="flex gap-2">
                        <Select
                          value={field.value || ''}
                          onValueChange={field.onChange}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select packaging..." />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {packagingConsumables?.consumables.map((consumable) => (
                              <SelectItem key={consumable.id} value={consumable.id}>
                                {consumable.name}
                                {consumable.current_cost_per_unit && (
                                  <span className="ml-2 text-muted-foreground">
                                    (£{consumable.current_cost_per_unit.toFixed(2)}/ea)
                                  </span>
                                )}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {field.value && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => field.onChange('')}
                            title="Clear selection"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                      <FormDescription>
                        Select a packaging consumable (e.g., box)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {selectedConsumableId ? (
                  <FormField
                    control={form.control}
                    name="packaging_quantity"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Quantity per Product</FormLabel>
                        <FormControl>
                          <Input type="number" min="1" placeholder="1" {...field} />
                        </FormControl>
                        <FormDescription>How many of this consumable per product</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                ) : (
                  <FormField
                    control={form.control}
                    name="packaging_cost"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Manual Packaging Cost (£)</FormLabel>
                        <FormControl>
                          <Input type="number" step="0.01" min="0" placeholder="0.00" {...field} />
                        </FormControl>
                        <FormDescription>Enter cost if no consumable selected</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>
            </div>

            {/* Assembly & Inventory */}
            <div className="grid gap-4 md:grid-cols-2">
              <FormField
                control={form.control}
                name="assembly_minutes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Assembly Time (minutes)</FormLabel>
                    <FormControl>
                      <Input type="number" min="0" placeholder="0" {...field} />
                    </FormControl>
                    <FormDescription>Time to assemble/package (@ £10/hr)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="units_in_stock"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Units in Stock</FormLabel>
                    <FormControl>
                      <Input type="number" min="0" placeholder="0" {...field} />
                    </FormControl>
                    <FormDescription>Finished product inventory</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
        </Card>

        {/* Product Specifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Ruler className="h-5 w-5" />
              Product Specifications
            </CardTitle>
            <CardDescription>
              Physical specifications for Etsy listings and product display
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <FormField
                control={form.control}
                name="weight_grams"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="flex items-center gap-2">
                      <Scale className="h-4 w-4" />
                      Weight (grams)
                    </FormLabel>
                    <FormControl>
                      <Input type="number" min="0" placeholder="e.g., 150" {...field} />
                    </FormControl>
                    <FormDescription>
                      Auto-captured from production or manual
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="size_cm"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="flex items-center gap-2">
                      <Ruler className="h-4 w-4" />
                      Size (cm)
                    </FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" min="0" placeholder="e.g., 15.5" {...field} />
                    </FormControl>
                    <FormDescription>
                      Length or primary dimension
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="print_time_hours"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Print Time (hours)
                    </FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" min="0" placeholder="e.g., 12.5" {...field} />
                    </FormControl>
                    <FormDescription>
                      Auto-captured from production or manual
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </CardContent>
        </Card>

        {/* Shop Settings - only show in edit mode */}
        {mode === 'edit' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Store className="h-5 w-5" />
                Shop Display Settings
              </CardTitle>
              <CardDescription>
                Control how this product appears in the Mystmereforge Shop
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Shop Visibility Toggle */}
              <FormField
                control={form.control}
                name="shop_visible"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Show in Shop</FormLabel>
                      <FormDescription>
                        Make this product visible in the online shop
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {/* Designer Selection */}
              <FormField
                control={form.control}
                name="designer_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Designer</FormLabel>
                    <div className="flex gap-2">
                      <Select
                        value={field.value || ''}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select designer..." />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {designersData?.designers.map((designer) => (
                            <SelectItem key={designer.id} value={designer.id}>
                              {designer.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {field.value && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => field.onChange('')}
                          title="Clear selection"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <FormDescription>
                      The designer who created this product's design
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Shop Description */}
              <FormField
                control={form.control}
                name="shop_description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Shop Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Customer-facing description for the shop (optional, falls back to main description)"
                        rows={4}
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Leave empty to use the main description
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Featured Toggle */}
              <FormField
                control={form.control}
                name="is_featured"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base flex items-center gap-2">
                        <Star className="h-4 w-4" />
                        Featured Item
                      </FormLabel>
                      <FormDescription>
                        Display in the featured showcase or gallery section
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {/* Dragon Collection Toggle */}
              <FormField
                control={form.control}
                name="is_dragon"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base flex items-center gap-2">
                        🐉 Dragon Collection
                      </FormLabel>
                      <FormDescription>
                        Include in the Dragons collection page
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {/* Print to Order Toggle */}
              <FormField
                control={form.control}
                name="print_to_order"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base flex items-center gap-2">
                        <Printer className="h-4 w-4" />
                        Print to Order
                      </FormLabel>
                      <FormDescription>
                        Made to order item (not in-stock ready to ship)
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {/* Featured fields - only show when is_featured is true */}
              {form.watch('is_featured') && (
                <div className="space-y-4 pl-4 border-l-2 border-primary/30">
                  <FormField
                    control={form.control}
                    name="feature_title"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Display Title</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="e.g., Ember the Ancient"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Custom title for featured display (dragon name, etc.)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="backstory"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Backstory</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Write the story behind this item... personality, lore, origin story"
                            rows={6}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Rich backstory/lore displayed in the dragon showcase
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Status - only show in edit mode */}
        {mode === 'edit' && (
          <Card>
            <CardContent className="pt-6">
              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Active Status</FormLabel>
                      <FormDescription>
                        Inactive products are hidden from listings but not deleted
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>
        )}

        {/* Help Text */}
        {mode === 'create' && (
          <Card className="bg-muted/50 border-dashed">
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">
                After creating the product, you'll be able to add models (what it's made of),
                bundle other products (to create sets), and set per-channel pricing on the product detail page.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              navigate({ to: product ? `/products/${product.id}` : '/products' })
            }
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === 'create' ? 'Create Product' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </Form>
  )
}
