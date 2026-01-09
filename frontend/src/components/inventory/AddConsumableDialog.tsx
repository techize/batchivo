import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { consumablesApi } from '@/lib/api/consumables'
import type { ConsumableTypeCreate } from '@/types/consumable'
import { CONSUMABLE_CATEGORIES, UNITS_OF_MEASURE } from '@/types/consumable'
import { useNextSKU } from '@/hooks/useSKU'
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
import { Loader2, RefreshCw } from 'lucide-react'

interface AddConsumableDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddConsumableDialog({ open, onOpenChange }: AddConsumableDialogProps) {
  const queryClient = useQueryClient()

  // Auto-generate SKU
  const { nextSKU, isLoading: isLoadingSKU, refetch: refetchSKU } = useNextSKU('COM', open)

  // Form state
  const [formData, setFormData] = useState<Partial<ConsumableTypeCreate>>({
    sku: '',
    name: '',
    description: '',
    category: 'hardware',
    unit_of_measure: 'each',
    current_cost_per_unit: undefined,
    quantity_on_hand: 0,
    reorder_point: undefined,
    reorder_quantity: undefined,
    preferred_supplier: '',
    supplier_sku: '',
    supplier_url: '',
    typical_lead_days: undefined,
    is_active: true,
  })

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
        sku: '',
        name: '',
        description: '',
        category: 'hardware',
        unit_of_measure: 'each',
        current_cost_per_unit: undefined,
        quantity_on_hand: 0,
        reorder_point: undefined,
        reorder_quantity: undefined,
        preferred_supplier: '',
        supplier_sku: '',
        supplier_url: '',
        typical_lead_days: undefined,
        is_active: true,
      })
    }
  }, [open])

  // Auto-fill SKU when nextSKU is fetched
  // formData.sku intentionally excluded to prevent re-run when this effect sets it
  useEffect(() => {
    if (open && nextSKU && !formData.sku) {
      setFormData(prev => ({ ...prev, sku: nextSKU }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, nextSKU])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: ConsumableTypeCreate) => consumablesApi.create(data),
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

    createMutation.mutate(formData as ConsumableTypeCreate)
  }

  const handleInputChange = (field: keyof ConsumableTypeCreate, value: string | number | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Consumable</DialogTitle>
          <DialogDescription>
            Create a new consumable type for tracking inventory (magnets, inserts, hardware, etc.)
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Basic Info */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="sku">
                  SKU <span className="text-destructive">*</span>
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="sku"
                    placeholder={isLoadingSKU ? 'Loading...' : 'COM-001'}
                    value={formData.sku}
                    onChange={(e) => handleInputChange('sku', e.target.value.toUpperCase())}
                    disabled={isLoadingSKU}
                    required
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      refetchSKU().then(result => {
                        if (result.data?.next_sku) {
                          setFormData(prev => ({ ...prev, sku: result.data.next_sku }))
                        }
                      })
                    }}
                    disabled={isLoadingSKU}
                    title="Generate new SKU"
                  >
                    <RefreshCw className={`h-4 w-4 ${isLoadingSKU ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">Auto-generated, but you can edit it</p>
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
                value={formData.name}
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
                onChange={(e) => handleInputChange('description', e.target.value)}
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
                <Label htmlFor="quantity_on_hand">Initial Quantity</Label>
                <Input
                  id="quantity_on_hand"
                  type="number"
                  min="0"
                  value={formData.quantity_on_hand || 0}
                  onChange={(e) => handleInputChange('quantity_on_hand', parseInt(e.target.value) || 0)}
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
                  value={formData.current_cost_per_unit || ''}
                  onChange={(e) =>
                    handleInputChange('current_cost_per_unit', e.target.value ? parseFloat(e.target.value) : undefined)
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
                  value={formData.reorder_point || ''}
                  onChange={(e) =>
                    handleInputChange('reorder_point', e.target.value ? parseInt(e.target.value) : undefined)
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
                  value={formData.reorder_quantity || ''}
                  onChange={(e) =>
                    handleInputChange('reorder_quantity', e.target.value ? parseInt(e.target.value) : undefined)
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
                  onChange={(e) => handleInputChange('preferred_supplier', e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="supplier_sku">Supplier SKU</Label>
                <Input
                  id="supplier_sku"
                  placeholder="Supplier's product code"
                  value={formData.supplier_sku || ''}
                  onChange={(e) => handleInputChange('supplier_sku', e.target.value)}
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
                onChange={(e) => handleInputChange('supplier_url', e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="typical_lead_days">Typical Lead Days</Label>
              <Input
                id="typical_lead_days"
                type="number"
                min="0"
                placeholder="Typical delivery time in days"
                value={formData.typical_lead_days || ''}
                onChange={(e) =>
                  handleInputChange('typical_lead_days', e.target.value ? parseInt(e.target.value) : undefined)
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
          {createMutation.isError && (
            <div className="bg-destructive/10 border border-destructive rounded-md p-3">
              <p className="text-sm text-destructive">
                Failed to create consumable:{' '}
                {createMutation.error instanceof Error ? createMutation.error.message : 'Unknown error'}
              </p>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Consumable
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
