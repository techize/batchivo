/**
 * EditRunDialog Component
 *
 * Dialog for editing a production run with status-based restrictions:
 * - in_progress runs: Allow editing all fields
 * - completed/failed/cancelled runs: Only allow editing notes
 */

import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Pencil, AlertCircle, Loader2, Info, Lock } from 'lucide-react'

import {
  updateProductionRun,
  updateProductionRunItem,
  updateProductionRunMaterial,
} from '@/lib/api/production-runs'
import type { ProductionRunDetail } from '@/types/production-run'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'

interface EditRunDialogProps {
  run: ProductionRunDetail
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

interface ItemEdit {
  itemId: string
  modelName: string
  currentQuantity: number
  newQuantity: number
}

interface MaterialEdit {
  materialId: string
  spoolName: string
  currentWeight: number
  newWeight: number
}

export function EditRunDialog({
  run,
  open,
  onOpenChange,
  onSuccess,
}: EditRunDialogProps) {
  const queryClient = useQueryClient()

  // Determine if run is immutable (only notes editable)
  const isImmutable = ['completed', 'failed', 'cancelled'].includes(run.status)

  // Basic info state
  const [printerName, setPrinterName] = useState('')
  const [slicerSoftware, setSlicerSoftware] = useState('')
  const [bedTemp, setBedTemp] = useState<number | ''>('')
  const [nozzleTemp, setNozzleTemp] = useState<number | ''>('')
  const [estimatedTime, setEstimatedTime] = useState<number | ''>('')
  const [notes, setNotes] = useState('')

  // Items and materials state
  const [items, setItems] = useState<ItemEdit[]>([])
  const [materials, setMaterials] = useState<MaterialEdit[]>([])

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize form from run data
  useEffect(() => {
    if (open) {
      // Basic info
      setPrinterName(run.printer_name || '')
      setSlicerSoftware(run.slicer_software || '')
      setBedTemp(run.bed_temperature ?? '')
      setNozzleTemp(run.nozzle_temperature ?? '')
      setEstimatedTime(run.estimated_print_time_hours ?? '')
      setNotes(run.notes || '')

      // Items
      if (run.items && run.items.length > 0) {
        const itemEdits: ItemEdit[] = run.items.map((item) => ({
          itemId: item.id,
          modelName: item.model?.name || item.model?.sku || `Model ${item.model_id.substring(0, 8)}`,
          currentQuantity: item.quantity,
          newQuantity: item.quantity,
        }))
        setItems(itemEdits)
      } else {
        setItems([])
      }

      // Materials
      if (run.materials && run.materials.length > 0) {
        const materialEdits: MaterialEdit[] = run.materials.map((material) => {
          const spool = material.spool
          let spoolName: string
          if (spool) {
            const materialType = spool.material_type?.name || spool.material_type?.code || ''
            spoolName = `${spool.brand} ${spool.color}${materialType ? ` (${materialType})` : ''}`
          } else {
            spoolName = `Spool ${material.spool_id.substring(0, 8)}`
          }

          const currentWeight = material.estimated_total_weight ??
            ((material.estimated_model_weight_grams || 0) +
             (material.estimated_flushed_grams || 0) +
             (material.estimated_tower_grams || 0))

          return {
            materialId: material.id,
            spoolName,
            currentWeight: Math.round((currentWeight || 0) * 10) / 10,
            newWeight: Math.round((currentWeight || 0) * 10) / 10,
          }
        })
        setMaterials(materialEdits)
      } else {
        setMaterials([])
      }

      setError(null)
    }
  }, [open, run])

  // Handle item quantity change
  const handleItemQuantityChange = (itemId: string, value: string) => {
    const numValue = parseInt(value) || 0
    setItems((prev) =>
      prev.map((item) =>
        item.itemId === itemId ? { ...item, newQuantity: numValue } : item
      )
    )
  }

  // Handle material weight change
  const handleMaterialWeightChange = (materialId: string, value: string) => {
    const numValue = parseFloat(value) || 0
    setMaterials((prev) =>
      prev.map((material) =>
        material.materialId === materialId ? { ...material, newWeight: numValue } : material
      )
    )
  }

  // Submit handler
  const handleSubmit = async () => {
    setIsSubmitting(true)
    setError(null)

    try {
      // If immutable, only update notes
      if (isImmutable) {
        if (notes !== run.notes) {
          await updateProductionRun(run.id, { notes })
        }
      } else {
        // Update basic info
        const basicUpdates: Record<string, unknown> = {}
        if (printerName !== (run.printer_name || '')) basicUpdates.printer_name = printerName || null
        if (slicerSoftware !== (run.slicer_software || '')) basicUpdates.slicer_software = slicerSoftware || null
        if (bedTemp !== (run.bed_temperature ?? '')) basicUpdates.bed_temperature = bedTemp || null
        if (nozzleTemp !== (run.nozzle_temperature ?? '')) basicUpdates.nozzle_temperature = nozzleTemp || null
        if (estimatedTime !== (run.estimated_print_time_hours ?? '')) basicUpdates.estimated_print_time_hours = estimatedTime || null
        if (notes !== (run.notes || '')) basicUpdates.notes = notes || null

        if (Object.keys(basicUpdates).length > 0) {
          await updateProductionRun(run.id, basicUpdates)
        }

        // Update items
        for (const item of items) {
          if (item.newQuantity !== item.currentQuantity) {
            await updateProductionRunItem(run.id, item.itemId, {
              quantity: item.newQuantity,
            })
          }
        }

        // Update materials
        for (const material of materials) {
          if (material.newWeight !== material.currentWeight) {
            await updateProductionRunMaterial(run.id, material.materialId, {
              estimated_model_weight_grams: material.newWeight,
            })
          }
        }
      }

      // Success
      queryClient.invalidateQueries({ queryKey: ['production-runs'] })
      queryClient.invalidateQueries({ queryKey: ['production-run', run.id] })
      onOpenChange(false)
      onSuccess?.()
    } catch (err) {
      console.error('Update run failed:', err)
      const errorMessage = (err as Error).message || 'Failed to update run'
      setError(errorMessage)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Check if anything changed
  const hasChanges = isImmutable
    ? notes !== (run.notes || '')
    : printerName !== (run.printer_name || '') ||
      slicerSoftware !== (run.slicer_software || '') ||
      bedTemp !== (run.bed_temperature ?? '') ||
      nozzleTemp !== (run.nozzle_temperature ?? '') ||
      estimatedTime !== (run.estimated_print_time_hours ?? '') ||
      notes !== (run.notes || '') ||
      items.some((item) => item.newQuantity !== item.currentQuantity) ||
      materials.some((material) => material.newWeight !== material.currentWeight)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Pencil className="h-5 w-5 text-blue-600" />
            Edit Production Run
          </DialogTitle>
          <DialogDescription>
            Run: <span className="font-mono font-medium">{run.run_number}</span>
            <br />
            Status: <span className="font-medium capitalize">{run.status.replace('_', ' ')}</span>
          </DialogDescription>
        </DialogHeader>

        {isImmutable && (
          <Alert>
            <Lock className="h-4 w-4" />
            <AlertDescription>
              This run is {run.status}. Only notes can be edited. All other fields are locked to preserve the audit trail.
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-4 py-4 max-h-[500px] overflow-y-auto">
          {/* Notes (always editable) */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              placeholder="Add notes about this production run..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>

          {/* Only show other fields if not immutable */}
          {!isImmutable && (
            <>
              <Separator />

              <Tabs defaultValue="basic" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="basic">Basic Info</TabsTrigger>
                  <TabsTrigger value="items">Items ({items.length})</TabsTrigger>
                  <TabsTrigger value="materials">Materials ({materials.length})</TabsTrigger>
                </TabsList>

                {/* Basic Info Tab */}
                <TabsContent value="basic" className="space-y-4 mt-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="printer">Printer Name</Label>
                      <Input
                        id="printer"
                        placeholder="e.g., Prusa i3 MK3S"
                        value={printerName}
                        onChange={(e) => setPrinterName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="slicer">Slicer Software</Label>
                      <Input
                        id="slicer"
                        placeholder="e.g., PrusaSlicer 2.6"
                        value={slicerSoftware}
                        onChange={(e) => setSlicerSoftware(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="bedTemp">Bed Temperature (°C)</Label>
                      <Input
                        id="bedTemp"
                        type="number"
                        min="0"
                        max="200"
                        placeholder="60"
                        value={bedTemp}
                        onChange={(e) => setBedTemp(e.target.value ? parseInt(e.target.value) : '')}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="nozzleTemp">Nozzle Temperature (°C)</Label>
                      <Input
                        id="nozzleTemp"
                        type="number"
                        min="0"
                        max="500"
                        placeholder="210"
                        value={nozzleTemp}
                        onChange={(e) => setNozzleTemp(e.target.value ? parseInt(e.target.value) : '')}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="estimatedTime">Estimated Print Time (hours)</Label>
                    <Input
                      id="estimatedTime"
                      type="number"
                      min="0"
                      step="0.1"
                      placeholder="5.5"
                      value={estimatedTime}
                      onChange={(e) => setEstimatedTime(e.target.value ? parseFloat(e.target.value) : '')}
                    />
                  </div>
                </TabsContent>

                {/* Items Tab */}
                <TabsContent value="items" className="space-y-3 mt-4">
                  {items.length === 0 ? (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>No items in this production run.</AlertDescription>
                    </Alert>
                  ) : (
                    <div className="space-y-2">
                      {items.map((item) => (
                        <div
                          key={item.itemId}
                          className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30"
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{item.modelName}</p>
                            <p className="text-xs text-muted-foreground">
                              Current: {item.currentQuantity}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Label htmlFor={`item-${item.itemId}`} className="text-sm">
                              Quantity:
                            </Label>
                            <Input
                              id={`item-${item.itemId}`}
                              type="number"
                              min="1"
                              className="w-20 text-right"
                              value={item.newQuantity}
                              onChange={(e) => handleItemQuantityChange(item.itemId, e.target.value)}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>

                {/* Materials Tab */}
                <TabsContent value="materials" className="space-y-3 mt-4">
                  {materials.length === 0 ? (
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>No materials in this production run.</AlertDescription>
                    </Alert>
                  ) : (
                    <div className="space-y-2">
                      {materials.map((material) => (
                        <div
                          key={material.materialId}
                          className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30"
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{material.spoolName}</p>
                            <p className="text-xs text-muted-foreground">
                              Current: {material.currentWeight.toFixed(1)}g
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Input
                              type="number"
                              min="0"
                              step="0.1"
                              className="w-24 text-right"
                              value={material.newWeight}
                              onChange={(e) => handleMaterialWeightChange(material.materialId, e.target.value)}
                            />
                            <span className="text-sm text-muted-foreground w-4">g</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !hasChanges}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Pencil className="mr-2 h-4 w-4" />
                Save Changes
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
