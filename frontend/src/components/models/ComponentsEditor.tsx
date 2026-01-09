/**
 * ComponentsEditor Component
 *
 * Editor for managing model components (magnets, inserts, screws, etc.).
 * Supports both selecting from consumables inventory and manual entry.
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { Loader2, Plus, Trash2 } from 'lucide-react'

import { addModelComponent, removeModelComponent, type ModelComponent } from '@/lib/api/models'
import { consumablesApi } from '@/lib/api/consumables'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const componentFormSchema = z.object({
  component_name: z.string().min(1, 'Component name is required').max(200),
  quantity: z.coerce.number().int().positive('Quantity must be positive'),
  unit_cost: z.string().regex(/^\d+(\.\d{1,4})?$/, 'Must be a valid number'),
  supplier: z.string().max(200).optional(),
  notes: z.string().optional(),
})

const consumableFormSchema = z.object({
  consumable_id: z.string().uuid('Must select a consumable'),
  quantity: z.coerce.number().int().positive('Quantity must be positive'),
})

type ComponentFormValues = z.infer<typeof componentFormSchema>
type ConsumableFormValues = z.infer<typeof consumableFormSchema>

interface ComponentsEditorProps {
  modelId: string
  components: ModelComponent[]
}

export function ComponentsEditor({ modelId, components }: ComponentsEditorProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'inventory' | 'manual'>('inventory')
  const queryClient = useQueryClient()

  // Fetch consumables for selection
  const { data: consumablesData } = useQuery({
    queryKey: ['consumables', { page: 1, page_size: 100 }],
    queryFn: () => consumablesApi.list({ page: 1, page_size: 100 }),
  })

  const form = useForm<ComponentFormValues>({
    resolver: zodResolver(componentFormSchema),
    defaultValues: {
      component_name: '',
      quantity: 1,
      unit_cost: '',
      supplier: '',
      notes: '',
    },
  })

  const consumableForm = useForm<ConsumableFormValues>({
    resolver: zodResolver(consumableFormSchema),
    defaultValues: {
      consumable_id: '',
      quantity: 1,
    },
  })

  const addMutation = useMutation({
    mutationFn: (data: ComponentFormValues) =>
      addModelComponent(modelId, {
        component_name: data.component_name,
        quantity: data.quantity,
        unit_cost: data.unit_cost,
        supplier: data.supplier || undefined,
        notes: data.notes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model', modelId] })
      form.reset()
      setDialogOpen(false)
    },
  })

  const removeMutation = useMutation({
    mutationFn: (componentId: string) => removeModelComponent(modelId, componentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model', modelId] })
    },
  })

  const onSubmit = (values: ComponentFormValues) => {
    addMutation.mutate(values)
  }

  const onConsumableSubmit = (values: ConsumableFormValues) => {
    const consumable = consumablesData?.consumables.find((c) => c.id === values.consumable_id)
    if (!consumable) return

    // Convert consumable to component format
    addMutation.mutate({
      component_name: consumable.name,
      quantity: values.quantity,
      unit_cost: (consumable.current_cost_per_unit || 0).toFixed(4),
      supplier: consumable.preferred_supplier || undefined,
      notes: `From inventory: ${consumable.sku}`,
    })
    consumableForm.reset()
  }

  const formatCurrency = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    return `£${numValue.toFixed(4)}`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Components</h3>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Component
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add Component</DialogTitle>
              <DialogDescription>Add a component from inventory or enter manually</DialogDescription>
            </DialogHeader>

            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'inventory' | 'manual')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="inventory">From Inventory</TabsTrigger>
                <TabsTrigger value="manual">Manual Entry</TabsTrigger>
              </TabsList>

              <TabsContent value="inventory" className="space-y-4 mt-4">
                <Form {...consumableForm}>
                  <form onSubmit={consumableForm.handleSubmit(onConsumableSubmit)} className="space-y-4">
                    <FormField
                      control={consumableForm.control}
                      name="consumable_id"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Select Consumable</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Choose from inventory..." />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {consumablesData?.consumables.map((c) => (
                                <SelectItem key={c.id} value={c.id}>
                                  {c.sku} - {c.name} ({formatCurrency(c.current_cost_per_unit || 0)}/ea)
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormDescription>Cost will be auto-filled from inventory</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={consumableForm.control}
                      name="quantity"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Quantity per Model</FormLabel>
                          <FormControl>
                            <Input type="number" min="1" placeholder="1" {...field} />
                          </FormControl>
                          <FormDescription>How many used per model</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <DialogFooter>
                      <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} disabled={addMutation.isPending}>
                        Cancel
                      </Button>
                      <Button type="submit" disabled={addMutation.isPending}>
                        {addMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Add from Inventory
                      </Button>
                    </DialogFooter>
                  </form>
                </Form>
              </TabsContent>

              <TabsContent value="manual" className="space-y-4 mt-4">
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                      control={form.control}
                      name="component_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Component Name</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g., Neodymium Magnet 6x3mm" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <div className="grid gap-4 grid-cols-2">
                      <FormField
                        control={form.control}
                        name="quantity"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Quantity</FormLabel>
                            <FormControl>
                              <Input type="number" min="1" placeholder="1" {...field} />
                            </FormControl>
                            <FormDescription>Per model</FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="unit_cost"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Unit Cost (£)</FormLabel>
                            <FormControl>
                              <Input type="number" step="0.0001" placeholder="0.00" {...field} />
                            </FormControl>
                            <FormDescription>Cost per unit</FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>

                    <FormField
                      control={form.control}
                      name="supplier"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Supplier (Optional)</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g., Amazon, AliExpress" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="notes"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Notes (Optional)</FormLabel>
                          <FormControl>
                            <Textarea placeholder="Additional notes..." rows={2} {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <DialogFooter>
                      <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} disabled={addMutation.isPending}>
                        Cancel
                      </Button>
                      <Button type="submit" disabled={addMutation.isPending}>
                        {addMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Add Component
                      </Button>
                    </DialogFooter>
                  </form>
                </Form>
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      </div>

      {!components || components.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          No components added yet. Click "Add Component" to get started.
        </div>
      ) : (
        <div className="space-y-2">
          {components?.map((component) => (
            <div key={component.id} className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-1 flex-1">
                <div className="font-medium">{component.component_name}</div>
                <div className="text-sm text-muted-foreground">
                  Qty: {component.quantity} × {formatCurrency(component.unit_cost)}
                  {component.supplier && ` • Supplier: ${component.supplier}`}
                </div>
                {component.notes && <div className="text-xs text-muted-foreground">{component.notes}</div>}
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="font-semibold">
                    {formatCurrency((component.quantity * parseFloat(component.unit_cost)).toFixed(3))}
                  </div>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="ghost" size="sm" disabled={removeMutation.isPending}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Remove Component</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to remove this component from the model?
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => removeMutation.mutate(component.id)}>Remove</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
