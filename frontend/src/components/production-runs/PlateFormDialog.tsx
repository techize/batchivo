/**
 * PlateFormDialog Component
 *
 * Dialog for creating and editing plates within a production run.
 */

import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createProductionRunPlate,
  updateProductionRunPlate,
  getProductionRunPlate,
} from '@/lib/api/production-runs'
import { listModels } from '@/lib/api/models'
import { getActivePrinters } from '@/lib/api/printers'
import type { ProductionRunPlateCreate, ProductionRunPlateUpdate } from '@/types/production-run-plate'
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
import { Textarea } from '@/components/ui/textarea'
import { Loader2 } from 'lucide-react'

interface PlateFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  runId: string
  plateId?: string | null
  plateNumber?: number
}

export function PlateFormDialog({
  open,
  onOpenChange,
  runId,
  plateId,
  plateNumber = 1,
}: PlateFormDialogProps) {
  const queryClient = useQueryClient()
  const isEdit = !!plateId

  // Fetch models for dropdown
  const { data: modelsData } = useQuery({
    queryKey: ['models', { limit: 500 }],
    queryFn: () => listModels({ limit: 500 }),
    enabled: open,
  })

  // Fetch printers for dropdown
  const { data: printers } = useQuery({
    queryKey: ['printers-active'],
    queryFn: () => getActivePrinters(),
    enabled: open,
  })

  // Fetch plate details for editing
  const { data: plate, isLoading: isLoadingPlate } = useQuery({
    queryKey: ['production-run-plate', runId, plateId],
    queryFn: () => (plateId ? getProductionRunPlate(runId, plateId) : null),
    enabled: !!plateId && open,
  })

  // Form state
  const [formData, setFormData] = useState<{
    model_id: string
    printer_id: string
    plate_number: number
    plate_name: string
    prints_per_plate: number
    print_time_minutes?: number
    estimated_material_weight_grams?: number
    notes?: string
  }>({
    model_id: '',
    printer_id: '',
    plate_number: plateNumber,
    plate_name: `Plate ${plateNumber}`,
    prints_per_plate: 1,
    print_time_minutes: undefined,
    estimated_material_weight_grams: undefined,
    notes: '',
  })

  // Populate form when plate is loaded (edit mode)
  useEffect(() => {
    if (plate) {
      setFormData({
        model_id: plate.model_id,
        printer_id: plate.printer_id,
        plate_number: plate.plate_number,
        plate_name: plate.plate_name,
        prints_per_plate: plate.prints_per_plate,
        print_time_minutes: plate.print_time_minutes ?? undefined,
        estimated_material_weight_grams: plate.estimated_material_weight_grams ?? undefined,
        notes: plate.notes ?? '',
      })
    } else if (!plateId && open) {
      // Reset form for new plate
      setFormData({
        model_id: '',
        printer_id: '',
        plate_number: plateNumber,
        plate_name: `Plate ${plateNumber}`,
        prints_per_plate: 1,
        print_time_minutes: undefined,
        estimated_material_weight_grams: undefined,
        notes: '',
      })
    }
  }, [plate, plateId, plateNumber, open])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: ProductionRunPlateCreate) => createProductionRunPlate(runId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
      onOpenChange(false)
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: ProductionRunPlateUpdate) =>
      plateId ? updateProductionRunPlate(runId, plateId, data) : Promise.reject('No ID'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
      onOpenChange(false)
    },
  })

  const mutation = isEdit ? updateMutation : createMutation
  const isPending = mutation.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.model_id || !formData.printer_id) {
      alert('Please select a model and printer')
      return
    }

    if (formData.prints_per_plate < 1) {
      alert('Prints per plate must be at least 1')
      return
    }

    if (isEdit) {
      updateMutation.mutate({
        notes: formData.notes || null,
      })
    } else {
      createMutation.mutate({
        model_id: formData.model_id,
        printer_id: formData.printer_id,
        plate_number: formData.plate_number,
        plate_name: formData.plate_name,
        prints_per_plate: formData.prints_per_plate,
        print_time_minutes: formData.print_time_minutes || null,
        estimated_material_weight_grams: formData.estimated_material_weight_grams || null,
        notes: formData.notes || null,
      })
    }
  }

  const handleInputChange = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const isLoading = isEdit && isLoadingPlate
  const models = modelsData?.models || []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Plate' : 'Add Plate'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update plate notes. Model and printer cannot be changed after creation.'
              : 'Add a new print plate to this production run.'}
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-2">Loading...</span>
          </div>
        )}

        {!isLoading && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Plate Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="plate_number">Plate Number</Label>
                <Input
                  id="plate_number"
                  type="number"
                  min="1"
                  value={formData.plate_number}
                  onChange={(e) => handleInputChange('plate_number', parseInt(e.target.value) || 1)}
                  disabled={isEdit}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="plate_name">Plate Name</Label>
                <Input
                  id="plate_name"
                  placeholder="e.g., Plate 1, Batch A"
                  value={formData.plate_name}
                  onChange={(e) => handleInputChange('plate_name', e.target.value)}
                  disabled={isEdit}
                />
              </div>
            </div>

            {/* Model Selection */}
            <div className="space-y-2">
              <Label htmlFor="model_id">
                Model <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.model_id}
                onValueChange={(value) => handleInputChange('model_id', value)}
                disabled={isEdit}
              >
                <SelectTrigger id="model_id">
                  <SelectValue placeholder="Select a model..." />
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      {model.name} ({model.sku})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Printer Selection */}
            <div className="space-y-2">
              <Label htmlFor="printer_id">
                Printer <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.printer_id}
                onValueChange={(value) => handleInputChange('printer_id', value)}
                disabled={isEdit}
              >
                <SelectTrigger id="printer_id">
                  <SelectValue placeholder="Select a printer..." />
                </SelectTrigger>
                <SelectContent>
                  {(printers || []).map((printer) => (
                    <SelectItem key={printer.id} value={printer.id}>
                      {printer.name}
                      {printer.manufacturer && ` (${printer.manufacturer})`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Prints per Plate */}
            <div className="space-y-2">
              <Label htmlFor="prints_per_plate">
                Prints per Plate <span className="text-destructive">*</span>
              </Label>
              <Input
                id="prints_per_plate"
                type="number"
                min="1"
                value={formData.prints_per_plate}
                onChange={(e) =>
                  handleInputChange('prints_per_plate', parseInt(e.target.value) || 1)
                }
                disabled={isEdit}
              />
              <p className="text-xs text-muted-foreground">
                Number of copies of the model on this plate
              </p>
            </div>

            {/* Optional Fields */}
            {!isEdit && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="print_time_minutes">Print Time (min)</Label>
                  <Input
                    id="print_time_minutes"
                    type="number"
                    min="0"
                    placeholder="Optional"
                    value={formData.print_time_minutes ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'print_time_minutes',
                        e.target.value ? parseInt(e.target.value) : undefined
                      )
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="estimated_material_weight_grams">Est. Material (g)</Label>
                  <Input
                    id="estimated_material_weight_grams"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="Optional"
                    value={formData.estimated_material_weight_grams ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'estimated_material_weight_grams',
                        e.target.value ? parseFloat(e.target.value) : undefined
                      )
                    }
                  />
                </div>
              </div>
            )}

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Any notes about this plate..."
                value={formData.notes || ''}
                onChange={(e) => handleInputChange('notes', e.target.value)}
              />
            </div>

            {/* Error Display */}
            {mutation.isError && (
              <div className="bg-destructive/10 border border-destructive rounded-md p-3">
                <p className="text-sm text-destructive">
                  Failed to {isEdit ? 'update' : 'create'} plate:{' '}
                  {mutation.error instanceof Error ? mutation.error.message : 'Unknown error'}
                </p>
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEdit ? 'Save Changes' : 'Add Plate'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
