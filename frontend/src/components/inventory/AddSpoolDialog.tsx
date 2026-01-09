import { useState, useEffect, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { spoolsApi, materialTypesApi } from '@/lib/api/spools'
import type { SpoolCreate } from '@/types/spool'
import type { SpoolmanDBFilament } from '@/types/spoolmandb'
import { SpoolmanDBPicker } from './SpoolmanDBPicker'
import { useNextSKU } from '@/hooks/useSKU'

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
import { Switch } from '@/components/ui/switch'
import { Loader2, Sparkles, Droplets, RefreshCw } from 'lucide-react'

interface AddSpoolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddSpoolDialog({ open, onOpenChange }: AddSpoolDialogProps) {
  const queryClient = useQueryClient()

  // Auto-generate spool ID
  const { nextSKU, isLoading: isLoadingSKU, refetch: refetchSKU } = useNextSKU('FIL', open)

  // Fetch material types for dropdown
  const { data: materialTypes, isLoading: loadingMaterials } = useQuery({
    queryKey: ['material-types'],
    queryFn: () => materialTypesApi.list(),
  })

  // Fetch existing spools for brand/supplier suggestions
  const { data: spoolData } = useQuery({
    queryKey: ['spools', { page: 1, page_size: 100 }],
    queryFn: () => spoolsApi.list({ page: 1, page_size: 100 }),
  })

  // Form state
  const [formData, setFormData] = useState<Partial<SpoolCreate>>({
    spool_id: '',
    material_type_id: '',
    brand: '',
    color: '',
    color_hex: undefined,
    finish: '',
    // Filament specifications
    diameter: 1.75,
    density: undefined,
    extruder_temp: undefined,
    bed_temp: undefined,
    // Special properties
    translucent: false,
    glow: false,
    pattern: undefined,
    spool_type: undefined,
    // Weight
    initial_weight: 1000, // Default 1kg
    current_weight: 1000,
    empty_spool_weight: undefined,
    // Purchase
    purchase_date: undefined,
    purchase_price: undefined,
    supplier: '',
    purchased_quantity: 1,
    spools_remaining: 1,
    // Organization
    storage_location: '',
    notes: '',
    is_active: true,
  })

  // Additional UI state for bulk purchases
  const [quantity, setQuantity] = useState(1)
  const [currency, setCurrency] = useState('GBP')
  const [customSupplier, setCustomSupplier] = useState('')

  // SpoolmanDB integration
  const [selectedSpoolmanDBFilament, setSelectedSpoolmanDBFilament] = useState<SpoolmanDBFilament | null>(null)

  // Handle SpoolmanDB filament selection - auto-fill form fields
  const handleSpoolmanDBSelect = (filament: SpoolmanDBFilament) => {
    setSelectedSpoolmanDBFilament(filament)

    // Map SpoolmanDB material to our material type
    const matchingMaterial = materialTypes?.find(
      m => m.code.toUpperCase() === filament.material.toUpperCase() ||
           m.name.toUpperCase() === filament.material.toUpperCase()
    )

    setFormData(prev => ({
      ...prev,
      brand: filament.manufacturer_name,
      color: filament.name,
      color_hex: filament.color_hex || undefined,
      finish: filament.finish || '',
      initial_weight: filament.weight,
      current_weight: filament.weight,
      empty_spool_weight: filament.spool_weight || undefined,
      material_type_id: matchingMaterial?.id || prev.material_type_id,
      // Filament specifications from SpoolmanDB
      diameter: filament.diameter || 1.75,
      density: filament.density || undefined,
      extruder_temp: filament.extruder_temp || undefined,
      bed_temp: filament.bed_temp || undefined,
      // Special filament properties
      translucent: filament.translucent || false,
      glow: filament.glow || false,
      pattern: filament.pattern || undefined,
      spool_type: filament.spool_type || undefined,
    }))
  }

  const handleSpoolmanDBClear = () => {
    setSelectedSpoolmanDBFilament(null)
  }

  // Calculate cost per spool
  const costPerSpool = formData.purchase_price && quantity > 0
    ? (formData.purchase_price / quantity).toFixed(2)
    : '0.00'

  // Auto-fill spool ID when nextSKU is fetched
  // formData.spool_id intentionally excluded to prevent re-run when this effect sets it
  useEffect(() => {
    if (open && nextSKU && !formData.spool_id) {
      setFormData(prev => ({ ...prev, spool_id: nextSKU }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, nextSKU])

  // Set PLA as default material when dialog opens
  useEffect(() => {
    if (open && materialTypes && materialTypes.length > 0) {
      const plaType = materialTypes.find(m => m.code === 'PLA')
      if (plaType && !formData.material_type_id) {
        setFormData(prev => ({ ...prev, material_type_id: plaType.id }))
      }
    }
  }, [open, materialTypes, formData.material_type_id])

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

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: SpoolCreate) => spoolsApi.create(data),
    onSuccess: () => {
      // Invalidate and refetch spools list
      queryClient.invalidateQueries({ queryKey: ['spools'] })
      // Close dialog and reset form
      onOpenChange(false)
      resetForm()
    },
  })

  const resetForm = () => {
    setFormData({
      spool_id: '',
      material_type_id: '',
      brand: '',
      color: '',
      color_hex: undefined,
      finish: '',
      diameter: 1.75,
      density: undefined,
      extruder_temp: undefined,
      bed_temp: undefined,
      translucent: false,
      glow: false,
      pattern: undefined,
      spool_type: undefined,
      initial_weight: 1000,
      current_weight: 1000,
      empty_spool_weight: undefined,
      purchase_date: undefined,
      purchase_price: undefined,
      supplier: '',
      purchased_quantity: 1,
      spools_remaining: 1,
      storage_location: '',
      notes: '',
      is_active: true,
    })
    setQuantity(1)
    setCurrency('GBP')
    setCustomSupplier('')
    setSelectedSpoolmanDBFilament(null)
  }

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

    createMutation.mutate(formData as SpoolCreate)
  }

  const handleInputChange = (field: keyof SpoolCreate, value: string | number | boolean | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] md:max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Spool</DialogTitle>
          <DialogDescription>
            Create a new filament spool entry in your inventory.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* SpoolmanDB Lookup */}
          <div className="bg-muted/50 rounded-lg p-4 border">
            <SpoolmanDBPicker
              onSelect={handleSpoolmanDBSelect}
              onClear={handleSpoolmanDBClear}
              selectedFilament={selectedSpoolmanDBFilament}
            />
          </div>

          {/* Required Fields */}
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="spool_id">
                  Spool ID <span className="text-destructive">*</span>
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="spool_id"
                    placeholder={isLoadingSKU ? 'Loading...' : 'FIL-001'}
                    value={formData.spool_id}
                    onChange={(e) => handleInputChange('spool_id', e.target.value)}
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
                          setFormData(prev => ({ ...prev, spool_id: result.data.next_sku }))
                        }
                      })
                    }}
                    disabled={isLoadingSKU}
                    title="Generate new Spool ID"
                  >
                    <RefreshCw className={`h-4 w-4 ${isLoadingSKU ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">Auto-generated, but you can edit it</p>
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
                    {sortedMaterials.length === 0 && (
                      <div className="p-2 text-sm text-muted-foreground">
                        No materials available
                      </div>
                    )}
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
                {uniqueBrands.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {uniqueBrands.length} existing brand{uniqueBrands.length !== 1 ? 's' : ''} available
                  </p>
                )}
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

            <div className="grid grid-cols-3 gap-4">
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
                <Label htmlFor="initial_weight">
                  Initial Weight (g) <span className="text-destructive">*</span>
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
                  Current Weight (g) <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="current_weight"
                  type="number"
                  placeholder="1000"
                  value={formData.current_weight}
                  onChange={(e) => handleInputChange('current_weight', parseFloat(e.target.value))}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="empty_spool_weight">Empty Spool Weight (g)</Label>
                <Input
                  id="empty_spool_weight"
                  type="number"
                  step="0.1"
                  placeholder="e.g., 190"
                  value={formData.empty_spool_weight || ''}
                  onChange={(e) => handleInputChange('empty_spool_weight', e.target.value ? parseFloat(e.target.value) : null)}
                />
                <p className="text-xs text-muted-foreground">
                  For gross weight calculations when weighing
                </p>
              </div>
            </div>
          </div>

          {/* Filament Properties (Optional - auto-filled from SpoolmanDB) */}
          <div className="border-t pt-4 space-y-4">
            <h4 className="text-sm font-medium">Filament Properties (Optional)</h4>
            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="diameter">Diameter (mm)</Label>
                <Select
                  value={String(formData.diameter || 1.75)}
                  onValueChange={(value) => handleInputChange('diameter', parseFloat(value))}
                >
                  <SelectTrigger id="diameter">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1.75">1.75mm</SelectItem>
                    <SelectItem value="2.85">2.85mm</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="color_hex">Colour</Label>
                <div className="flex gap-2">
                  <div
                    className="w-10 h-10 rounded-md border border-input flex-shrink-0"
                    style={{
                      backgroundColor: formData.color_hex
                        ? `#${formData.color_hex.length === 8 ? formData.color_hex.slice(2) : formData.color_hex}`
                        : '#e5e7eb'
                    }}
                  />
                  <Input
                    id="color_hex"
                    placeholder="FF5733"
                    value={formData.color_hex || ''}
                    onChange={(e) => handleInputChange('color_hex', e.target.value.replace('#', '') || null)}
                    maxLength={9}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="extruder_temp">Extruder Temp (°C)</Label>
                <Input
                  id="extruder_temp"
                  type="number"
                  placeholder="210"
                  value={formData.extruder_temp || ''}
                  onChange={(e) => handleInputChange('extruder_temp', e.target.value ? parseInt(e.target.value) : null)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="bed_temp">Bed Temp (°C)</Label>
                <Input
                  id="bed_temp"
                  type="number"
                  placeholder="60"
                  value={formData.bed_temp || ''}
                  onChange={(e) => handleInputChange('bed_temp', e.target.value ? parseInt(e.target.value) : null)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="pattern">Pattern</Label>
                <Input
                  id="pattern"
                  placeholder="Marble, Gradient, Speckled..."
                  value={formData.pattern || ''}
                  onChange={(e) => handleInputChange('pattern', e.target.value || null)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="spool_type">Spool Type</Label>
                <Select
                  value={formData.spool_type || '__none__'}
                  onValueChange={(value) => handleInputChange('spool_type', value === '__none__' ? null : value)}
                >
                  <SelectTrigger id="spool_type">
                    <SelectValue placeholder="Select type..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">Not specified</SelectItem>
                    <SelectItem value="plastic">Plastic</SelectItem>
                    <SelectItem value="cardboard">Cardboard</SelectItem>
                    <SelectItem value="refill">Refill (no spool)</SelectItem>
                    <SelectItem value="masterspool">MasterSpool</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex flex-wrap gap-6">
              <div className="flex items-center gap-2">
                <Switch
                  id="translucent"
                  checked={formData.translucent || false}
                  onCheckedChange={(checked) => handleInputChange('translucent', checked)}
                />
                <Label htmlFor="translucent" className="flex items-center gap-1.5 cursor-pointer">
                  <Droplets className="h-4 w-4 text-muted-foreground" />
                  Translucent
                </Label>
              </div>

              <div className="flex items-center gap-2">
                <Switch
                  id="glow"
                  checked={formData.glow || false}
                  onCheckedChange={(checked) => handleInputChange('glow', checked)}
                />
                <Label htmlFor="glow" className="flex items-center gap-1.5 cursor-pointer">
                  <Sparkles className="h-4 w-4 text-muted-foreground" />
                  Glow-in-the-Dark
                </Label>
              </div>
            </div>
          </div>

          {/* Optional Purchase Info */}
          <div className="border-t pt-4 space-y-4">
            <h4 className="text-sm font-medium">Purchase Information (Optional)</h4>
            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="quantity">Number of Spools</Label>
                <Input
                  id="quantity"
                  type="number"
                  min="1"
                  value={quantity}
                  onChange={(e) => {
                    const qty = parseInt(e.target.value) || 1
                    setQuantity(qty)
                    setFormData(prev => ({
                      ...prev,
                      purchased_quantity: qty,
                      spools_remaining: qty
                    }))
                  }}
                />
                <p className="text-xs text-muted-foreground">How many spools in this purchase</p>
              </div>

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
                <Label htmlFor="purchase_price">Total Price</Label>
                <Input
                  id="purchase_price"
                  type="number"
                  step="0.01"
                  placeholder="41.48"
                  value={formData.purchase_price || ''}
                  onChange={(e) =>
                    handleInputChange('purchase_price', e.target.value ? parseFloat(e.target.value) : undefined)
                  }
                />
                <p className="text-xs text-muted-foreground">
                  {currency}{costPerSpool} per spool
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
              {formData.supplier === '__custom__' ? (
                <div className="space-y-2">
                  <Input
                    placeholder="Enter supplier name"
                    value={customSupplier}
                    onChange={(e) => setCustomSupplier(e.target.value)}
                    onBlur={() => {
                      if (customSupplier.trim()) {
                        handleInputChange('supplier', getDisplayName(customSupplier))
                        setCustomSupplier('')
                      } else {
                        handleInputChange('supplier', '')
                      }
                    }}
                    autoFocus
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      handleInputChange('supplier', '')
                      setCustomSupplier('')
                    }}
                  >
                    ← Back to list
                  </Button>
                </div>
              ) : (
                <Select
                  value={formData.supplier || ''}
                  onValueChange={(value) => {
                    if (value === '__custom__') {
                      handleInputChange('supplier', '__custom__')
                    } else {
                      handleInputChange('supplier', value)
                    }
                  }}
                >
                  <SelectTrigger id="supplier">
                    <SelectValue placeholder="Amazon, MatterHackers, etc." />
                  </SelectTrigger>
                  <SelectContent>
                    {uniqueSuppliers.map((supplier) => (
                      <SelectItem key={supplier} value={supplier}>
                        {supplier}
                      </SelectItem>
                    ))}
                    <SelectItem value="__custom__">+ Add new supplier</SelectItem>
                  </SelectContent>
                </Select>
              )}
              {uniqueSuppliers.length > 0 && formData.supplier !== '__custom__' && (
                <p className="text-xs text-muted-foreground">
                  {uniqueSuppliers.length} existing supplier{uniqueSuppliers.length !== 1 ? 's' : ''} available
                </p>
              )}
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
          </div>

          {/* Error Display */}
          {createMutation.isError && (
            <div className="bg-destructive/10 border border-destructive rounded-md p-3">
              <p className="text-sm text-destructive">
                Failed to create spool: {createMutation.error instanceof Error ? createMutation.error.message : 'Unknown error'}
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
              Create Spool
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
