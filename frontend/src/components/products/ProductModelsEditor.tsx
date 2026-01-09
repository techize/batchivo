/**
 * ProductModelsEditor Component
 *
 * Editor for managing product model composition.
 * Allows adding/removing models and adjusting quantities.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Loader2, Plus, Trash2, ExternalLink } from 'lucide-react'

import {
  addProductModel,
  removeProductModel,
  updateProductModel,
  formatCurrency,
  type ProductModel,
} from '@/lib/api/products'
import { listModels } from '@/lib/api/models'
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

const modelFormSchema = z.object({
  model_id: z.string().uuid('Must select a model'),
  quantity: z.coerce.number().int().positive('Quantity must be positive'),
})

type ModelFormValues = z.infer<typeof modelFormSchema>

interface ProductModelsEditorProps {
  productId: string
  models: ProductModel[]
}

export function ProductModelsEditor({ productId, models }: ProductModelsEditorProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [, setEditingModel] = useState<ProductModel | null>(null)
  const queryClient = useQueryClient()

  // Fetch available models for selection
  const { data: availableModels } = useQuery({
    queryKey: ['models', { limit: 100 }],
    queryFn: () => listModels({ limit: 100 }),
  })

  const form = useForm<ModelFormValues>({
    resolver: zodResolver(modelFormSchema),
    defaultValues: {
      model_id: '',
      quantity: 1,
    },
  })

  const addMutation = useMutation({
    mutationFn: (data: ModelFormValues) =>
      addProductModel(productId, {
        model_id: data.model_id,
        quantity: data.quantity,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      form.reset()
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ productModelId, data }: { productModelId: string; data: ModelFormValues }) =>
      updateProductModel(productId, productModelId, {
        model_id: data.model_id,
        quantity: data.quantity,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      setEditingModel(null)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (productModelId: string) => removeProductModel(productId, productModelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  const onSubmit = (values: ModelFormValues) => {
    addMutation.mutate(values)
  }

  const handleQuantityUpdate = (productModel: ProductModel, newQuantity: number) => {
    if (newQuantity < 1) return
    updateMutation.mutate({
      productModelId: productModel.id,
      data: {
        model_id: productModel.model_id,
        quantity: newQuantity,
      },
    })
  }

  // Filter out models that are already in the product
  const existingModelIds = models.map((m) => m.model_id)
  const selectableModels =
    availableModels?.models?.filter((m) => !existingModelIds.includes(m.id)) || []

  // Calculate total cost
  const totalModelsCost = models.reduce((total, pm) => {
    const modelCost = parseFloat(pm.model_cost || '0')
    return total + modelCost * pm.quantity
  }, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Total models cost: <span className="font-semibold">{formatCurrency(totalModelsCost)}</span>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Model
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add Model to Product</DialogTitle>
              <DialogDescription>
                Select a model and specify how many are needed per product unit
              </DialogDescription>
            </DialogHeader>

            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="model_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Select Model</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Choose a model..." />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {selectableModels.length === 0 ? (
                            <SelectItem value="none" disabled>
                              No models available
                            </SelectItem>
                          ) : (
                            selectableModels.map((model) => (
                              <SelectItem key={model.id} value={model.id}>
                                {model.sku} - {model.name} ({formatCurrency(model.total_cost || '0')})
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        Models already in this product are hidden
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
                      <FormLabel>Quantity per Product</FormLabel>
                      <FormControl>
                        <Input type="number" min="1" placeholder="1" {...field} />
                      </FormControl>
                      <FormDescription>
                        How many of this model are needed per product unit
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
                  <Button type="submit" disabled={addMutation.isPending || selectableModels.length === 0}>
                    {addMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Add Model
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {!models || models.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          No models added yet. Click "Add Model" to compose this product.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Model</TableHead>
              <TableHead className="w-[100px] text-right">Unit Cost</TableHead>
              <TableHead className="w-[100px] text-center">Quantity</TableHead>
              <TableHead className="w-[100px] text-right">Total</TableHead>
              <TableHead className="w-[80px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {models.map((productModel) => {
              const unitCost = parseFloat(productModel.model_cost || '0')
              const totalCost = unitCost * productModel.quantity

              return (
                <TableRow key={productModel.id}>
                  <TableCell>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <Link
                          to="/models/$modelId"
                          params={{ modelId: productModel.model_id }}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {productModel.model_name || 'Unknown Model'}
                        </Link>
                        <Link
                          to="/models/$modelId"
                          params={{ modelId: productModel.model_id }}
                          className="text-muted-foreground hover:text-primary"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                      {productModel.model_sku && (
                        <div className="text-xs font-mono text-muted-foreground">
                          {productModel.model_sku}
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
                        onClick={() => handleQuantityUpdate(productModel, productModel.quantity - 1)}
                        disabled={productModel.quantity <= 1 || updateMutation.isPending}
                      >
                        -
                      </Button>
                      <span className="w-8 text-center tabular-nums font-medium">
                        {productModel.quantity}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleQuantityUpdate(productModel, productModel.quantity + 1)}
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
                          <AlertDialogTitle>Remove Model</AlertDialogTitle>
                          <AlertDialogDescription>
                            Are you sure you want to remove "{productModel.model_name}" from this product?
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => removeMutation.mutate(productModel.id)}>
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
                Total Models Cost
              </TableCell>
              <TableCell className="text-right tabular-nums font-bold">
                {formatCurrency(totalModelsCost)}
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )}
    </div>
  )
}
