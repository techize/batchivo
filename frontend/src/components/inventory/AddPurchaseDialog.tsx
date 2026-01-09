import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { consumablesApi } from '@/lib/api/consumables'
import type { ConsumablePurchaseCreate } from '@/types/consumable'
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
import { Loader2 } from 'lucide-react'

interface AddPurchaseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  consumableId: string | null
}

export function AddPurchaseDialog({ open, onOpenChange, consumableId }: AddPurchaseDialogProps) {
  const queryClient = useQueryClient()

  // Fetch consumable details if ID provided
  const { data: consumable } = useQuery({
    queryKey: ['consumables', consumableId],
    queryFn: () => (consumableId ? consumablesApi.get(consumableId) : null),
    enabled: !!consumableId && open,
  })

  // Fetch all consumables for dropdown (when no ID provided)
  const { data: consumableList } = useQuery({
    queryKey: ['consumables', { page: 1, page_size: 100 }],
    queryFn: () => consumablesApi.list({ page: 1, page_size: 100 }),
    enabled: !consumableId && open,
  })

  // Form state
  const [formData, setFormData] = useState<Partial<ConsumablePurchaseCreate>>({
    consumable_type_id: '',
    quantity_purchased: 1,
    total_cost: 0,
    supplier: '',
    order_reference: '',
    purchase_url: '',
    purchase_date: new Date().toISOString().split('T')[0],
    notes: '',
  })

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setFormData({
        consumable_type_id: consumableId || '',
        quantity_purchased: 1,
        total_cost: 0,
        supplier: consumable?.preferred_supplier || '',
        order_reference: '',
        purchase_url: consumable?.supplier_url || '',
        purchase_date: new Date().toISOString().split('T')[0],
        notes: '',
      })
    }
  }, [open, consumableId, consumable])

  // Calculate cost per unit
  const costPerUnit =
    formData.total_cost && formData.quantity_purchased && formData.quantity_purchased > 0
      ? (formData.total_cost / formData.quantity_purchased).toFixed(4)
      : '0.0000'

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: ConsumablePurchaseCreate) => consumablesApi.createPurchase(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consumables'] })
      onOpenChange(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.consumable_type_id || !formData.quantity_purchased || !formData.total_cost) {
      alert('Please fill in all required fields')
      return
    }

    createMutation.mutate(formData as ConsumablePurchaseCreate)
  }

  const handleInputChange = (field: keyof ConsumablePurchaseCreate, value: string | number | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Purchase</DialogTitle>
          <DialogDescription>
            {consumable
              ? `Record a purchase of ${consumable.name}`
              : 'Record a new consumable purchase'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Consumable Selection (if not pre-selected) */}
          {!consumableId && (
            <div className="space-y-2">
              <Label htmlFor="consumable_type_id">
                Consumable <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.consumable_type_id}
                onValueChange={(value) => handleInputChange('consumable_type_id', value)}
              >
                <SelectTrigger id="consumable_type_id">
                  <SelectValue placeholder="Select consumable..." />
                </SelectTrigger>
                <SelectContent>
                  {consumableList?.consumables.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.sku} - {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Display selected consumable info */}
          {consumable && (
            <div className="bg-muted/50 rounded-md p-3">
              <p className="font-medium">{consumable.name}</p>
              <p className="text-sm text-muted-foreground">SKU: {consumable.sku}</p>
              <p className="text-sm text-muted-foreground">
                Current stock: {consumable.quantity_on_hand} {consumable.unit_of_measure}
              </p>
            </div>
          )}

          {/* Purchase Details */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="quantity_purchased">
                Quantity <span className="text-destructive">*</span>
              </Label>
              <Input
                id="quantity_purchased"
                type="number"
                min="1"
                value={formData.quantity_purchased || ''}
                onChange={(e) =>
                  handleInputChange('quantity_purchased', parseInt(e.target.value) || 0)
                }
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="total_cost">
                Total Cost (£) <span className="text-destructive">*</span>
              </Label>
              <Input
                id="total_cost"
                type="number"
                step="0.01"
                min="0"
                value={formData.total_cost || ''}
                onChange={(e) =>
                  handleInputChange('total_cost', parseFloat(e.target.value) || 0)
                }
                required
              />
            </div>
          </div>

          <div className="text-sm text-muted-foreground">
            Cost per unit: <span className="font-mono">£{costPerUnit}</span>
          </div>

          <div className="space-y-2">
            <Label htmlFor="purchase_date">Purchase Date</Label>
            <Input
              id="purchase_date"
              type="date"
              value={formData.purchase_date || ''}
              onChange={(e) => handleInputChange('purchase_date', e.target.value || undefined)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="supplier">Supplier</Label>
              <Input
                id="supplier"
                placeholder="Amazon, AliExpress, etc."
                value={formData.supplier || ''}
                onChange={(e) => handleInputChange('supplier', e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="order_reference">Order Reference</Label>
              <Input
                id="order_reference"
                placeholder="Order #, invoice, etc."
                value={formData.order_reference || ''}
                onChange={(e) => handleInputChange('order_reference', e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="purchase_url">Purchase URL</Label>
            <Input
              id="purchase_url"
              type="url"
              placeholder="https://amazon.co.uk/dp/..."
              value={formData.purchase_url || ''}
              onChange={(e) => handleInputChange('purchase_url', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <textarea
              id="notes"
              className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              placeholder="Additional notes about this purchase..."
              value={formData.notes || ''}
              onChange={(e) => handleInputChange('notes', e.target.value)}
            />
          </div>

          {/* Error Display */}
          {createMutation.isError && (
            <div className="bg-destructive/10 border border-destructive rounded-md p-3">
              <p className="text-sm text-destructive">
                Failed to record purchase:{' '}
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
              Add Purchase
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
