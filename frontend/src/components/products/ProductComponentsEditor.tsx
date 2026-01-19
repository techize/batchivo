/**
 * ProductComponentsEditor Component
 *
 * Editor for managing product components (child products in bundles).
 * Allows adding/removing child products and adjusting quantities.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Loader2, Plus, Trash2, ExternalLink, Package } from 'lucide-react'

import {
  addProductComponent,
  removeProductComponent,
  updateProductComponent,
  listProducts,
  type ProductComponent,
} from '@/lib/api/products'
import { useCurrency } from '@/hooks/useCurrency'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const componentFormSchema = z.object({
  child_product_id: z.string().uuid('Must select a product'),
  quantity: z.coerce.number().int().positive('Quantity must be positive'),
})

type ComponentFormValues = z.infer<typeof componentFormSchema>

interface ProductComponentsEditorProps {
  productId: string
  components: ProductComponent[]
}

export function ProductComponentsEditor({ productId, components }: ProductComponentsEditorProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const queryClient = useQueryClient()
  const { formatCurrency } = useCurrency()

  // Fetch available products for selection (excluding current product)
  const { data: availableProducts } = useQuery({
    queryKey: ['products', { limit: 100 }],
    queryFn: () => listProducts({ limit: 100, is_active: true }),
  })

  const form = useForm<ComponentFormValues>({
    resolver: zodResolver(componentFormSchema),
    defaultValues: {
      child_product_id: '',
      quantity: 1,
    },
  })

  const addMutation = useMutation({
    mutationFn: (data: ComponentFormValues) =>
      addProductComponent(productId, {
        child_product_id: data.child_product_id,
        quantity: data.quantity,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      form.reset()
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ componentId, data }: { componentId: string; data: { quantity: number } }) =>
      updateProductComponent(productId, componentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (componentId: string) => removeProductComponent(productId, componentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  const onSubmit = (values: ComponentFormValues) => {
    addMutation.mutate(values)
  }

  const handleQuantityUpdate = (component: ProductComponent, newQuantity: number) => {
    if (newQuantity < 1) return
    updateMutation.mutate({
      componentId: component.id,
      data: { quantity: newQuantity },
    })
  }

  // Filter out products that are already in the bundle and the current product itself
  const existingProductIds = components.map((c) => c.child_product_id)
  const selectableProducts =
    availableProducts?.products?.filter(
      (p) => !existingProductIds.includes(p.id) && p.id !== productId
    ) || []

  // Calculate total cost of all child products
  const totalComponentsCost = components.reduce((total, pc) => {
    const productCost = parseFloat(pc.child_product_cost || '0')
    return total + productCost * pc.quantity
  }, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Total child products cost: <span className="font-semibold">{formatCurrency(totalComponentsCost)}</span>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Product
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add Child Product to Bundle</DialogTitle>
              <DialogDescription>
                Select a product to include in this bundle and specify the quantity
              </DialogDescription>
            </DialogHeader>

            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="child_product_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Select Product</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Choose a product..." />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {selectableProducts.length === 0 ? (
                            <SelectItem value="none" disabled>
                              No products available
                            </SelectItem>
                          ) : (
                            selectableProducts.map((product) => (
                              <SelectItem key={product.id} value={product.id}>
                                {product.sku} - {product.name}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        Products already in this bundle are hidden
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="quantity"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Quantity</FormLabel>
                      <FormControl>
                        <Input type="number" min="1" placeholder="1" {...field} />
                      </FormControl>
                      <FormDescription>
                        How many of this product are included in the bundle
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setDialogOpen(false)}
                    disabled={addMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={addMutation.isPending || selectableProducts.length === 0}>
                    {addMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Add Product
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {!components || components.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No child products added yet.</p>
          <p className="text-sm">Click "Add Product" to create a bundle.</p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Product</TableHead>
              <TableHead className="w-[100px] text-right">Unit Cost</TableHead>
              <TableHead className="w-[100px] text-center">Quantity</TableHead>
              <TableHead className="w-[100px] text-right">Total</TableHead>
              <TableHead className="w-[80px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {components.map((component) => {
              const unitCost = parseFloat(component.child_product_cost || '0')
              const totalCost = unitCost * component.quantity

              return (
                <TableRow key={component.id}>
                  <TableCell>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Link
                          to="/products/$productId"
                          params={{ productId: component.child_product_id }}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {component.child_product_name || 'Unknown Product'}
                        </Link>
                        <Link
                          to="/products/$productId"
                          params={{ productId: component.child_product_id }}
                          className="text-muted-foreground hover:text-primary"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                      {component.child_product_sku && (
                        <div className="text-xs font-mono text-muted-foreground">
                          {component.child_product_sku}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(unitCost)}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleQuantityUpdate(component, component.quantity - 1)}
                        disabled={component.quantity <= 1 || updateMutation.isPending}
                      >
                        -
                      </Button>
                      <span className="w-8 text-center tabular-nums font-medium">
                        {component.quantity}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleQuantityUpdate(component, component.quantity + 1)}
                        disabled={updateMutation.isPending}
                      >
                        +
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-semibold">
                    {formatCurrency(totalCost)}
                  </TableCell>
                  <TableCell className="text-right">
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="sm" disabled={removeMutation.isPending}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Remove Child Product</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to remove "{component.child_product_name}" from this bundle?
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => removeMutation.mutate(component.id)}>
                            Remove
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </TableCell>
                </TableRow>
              )
            })}
            {/* Total Row */}
            <TableRow className="bg-muted/50">
              <TableCell colSpan={3} className="text-right font-medium">
                Total Child Products Cost
              </TableCell>
              <TableCell className="text-right tabular-nums font-bold">
                {formatCurrency(totalComponentsCost)}
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )}
    </div>
  )
}
