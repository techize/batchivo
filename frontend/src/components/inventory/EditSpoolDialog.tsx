import { useState, useEffect, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { spoolsApi, materialTypesApi } from '@/lib/api/spools'
import type { SpoolUpdate } from '@/types/spool'

// Normalize brand/supplier names to prevent duplicates
const normalizeName = (name: string): string => {
  return name
    .toLowerCase()
    .replace(/\s+/g, '') // Remove all spaces
    .trim()
}

// Get display name (capitalize first letter of each word)
const getDisplayName = (name: string): string => {
  return name
    .split(/\s+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
    .trim()
}

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

interface EditSpoolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  spoolId: string | null
}

export function EditSpoolDialog({ open, onOpenChange, spoolId }: EditSpoolDialogProps) {
  const queryClient = useQueryClient()

  // Fetch the specific spool to edit
  const { data: spool, isLoading: loadingSpool } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => spoolsApi.get(spoolId!),
    enabled: !!spoolId && open,
  })

  // Fetch material types for dropdown
  const { data: materialTypes, isLoading: loadingMaterials } = useQuery({
    queryKey: ['material-types'],
    queryFn: () => materialTypesApi.list(),
  })

  // Fetch existing spools for brand/supplier autocomplete
  const { data: spoolData } = useQuery({
    queryKey: ['spools', { page: 1, page_size: 100 }],
    queryFn: () => spoolsApi.list({ page: 1, page_size: 100 }),
  })

  // Form state
  const [formData, setFormData] = useState<Partial<SpoolUpdate>>({})

  // UI state for purchase info
  const [currency, setCurrency] = useState('GBP')

  // Weight input mode - when true, user enters gross weight (what they read from scales)
  const [useGrossWeight, setUseGrossWeight] = useState(false)
  // Store the displayed weight value (could be gross or net depending on mode)
  const [displayedWeight, setDisplayedWeight] = useState<string>('')

  // Populate form when spool data loads
  useEffect(() => {
    if (spool && open) {
      setFormData({
        spool_id: spool.spool_id,
        material_type_id: spool.material_type_id,
        brand: spool.brand,
        color: spool.color,
        finish: spool.finish || '',
        initial_weight: spool.initial_weight,
        current_weight: spool.current_weight,
        empty_spool_weight: spool.empty_spool_weight || undefined,
        purchase_date: spool.purchase_date ? spool.purchase_date.split('T')[0] : undefined,
        purchase_price: spool.purchase_price || undefined,
        supplier: spool.supplier || '',
        purchased_quantity: spool.purchased_quantity,
        spools_remaining: spool.spools_remaining,
        storage_location: spool.storage_location || '',
        notes: spool.notes || '',
        is_active: spool.is_active,
      })
      // Set currency based on context if available (default GBP)
      setCurrency('GBP')
      // Reset weight input mode and display value
      setUseGrossWeight(false)
      setDisplayedWeight(spool.current_weight.toString())
    }
  }, [spool, open])

  // Sort materials to show PLA, PETG, TPU first
  const sortedMaterials = (materialTypes && Array.isArray(materialTypes)) ? [...materialTypes].sort((a, b) => {
    const priority = { 'PLA': 1, 'PETG': 2, 'TPU': 3 }
    const aPriority = priority[a.code as keyof typeof priority] || 999
    const bPriority = priority[b.code as keyof typeof priority] || 999

    if (aPriority !== bPriority) {
      return aPriority - bPriority
    }
    return a.code.localeCompare(b.code)
  }) : []

  // Extract unique brands and suppliers from existing spools
  const uniqueBrands = useMemo(() => {
    if (!spoolData) return []

    const brandMap = new Map<string, string>()
    spoolData.spools.forEach(spool => {
      const normalized = normalizeName(spool.brand)
      if (!brandMap.has(normalized)) {
        brandMap.set(normalized, getDisplayName(spool.brand))
      }
    })

    return Array.from(brandMap.values()).sort()
  }, [spoolData])

  const uniqueSuppliers = useMemo(() => {
    if (!spoolData) return []

    const supplierMap = new Map<string, string>()
    spoolData.spools.forEach(spool => {
      if (spool.supplier) {
        const normalized = normalizeName(spool.supplier)
        if (!supplierMap.has(normalized)) {
          supplierMap.set(normalized, getDisplayName(spool.supplier))
        }
      }
    })

    return Array.from(supplierMap.values()).sort()
  }, [spoolData])

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: SpoolUpdate) => spoolsApi.update(spoolId!, data),
    onSuccess: () => {
      // Invalidate and refetch spools list
      queryClient.invalidateQueries({ queryKey: ['spools'] })
      queryClient.invalidateQueries({ queryKey: ['spool', spoolId] })
      // Close dialog
      onOpenChange(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (
      !formData.spool_id ||
      !formData.material_type_id ||
      !formData.brand ||
      !formData.color ||
      !formData.initial_weight ||
      formData.current_weight === undefined
    ) {
      alert('Please fill in all required fields')
      return
    }

    updateMutation.mutate(formData as SpoolUpdate)
  }

  const handleInputChange = (field: keyof SpoolUpdate, value: string | number | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  // Calculate net weight from displayed weight (subtracts spool weight if in gross mode)
  const getNetWeight = (): number => {
    const enteredWeight = parseFloat(displayedWeight) || 0
    if (useGrossWeight && formData.empty_spool_weight) {
      return Math.max(0, enteredWeight - formData.empty_spool_weight)
    }
    return enteredWeight
  }

  // Handle weight input changes - updates both display and form data
  const handleWeightChange = (value: string) => {
    setDisplayedWeight(value)
    const numValue = parseFloat(value) || 0

    if (useGrossWeight && formData.empty_spool_weight) {
      // User entered gross weight, store net weight
      const netWeight = Math.max(0, numValue - formData.empty_spool_weight)
      setFormData((prev) => ({ ...prev, current_weight: netWeight }))
    } else {
      // User entered net weight directly
      setFormData((prev) => ({ ...prev, current_weight: numValue }))
    }
  }

  // Handle toggle between gross/net weight mode
  const handleWeightModeChange = (useGross: boolean) => {
    const currentNet = formData.current_weight || 0
    const spoolWeight = formData.empty_spool_weight || 0

    if (useGross && spoolWeight) {
      // Switching TO gross mode: display = net + spool
      setDisplayedWeight((currentNet + spoolWeight).toString())
    } else {
      // Switching TO net mode: display = net
      setDisplayedWeight(currentNet.toString())
    }
    setUseGrossWeight(useGross)
  }

  // Calculate remaining percentage for display using actual net weight
  const remainingPercentage = formData.current_weight && formData.initial_weight
    ? ((formData.current_weight / formData.initial_weight) * 100).toFixed(0)
    : '0'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Spool {spool?.spool_id}</DialogTitle>
          <DialogDescription>
            Update filament spool information and weight tracking.
          </DialogDescription>
        </DialogHeader>

        {loadingSpool ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3">Loading spool data...</span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Required Fields */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="spool_id">
                    Spool ID <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="spool_id"
                    placeholder="FIL-001"
                    value={formData.spool_id}
                    onChange={(e) => handleInputChange('spool_id', e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="material_type">
                    Material Type <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={formData.material_type_id}
                    onValueChange={(value) => handleInputChange('material_type_id', value)}
                    disabled={loadingMaterials}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select material..." />
                    </SelectTrigger>
                    <SelectContent>
                      {sortedMaterials.length > 0 && sortedMaterials.map((mat) => (
                        <SelectItem key={mat.id} value={mat.id}>
                          {mat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="brand">
                    Brand <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="brand"
                    list="brand-list"
                    placeholder="Polymaker"
                    value={formData.brand}
                    onChange={(e) => handleInputChange('brand', getDisplayName(e.target.value))}
                    onBlur={(e) => handleInputChange('brand', getDisplayName(e.target.value))}
                    required
                  />
                  <datalist id="brand-list">
                    {uniqueBrands.map((brand) => (
                      <option key={brand} value={brand} />
                    ))}
                  </datalist>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="color">
                    Colour <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="color"
                    placeholder="Galaxy Black"
                    value={formData.color}
                    onChange={(e) => handleInputChange('color', e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="finish">Finish</Label>
                  <Input
                    id="finish"
                    placeholder="Matte, Glossy, etc."
                    value={formData.finish || ''}
                    onChange={(e) => handleInputChange('finish', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="empty_spool_weight">
                    Empty Spool Weight (g)
                  </Label>
                  <Input
                    id="empty_spool_weight"
                    type="number"
                    placeholder="250"
                    value={formData.empty_spool_weight || ''}
                    onChange={(e) => handleInputChange('empty_spool_weight', e.target.value ? parseFloat(e.target.value) : undefined)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Weight of the plastic spool without filament
                  </p>
                </div>
              </div>

              {/* Weight Mode Toggle (only show if empty_spool_weight is set) */}
              {formData.empty_spool_weight && (
                <div className="flex items-center gap-4 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="use_gross_weight"
                      checked={useGrossWeight}
                      onChange={(e) => handleWeightModeChange(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <Label htmlFor="use_gross_weight" className="text-sm font-normal cursor-pointer">
                      Enter gross weight (what you weigh on scales)
                    </Label>
                  </div>
                  {useGrossWeight && (
                    <span className="text-xs text-muted-foreground">
                      Will subtract {formData.empty_spool_weight}g spool weight
                    </span>
                  )}
                </div>
              )}

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="initial_weight">
                    Initial Filament (g) <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="initial_weight"
                    type="number"
                    placeholder="1000"
                    value={formData.initial_weight}
                    onChange={(e) => handleInputChange('initial_weight', parseFloat(e.target.value))}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="current_weight">
                    {useGrossWeight ? 'Gross Weight (g)' : 'Current Filament (g)'} <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="current_weight"
                    type="number"
                    step="0.1"
                    placeholder={useGrossWeight ? 'Weigh spool on scale' : '1000'}
                    value={displayedWeight}
                    onChange={(e) => handleWeightChange(e.target.value)}
                    required
                  />
                  {useGrossWeight && formData.empty_spool_weight && displayedWeight && (
                    <p className="text-xs text-muted-foreground">
                      Filament: {getNetWeight().toFixed(0)}g (gross - {formData.empty_spool_weight}g spool)
                    </p>
                  )}
                  {!useGrossWeight && (
                    <p className="text-xs text-muted-foreground">
                      {remainingPercentage}% remaining
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label className="text-muted-foreground">
                    {useGrossWeight ? 'Calculated Filament' : 'Gross Weight'}
                  </Label>
                  <div className="h-10 flex items-center px-3 bg-muted rounded-md text-sm">
                    {useGrossWeight
                      ? `${getNetWeight().toFixed(0)}g`
                      : formData.empty_spool_weight
                        ? `${((formData.current_weight || 0) + formData.empty_spool_weight).toFixed(0)}g`
                        : '—'
                    }
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {useGrossWeight
                      ? `${remainingPercentage}% remaining`
                      : formData.empty_spool_weight
                        ? 'Filament + spool'
                        : 'Set empty spool weight first'
                    }
                  </p>
                </div>
              </div>
            </div>

            {/* Optional Purchase Info */}
            <div className="border-t pt-4 space-y-4">
              <h4 className="text-sm font-medium">Purchase Information (Optional)</h4>

              {/* Batch Tracking */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="purchased_quantity">
                    Purchased Quantity <span className="text-muted-foreground text-xs">(spools)</span>
                  </Label>
                  <Input
                    id="purchased_quantity"
                    type="number"
                    min="1"
                    placeholder="1"
                    value={formData.purchased_quantity || 1}
                    onChange={(e) => handleInputChange('purchased_quantity', parseInt(e.target.value) || 1)}
                  />
                  <p className="text-xs text-muted-foreground">
                    How many spools were in this batch purchase?
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="spools_remaining">
                    Spools Remaining <span className="text-muted-foreground text-xs">(spools)</span>
                  </Label>
                  <Input
                    id="spools_remaining"
                    type="number"
                    min="0"
                    max={formData.purchased_quantity || 1}
                    placeholder="1"
                    value={formData.spools_remaining || 1}
                    onChange={(e) => handleInputChange('spools_remaining', parseInt(e.target.value) || 1)}
                  />
                  <p className="text-xs text-muted-foreground">
                    How many spools are left from this batch?
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="currency">Currency</Label>
                  <Select value={currency} onValueChange={setCurrency}>
                    <SelectTrigger id="currency">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GBP">£ GBP</SelectItem>
                      <SelectItem value="USD">$ USD</SelectItem>
                      <SelectItem value="EUR">€ EUR</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="purchase_price">Price</Label>
                  <Input
                    id="purchase_price"
                    type="number"
                    step="0.01"
                    placeholder="8.30"
                    value={formData.purchase_price || ''}
                    onChange={(e) =>
                      handleInputChange('purchase_price', e.target.value ? parseFloat(e.target.value) : undefined)
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    {currency} per spool
                  </p>
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
              </div>

              <div className="space-y-2">
                <Label htmlFor="supplier">Supplier</Label>
                <Input
                  id="supplier"
                  list="supplier-list"
                  placeholder="Amazon, MatterHackers, etc."
                  value={formData.supplier || ''}
                  onChange={(e) => handleInputChange('supplier', getDisplayName(e.target.value))}
                  onBlur={(e) => handleInputChange('supplier', getDisplayName(e.target.value))}
                />
                <datalist id="supplier-list">
                  {uniqueSuppliers.map((supplier) => (
                    <option key={supplier} value={supplier} />
                  ))}
                </datalist>
              </div>
            </div>

            {/* Optional Organization */}
            <div className="border-t pt-4 space-y-4">
              <h4 className="text-sm font-medium">Organization (Optional)</h4>
              <div className="space-y-2">
                <Label htmlFor="storage_location">Storage Location</Label>
                <Input
                  id="storage_location"
                  placeholder="Shelf A3, Bin 12, etc."
                  value={formData.storage_location || ''}
                  onChange={(e) => handleInputChange('storage_location', e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <textarea
                  id="notes"
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="Any additional notes about this spool..."
                  value={formData.notes || ''}
                  onChange={(e) => handleInputChange('notes', e.target.value)}
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active ?? true}
                  onChange={(e) => handleInputChange('is_active', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="is_active" className="text-sm font-normal cursor-pointer">
                  Spool is active (uncheck to mark as depleted/retired)
                </Label>
              </div>
            </div>

            {/* Error Display */}
            {updateMutation.isError && (
              <div className="bg-destructive/10 border border-destructive rounded-md p-3">
                <p className="text-sm text-destructive">
                  Failed to update spool: {updateMutation.error instanceof Error ? updateMutation.error.message : 'Unknown error'}
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
                Update Spool
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
