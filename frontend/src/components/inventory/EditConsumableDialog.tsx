import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { consumablesApi } from '@/lib/api/consumables'
import type { ConsumableTypeUpdate } from '@/types/consumable'
import { CONSUMABLE_CATEGORIES, UNITS_OF_MEASURE } from '@/types/consumable'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Loader2 } from 'lucide-react'

interface EditConsumableDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  consumableId: string | null
}

export function EditConsumableDialog({ open, onOpenChange, consumableId }: EditConsumableDialogProps) {
  const queryClient = useQueryClient()

  // Fetch consumable details
  const { data: consumable, isLoading } = useQuery({
    queryKey: ['consumables', consumableId],
    queryFn: () => (consumableId ? consumablesApi.get(consumableId) : null),
    enabled: !!consumableId && open,
  })

  // Form state
  const [formData, setFormData] = useState<ConsumableTypeUpdate>({})

  // Populate form when consumable is loaded
  useEffect(() => {
    if (consumable) {
      setFormData({
        sku: consumable.sku,
        name: consumable.name,
        description: consumable.description,
        category: consumable.category,
        unit_of_measure: consumable.unit_of_measure,
        current_cost_per_unit: consumable.current_cost_per_unit,
        quantity_on_hand: consumable.quantity_on_hand,
        reorder_point: consumable.reorder_point,
        reorder_quantity: consumable.reorder_quantity,
        preferred_supplier: consumable.preferred_supplier,
        supplier_sku: consumable.supplier_sku,
        supplier_url: consumable.supplier_url,
        typical_lead_days: consumable.typical_lead_days,
        is_active: consumable.is_active,
      })
    }
  }, [consumable])

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: ConsumableTypeUpdate) =>
      consumableId ? consumablesApi.update(consumableId, data) : Promise.reject('No ID'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consumables'] })
      onOpenChange(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.sku || !formData.name) {
      alert('Please fill in all required fields')
      return
    }

    updateMutation.mutate(formData)
  }

  const handleInputChange = (field: keyof ConsumableTypeUpdate, value: string | number | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Consumable</DialogTitle>
          <DialogDescription>Update consumable details and stock settings.</DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-2">Loading...</span>
          </div>
        )}

        {consumable && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Basic Info */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="sku">
                    SKU <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="sku"
                    placeholder="MAG-3X1, INS-M3, etc."
                    value={formData.sku || ''}
                    onChange={(e) => handleInputChange('sku', e.target.value.toUpperCase())}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Select
                    value={formData.category || 'hardware'}
                    onValueChange={(value) => handleInputChange('category', value)}
                  >
                    <SelectTrigger id="category">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONSUMABLE_CATEGORIES.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat.charAt(0).toUpperCase() + cat.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">
                  Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  placeholder="Magnet 3mm x 1mm, M3 Heat Insert, etc."
                  value={formData.name || ''}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <textarea
                  id="description"
                  className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="Additional details about this consumable..."
                  value={formData.description || ''}
                  onChange={(e) => handleInputChange('description', e.target.value || null)}
                />
              </div>
            </div>

            {/* Stock & Pricing */}
            <div className="border-t pt-4 space-y-4">
              <h4 className="text-sm font-medium">Stock & Pricing</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="unit_of_measure">Unit</Label>
                  <Select
                    value={formData.unit_of_measure || 'each'}
                    onValueChange={(value) => handleInputChange('unit_of_measure', value)}
                  >
                    <SelectTrigger id="unit_of_measure">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {UNITS_OF_MEASURE.map((unit) => (
                        <SelectItem key={unit} value={unit}>
                          {unit}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="quantity_on_hand">Quantity on Hand</Label>
                  <Input
                    id="quantity_on_hand"
                    type="number"
                    min="0"
                    value={formData.quantity_on_hand ?? 0}
                    onChange={(e) =>
                      handleInputChange('quantity_on_hand', parseInt(e.target.value) || 0)
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="current_cost_per_unit">Cost per Unit</Label>
                  <Input
                    id="current_cost_per_unit"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="0.00"
                    value={formData.current_cost_per_unit ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'current_cost_per_unit',
                        e.target.value ? parseFloat(e.target.value) : null
                      )
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="reorder_point">Reorder Point</Label>
                  <Input
                    id="reorder_point"
                    type="number"
                    min="0"
                    placeholder="Alert when stock falls below..."
                    value={formData.reorder_point ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'reorder_point',
                        e.target.value ? parseInt(e.target.value) : null
                      )
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="reorder_quantity">Reorder Quantity</Label>
                  <Input
                    id="reorder_quantity"
                    type="number"
                    min="1"
                    placeholder="Suggested order quantity..."
                    value={formData.reorder_quantity ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'reorder_quantity',
                        e.target.value ? parseInt(e.target.value) : null
                      )
                    }
                  />
                </div>
              </div>
            </div>

            {/* Supplier Info */}
            <div className="border-t pt-4 space-y-4">
              <h4 className="text-sm font-medium">Supplier Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="preferred_supplier">Preferred Supplier</Label>
                  <Input
                    id="preferred_supplier"
                    placeholder="Amazon, AliExpress, etc."
                    value={formData.preferred_supplier || ''}
                    onChange={(e) => handleInputChange('preferred_supplier', e.target.value || null)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="supplier_sku">Supplier SKU</Label>
                  <Input
                    id="supplier_sku"
                    placeholder="Supplier's product code"
                    value={formData.supplier_sku || ''}
                    onChange={(e) => handleInputChange('supplier_sku', e.target.value || null)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="supplier_url">Supplier URL</Label>
                <Input
                  id="supplier_url"
                  type="url"
                  placeholder="https://amazon.co.uk/dp/..."
                  value={formData.supplier_url || ''}
                  onChange={(e) => handleInputChange('supplier_url', e.target.value || null)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="typical_lead_days">Typical Lead Days</Label>
                <Input
                  id="typical_lead_days"
                  type="number"
                  min="0"
                  placeholder="Typical delivery time in days"
                  value={formData.typical_lead_days ?? ''}
                  onChange={(e) =>
                    handleInputChange(
                      'typical_lead_days',
                      e.target.value ? parseInt(e.target.value) : null
                    )
                  }
                />
              </div>
            </div>

            {/* Status */}
            <div className="border-t pt-4">
              <div className="flex items-center gap-2">
                <Switch
                  id="is_active"
                  checked={formData.is_active ?? true}
                  onCheckedChange={(checked) => handleInputChange('is_active', checked)}
                />
                <Label htmlFor="is_active" className="cursor-pointer">
                  Active (include in low stock alerts)
                </Label>
              </div>
            </div>

            {/* Error Display */}
            {updateMutation.isError && (
              <div className="bg-destructive/10 border border-destructive rounded-md p-3">
                <p className="text-sm text-destructive">
                  Failed to update consumable:{' '}
                  {updateMutation.error instanceof Error
                    ? updateMutation.error.message
                    : 'Unknown error'}
                </p>
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
