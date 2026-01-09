/**
 * CompleteRunDialog Component
 *
 * Dialog for completing a production run with:
 * - Actual material weights (pre-populated from estimates)
 * - Item success/failure counts
 */

import { useState, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle, AlertCircle, Loader2, Scale, PenLine, Package, Clock, Pencil } from 'lucide-react'

import {
  updateProductionRun,
  updateProductionRunMaterial,
  updateProductionRunItem,
  completeProductionRun,
} from '@/lib/api/production-runs'
import type { ProductionRunDetail } from '@/types/production-run'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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

interface CompleteRunDialogProps {
  run: ProductionRunDetail
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  editMode?: boolean  // If true, just update without completing
}

interface MaterialWeight {
  materialId: string
  spoolId: string
  spoolName: string
  estimated: number
  actual: number
  // For weighing mode
  weightBefore: number | null
  weightAfter: number | null
}

interface ItemResult {
  itemId: string
  modelName: string
  quantity: number
  successful: number
  failed: number
}

type EntryMode = 'manual' | 'weighing'

export function CompleteRunDialog({
  run,
  open,
  onOpenChange,
  onSuccess,
  editMode = false,
}: CompleteRunDialogProps) {
  const queryClient = useQueryClient()

  // State
  const [entryMode, setEntryMode] = useState<EntryMode>('manual')
  const [materialWeights, setMaterialWeights] = useState<MaterialWeight[]>([])
  const [itemResults, setItemResults] = useState<ItemResult[]>([])
  const [durationHours, setDurationHours] = useState<number>(0)
  const [startedAt, setStartedAt] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Detect if run is already completed - treat as edit mode to prevent re-completion attempts
  const isRunCompleted = run.status === 'completed'
  const effectiveEditMode = editMode || isRunCompleted

  // Initialize material weights and item results from run data
  useEffect(() => {
    if (open) {
      // Initialize materials
      if (run.materials.length > 0) {
        const weights: MaterialWeight[] = run.materials.map((material) => {
          // Get spool display name from nested spool object
          const spool = material.spool
          let spoolName: string
          if (spool) {
            // Build name from brand + color, or fallback to spool_id
            const materialType = spool.material_type?.name || spool.material_type?.code || ''
            spoolName = `${spool.brand} ${spool.color}${materialType ? ` (${materialType})` : ''}`
          } else {
            spoolName = `Spool ${material.spool_id.substring(0, 8)}`
          }

          // Use the computed estimated_total_weight, or calculate from components
          const estimated = material.estimated_total_weight ??
            ((material.estimated_model_weight_grams || 0) +
             (material.estimated_flushed_grams || 0) +
             (material.estimated_tower_grams || 0))

          // Use existing actual if available, otherwise use estimated
          const existingActual = material.actual_total_weight > 0
            ? material.actual_total_weight
            : (material.actual_weight_from_weighing ?? null)

          return {
            materialId: material.id,
            spoolId: material.spool_id,
            spoolName,
            estimated: Math.round((estimated || 0) * 10) / 10, // Round to 1 decimal
            actual: existingActual ?? Math.round((estimated || 0) * 10) / 10,
            weightBefore: material.spool_weight_before_grams ?? null,
            weightAfter: material.spool_weight_after_grams ?? null,
          }
        })
        setMaterialWeights(weights)
      }

      // Initialize items - default successful to quantity, failed to 0
      if (run.items && run.items.length > 0) {
        const items: ItemResult[] = run.items.map((item) => ({
          itemId: item.id,
          modelName: item.model?.name || item.model?.sku || `Model ${item.model_id.substring(0, 8)}`,
          quantity: item.quantity,
          // Use existing values if set, otherwise default all to successful
          successful: item.successful_quantity ?? item.quantity,
          failed: item.failed_quantity ?? 0,
        }))
        setItemResults(items)
      }

      // Initialize duration from estimated print time
      const estimatedHours = Number(run.estimated_print_time_hours ?? 0)
      setDurationHours(Math.round(estimatedHours * 100) / 100)

      // Initialize started_at - format for datetime-local input
      if (run.started_at) {
        const date = new Date(run.started_at)
        // Format as YYYY-MM-DDTHH:MM for datetime-local input
        const formatted = date.toISOString().slice(0, 16)
        setStartedAt(formatted)
      }

      setError(null)
    }
  }, [open, run.materials, run.items, run.estimated_print_time_hours, run.started_at])

  // Handle weight change (manual mode)
  const handleWeightChange = (materialId: string, value: string) => {
    const numValue = parseFloat(value) || 0
    setMaterialWeights((prev) =>
      prev.map((m) =>
        m.materialId === materialId ? { ...m, actual: numValue } : m
      )
    )
  }

  // Handle weighing change (before/after)
  const handleWeighingChange = (
    materialId: string,
    field: 'weightBefore' | 'weightAfter',
    value: string
  ) => {
    const numValue = value ? parseFloat(value) : null
    setMaterialWeights((prev) =>
      prev.map((m) => {
        if (m.materialId !== materialId) return m
        const updated = { ...m, [field]: numValue }
        // Auto-calculate actual from weighing if both values present
        if (updated.weightBefore !== null && updated.weightAfter !== null) {
          updated.actual = Math.max(0, updated.weightBefore - updated.weightAfter)
        }
        return updated
      })
    )
  }

  // Copy all estimated to actual
  const handleCopyAllEstimated = () => {
    setMaterialWeights((prev) =>
      prev.map((m) => ({ ...m, actual: m.estimated }))
    )
  }

  // Handle item success/failure change
  const handleItemChange = (
    itemId: string,
    field: 'successful' | 'failed',
    value: string
  ) => {
    const numValue = parseInt(value) || 0
    setItemResults((prev) =>
      prev.map((item) => {
        if (item.itemId !== itemId) return item
        const updated = { ...item, [field]: numValue }
        // Auto-adjust the other field to not exceed quantity
        if (field === 'successful') {
          updated.failed = Math.min(updated.failed, item.quantity - numValue)
        } else {
          updated.successful = Math.min(updated.successful, item.quantity - numValue)
        }
        return updated
      })
    )
  }

  // Set all items as successful
  const handleAllSuccessful = () => {
    setItemResults((prev) =>
      prev.map((item) => ({ ...item, successful: item.quantity, failed: 0 }))
    )
  }

  // Submit handler
  const handleSubmit = async () => {
    setIsSubmitting(true)
    setError(null)

    try {
      // Skip material/item updates if run is already completed (backend will reject them)
      if (!isRunCompleted) {
        // Step 1: Update each material with actual weights
        for (const material of materialWeights) {
          const updateData: Record<string, number | null> = {}

          if (entryMode === 'weighing' && material.weightBefore !== null && material.weightAfter !== null) {
            // Weighing mode - set before/after weights
            updateData.spool_weight_before_grams = material.weightBefore
            updateData.spool_weight_after_grams = material.weightAfter
          } else {
            // Manual mode - set actual model weight
            updateData.actual_model_weight_grams = material.actual
          }

          await updateProductionRunMaterial(run.id, material.materialId, updateData)
        }

        // Step 2: Update each item with success/failure counts
        for (const item of itemResults) {
          await updateProductionRunItem(run.id, item.itemId, {
            successful_quantity: item.successful,
            failed_quantity: item.failed,
          })
        }
      }

      // Step 3: Update duration and start time (must happen BEFORE completion)
      // Wrapped in try-catch: if this fails because run is already completed, that's OK
      if (!isRunCompleted) {
        try {
          const runUpdates: Record<string, unknown> = {}
          if (durationHours > 0) {
            runUpdates.duration_hours = durationHours
          }
          if (startedAt) {
            runUpdates.started_at = new Date(startedAt).toISOString()
          }
          if (Object.keys(runUpdates).length > 0) {
            await updateProductionRun(run.id, runUpdates)
          }
        } catch (updateErr) {
          // If update fails because run was just completed, continue - that's the goal
          console.warn('Duration/time update failed (run may already be completed):', updateErr)
        }
      }

      // Step 4: Complete the run (skip if editing or run is already completed)
      if (!effectiveEditMode) {
        await completeProductionRun(run.id)
      }

      // Success
      queryClient.invalidateQueries({ queryKey: ['production-runs'] })
      queryClient.invalidateQueries({ queryKey: ['production-run', run.id] })
      onOpenChange(false)
      onSuccess?.()
    } catch (err) {
      console.error('Complete run failed:', err)
      setError((err as Error).message || 'Failed to complete run')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Validation
  const isValid = materialWeights.every((m) => {
    if (entryMode === 'weighing') {
      return m.weightBefore !== null && m.weightAfter !== null && m.weightBefore >= m.weightAfter
    }
    return m.actual > 0
  })

  // Calculate totals
  const totalEstimated = materialWeights.reduce((sum, m) => sum + m.estimated, 0)
  const totalActual = materialWeights.reduce((sum, m) => sum + m.actual, 0)
  const variance = totalActual - totalEstimated
  const variancePercent = totalEstimated > 0 ? (variance / totalEstimated) * 100 : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {effectiveEditMode ? (
              <>
                <Pencil className="h-5 w-5 text-blue-600" />
                Edit Production Run
              </>
            ) : (
              <>
                <CheckCircle className="h-5 w-5 text-green-600" />
                Complete Production Run
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            Run: <span className="font-mono font-medium">{run.run_number}</span>
            <br />
            {effectiveEditMode
              ? 'Update material weights, item results, and duration.'
              : 'Confirm or adjust the actual material usage before completing.'}
          </DialogDescription>
        </DialogHeader>

        {/* Warning if run was already completed */}
        {isRunCompleted && !editMode && (
          <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-700 dark:text-amber-300">
              This run is already completed. No changes can be made.
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-4 py-4">
          {/* Entry Mode Tabs */}
          <Tabs value={entryMode} onValueChange={(v) => setEntryMode(v as EntryMode)}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="manual" className="flex items-center gap-2">
                <PenLine className="h-4 w-4" />
                Manual Entry
              </TabsTrigger>
              <TabsTrigger value="weighing" className="flex items-center gap-2">
                <Scale className="h-4 w-4" />
                Spool Weighing
              </TabsTrigger>
            </TabsList>

            {/* Manual Entry Mode */}
            <TabsContent value="manual" className="space-y-4 mt-4">
              <div className="flex justify-between items-center">
                <Label className="text-sm font-medium">Material Weights (grams)</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCopyAllEstimated}
                  disabled={isRunCompleted}
                >
                  Reset to Estimated
                </Button>
              </div>

              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                {materialWeights.map((material) => (
                  <div
                    key={material.materialId}
                    className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{material.spoolName}</p>
                      <p className="text-xs text-muted-foreground">
                        Estimated: {material.estimated.toFixed(1)}g
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min="0"
                        step="0.1"
                        className="w-24 text-right"
                        value={material.actual || ''}
                        onChange={(e) =>
                          handleWeightChange(material.materialId, e.target.value)
                        }
                        disabled={isRunCompleted}
                      />
                      <span className="text-sm text-muted-foreground w-4">g</span>
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>

            {/* Weighing Mode */}
            <TabsContent value="weighing" className="space-y-4 mt-4">
              <p className="text-sm text-muted-foreground">
                Enter the spool weight before and after printing for accurate usage tracking.
              </p>

              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                {materialWeights.map((material) => (
                  <div
                    key={material.materialId}
                    className="p-3 rounded-lg border bg-muted/30 space-y-2"
                  >
                    <p className="text-sm font-medium truncate">{material.spoolName}</p>
                    <div className="grid grid-cols-3 gap-2 items-center">
                      <div>
                        <Label className="text-xs">Before (g)</Label>
                        <Input
                          type="number"
                          min="0"
                          step="0.1"
                          placeholder="0"
                          value={material.weightBefore ?? ''}
                          onChange={(e) =>
                            handleWeighingChange(material.materialId, 'weightBefore', e.target.value)
                          }
                          disabled={isRunCompleted}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">After (g)</Label>
                        <Input
                          type="number"
                          min="0"
                          step="0.1"
                          placeholder="0"
                          value={material.weightAfter ?? ''}
                          onChange={(e) =>
                            handleWeighingChange(material.materialId, 'weightAfter', e.target.value)
                          }
                          disabled={isRunCompleted}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Used</Label>
                        <p className="text-sm font-medium py-2">
                          {material.weightBefore !== null && material.weightAfter !== null
                            ? `${(material.weightBefore - material.weightAfter).toFixed(1)}g`
                            : '—'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>

          {/* Items Section */}
          {itemResults.length > 0 && (
            <>
              <Separator />
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label className="text-sm font-medium flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    Print Results
                  </Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAllSuccessful}
                    disabled={isRunCompleted}
                  >
                    All Successful
                  </Button>
                </div>
                <div className="space-y-2">
                  {itemResults.map((item) => (
                    <div
                      key={item.itemId}
                      className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{item.modelName}</p>
                        <p className="text-xs text-muted-foreground">
                          Quantity: {item.quantity}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1">
                          <Input
                            type="number"
                            min="0"
                            max={item.quantity}
                            className="w-16 text-right text-green-600"
                            value={item.successful}
                            onChange={(e) =>
                              handleItemChange(item.itemId, 'successful', e.target.value)
                            }
                            disabled={isRunCompleted}
                          />
                          <span className="text-xs text-green-600">OK</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Input
                            type="number"
                            min="0"
                            max={item.quantity}
                            className="w-16 text-right text-destructive"
                            value={item.failed}
                            onChange={(e) =>
                              handleItemChange(item.itemId, 'failed', e.target.value)
                            }
                            disabled={isRunCompleted}
                          />
                          <span className="text-xs text-destructive">Fail</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Time & Duration Section */}
          <Separator />
          <div className="space-y-3">
            <Label className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Time & Duration
            </Label>
            <div className="space-y-3 p-3 rounded-lg border bg-muted/30">
              {/* Start Time */}
              <div className="flex items-center gap-3">
                <Label className="w-24 text-sm text-muted-foreground">Started</Label>
                <Input
                  type="datetime-local"
                  className="flex-1"
                  value={startedAt}
                  onChange={(e) => setStartedAt(e.target.value)}
                  disabled={isRunCompleted}
                />
              </div>
              {/* Duration */}
              <div className="flex items-center gap-3">
                <Label className="w-24 text-sm text-muted-foreground">Duration</Label>
                <div className="flex items-center gap-2 flex-1">
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    className="w-24 text-right"
                    value={durationHours || ''}
                    onChange={(e) => setDurationHours(parseFloat(e.target.value) || 0)}
                    disabled={isRunCompleted}
                  />
                  <span className="text-sm text-muted-foreground">hours</span>
                  <span className="text-xs text-muted-foreground ml-2">
                    (Est: {Number(run.estimated_print_time_hours ?? 0).toFixed(2)}h)
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="rounded-lg border p-4 bg-muted/30">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-muted-foreground">Estimated</p>
                <p className="text-lg font-semibold">{totalEstimated.toFixed(1)}g</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Actual</p>
                <p className="text-lg font-semibold">{totalActual.toFixed(1)}g</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Variance</p>
                <p className={`text-lg font-semibold ${variance > 0 ? 'text-orange-600' : variance < 0 ? 'text-green-600' : ''}`}>
                  {variance >= 0 ? '+' : ''}{variance.toFixed(1)}g ({variancePercent.toFixed(1)}%)
                </p>
              </div>
            </div>
          </div>

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
            disabled={isSubmitting || !isValid}
            className={effectiveEditMode ? '' : 'bg-green-600 hover:bg-green-700'}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {effectiveEditMode ? 'Saving...' : 'Completing...'}
              </>
            ) : (
              <>
                {effectiveEditMode ? (
                  <>
                    <Pencil className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Complete Run
                  </>
                )}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
