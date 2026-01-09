/**
 * PrinterFormDialog Component
 *
 * Dialog for creating and editing printers.
 * Used for both new printer creation and editing existing printers.
 */

import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createPrinter, getPrinter, updatePrinter } from '@/lib/api/printers'
import type { PrinterCreate, PrinterUpdate } from '@/types/printer'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Loader2 } from 'lucide-react'

interface PrinterFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  printerId?: string | null
}

const emptyFormData: PrinterCreate = {
  name: '',
  manufacturer: null,
  model: null,
  serial_number: null,
  bed_size_x_mm: null,
  bed_size_y_mm: null,
  bed_size_z_mm: null,
  nozzle_diameter_mm: 0.4,
  default_bed_temp: null,
  default_nozzle_temp: null,
  notes: null,
  is_active: true,
}

export function PrinterFormDialog({ open, onOpenChange, printerId }: PrinterFormDialogProps) {
  const queryClient = useQueryClient()
  const isEdit = !!printerId

  // Fetch printer details for editing
  const { data: printer, isLoading: isLoadingPrinter } = useQuery({
    queryKey: ['printers', printerId],
    queryFn: () => (printerId ? getPrinter(printerId) : null),
    enabled: !!printerId && open,
  })

  // Form state
  const [formData, setFormData] = useState<PrinterCreate>(emptyFormData)

  // Populate form when printer is loaded (edit mode)
  useEffect(() => {
    if (printer) {
      setFormData({
        name: printer.name,
        manufacturer: printer.manufacturer,
        model: printer.model,
        serial_number: printer.serial_number,
        bed_size_x_mm: printer.bed_size_x_mm,
        bed_size_y_mm: printer.bed_size_y_mm,
        bed_size_z_mm: printer.bed_size_z_mm,
        nozzle_diameter_mm: printer.nozzle_diameter_mm,
        default_bed_temp: printer.default_bed_temp,
        default_nozzle_temp: printer.default_nozzle_temp,
        notes: printer.notes,
        is_active: printer.is_active ?? true,
      })
    } else if (!printerId) {
      // Reset form for new printer
      setFormData(emptyFormData)
    }
  }, [printer, printerId])

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setFormData(emptyFormData)
    }
  }, [open])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: PrinterCreate) => createPrinter(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['printers'] })
      onOpenChange(false)
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: PrinterUpdate) =>
      printerId ? updatePrinter(printerId, data) : Promise.reject('No ID'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['printers'] })
      onOpenChange(false)
    },
  })

  const mutation = isEdit ? updateMutation : createMutation
  const isPending = mutation.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.name.trim()) {
      alert('Please enter a printer name')
      return
    }

    if (isEdit) {
      updateMutation.mutate(formData as PrinterUpdate)
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleInputChange = (field: keyof PrinterCreate, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const isLoading = isEdit && isLoadingPrinter

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Printer' : 'Add Printer'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update printer details and settings.'
              : 'Add a new 3D printer to your fleet.'}
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
            {/* Basic Info */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">
                  Printer Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  placeholder="e.g., Bambu X1C, Prusa MK4"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="manufacturer">Manufacturer</Label>
                  <Input
                    id="manufacturer"
                    placeholder="e.g., Bambu Lab, Prusa"
                    value={formData.manufacturer || ''}
                    onChange={(e) => handleInputChange('manufacturer', e.target.value || null)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Input
                    id="model"
                    placeholder="e.g., X1 Carbon, MK4"
                    value={formData.model || ''}
                    onChange={(e) => handleInputChange('model', e.target.value || null)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="serial_number">Serial Number</Label>
                <Input
                  id="serial_number"
                  placeholder="Optional serial number"
                  value={formData.serial_number || ''}
                  onChange={(e) => handleInputChange('serial_number', e.target.value || null)}
                />
              </div>
            </div>

            {/* Bed Size */}
            <div className="border-t pt-4 space-y-4">
              <h4 className="text-sm font-medium">Build Volume (mm)</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="bed_size_x_mm">X (Width)</Label>
                  <Input
                    id="bed_size_x_mm"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="e.g., 256"
                    value={formData.bed_size_x_mm ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'bed_size_x_mm',
                        e.target.value ? parseFloat(e.target.value) : null
                      )
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bed_size_y_mm">Y (Depth)</Label>
                  <Input
                    id="bed_size_y_mm"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="e.g., 256"
                    value={formData.bed_size_y_mm ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'bed_size_y_mm',
                        e.target.value ? parseFloat(e.target.value) : null
                      )
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bed_size_z_mm">Z (Height)</Label>
                  <Input
                    id="bed_size_z_mm"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="e.g., 256"
                    value={formData.bed_size_z_mm ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'bed_size_z_mm',
                        e.target.value ? parseFloat(e.target.value) : null
                      )
                    }
                  />
                </div>
              </div>
            </div>

            {/* Print Settings */}
            <div className="border-t pt-4 space-y-4">
              <h4 className="text-sm font-medium">Default Settings</h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="nozzle_diameter_mm">Nozzle (mm)</Label>
                  <Input
                    id="nozzle_diameter_mm"
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="2.0"
                    placeholder="0.4"
                    value={formData.nozzle_diameter_mm ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'nozzle_diameter_mm',
                        e.target.value ? parseFloat(e.target.value) : null
                      )
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="default_bed_temp">Bed Temp (°C)</Label>
                  <Input
                    id="default_bed_temp"
                    type="number"
                    min="0"
                    max="150"
                    placeholder="e.g., 60"
                    value={formData.default_bed_temp ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'default_bed_temp',
                        e.target.value ? parseInt(e.target.value) : null
                      )
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="default_nozzle_temp">Nozzle Temp (°C)</Label>
                  <Input
                    id="default_nozzle_temp"
                    type="number"
                    min="0"
                    max="350"
                    placeholder="e.g., 220"
                    value={formData.default_nozzle_temp ?? ''}
                    onChange={(e) =>
                      handleInputChange(
                        'default_nozzle_temp',
                        e.target.value ? parseInt(e.target.value) : null
                      )
                    }
                  />
                </div>
              </div>
            </div>

            {/* Notes */}
            <div className="border-t pt-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="Any additional notes about this printer..."
                  value={formData.notes || ''}
                  onChange={(e) => handleInputChange('notes', e.target.value || null)}
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
                  Active (available for production runs)
                </Label>
              </div>
            </div>

            {/* Error Display */}
            {mutation.isError && (
              <div className="bg-destructive/10 border border-destructive rounded-md p-3">
                <p className="text-sm text-destructive">
                  Failed to {isEdit ? 'update' : 'create'} printer:{' '}
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
                {isEdit ? 'Save Changes' : 'Add Printer'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
