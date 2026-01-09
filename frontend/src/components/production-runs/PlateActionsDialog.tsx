/**
 * PlateActionsDialog Component
 *
 * Dialog for plate status actions: complete, fail, cancel.
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  completeProductionRunPlate,
  failProductionRunPlate,
  cancelProductionRunPlate,
} from '@/lib/api/production-runs'
import type { ProductionRunPlate, MarkPlateCompleteRequest } from '@/types/production-run-plate'
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
import { Textarea } from '@/components/ui/textarea'
import { Loader2, CheckCircle, XCircle, Ban } from 'lucide-react'

type ActionType = 'complete' | 'fail' | 'cancel'

interface PlateActionsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  runId: string
  plate: ProductionRunPlate | null
  action: ActionType
}

export function PlateActionsDialog({
  open,
  onOpenChange,
  runId,
  plate,
  action,
}: PlateActionsDialogProps) {
  const queryClient = useQueryClient()

  // Form state for complete action
  const [completeData, setCompleteData] = useState<MarkPlateCompleteRequest>({
    successful_prints: plate?.prints_per_plate || 1,
    failed_prints: 0,
    actual_print_time_minutes: undefined,
    actual_material_weight_grams: undefined,
    notes: undefined,
  })

  // Form state for fail/cancel actions
  const [notes, setNotes] = useState('')

  // Reset form when plate changes
  useState(() => {
    if (plate) {
      setCompleteData({
        successful_prints: plate.prints_per_plate,
        failed_prints: 0,
        actual_print_time_minutes: undefined,
        actual_material_weight_grams: undefined,
        notes: undefined,
      })
      setNotes('')
    }
  })

  // Complete mutation
  const completeMutation = useMutation({
    mutationFn: (data: MarkPlateCompleteRequest) =>
      plate ? completeProductionRunPlate(runId, plate.id, data) : Promise.reject('No plate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
      onOpenChange(false)
    },
  })

  // Fail mutation
  const failMutation = useMutation({
    mutationFn: () =>
      plate
        ? failProductionRunPlate(runId, plate.id, notes || undefined)
        : Promise.reject('No plate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
      onOpenChange(false)
    },
  })

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () =>
      plate
        ? cancelProductionRunPlate(runId, plate.id, notes || undefined)
        : Promise.reject('No plate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
      onOpenChange(false)
    },
  })

  const mutation = action === 'complete' ? completeMutation : action === 'fail' ? failMutation : cancelMutation
  const isPending = mutation.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (action === 'complete') {
      completeMutation.mutate(completeData)
    } else if (action === 'fail') {
      failMutation.mutate()
    } else {
      cancelMutation.mutate()
    }
  }

  if (!plate) return null

  const getTitle = () => {
    switch (action) {
      case 'complete':
        return 'Complete Plate'
      case 'fail':
        return 'Mark Plate as Failed'
      case 'cancel':
        return 'Cancel Plate'
    }
  }

  const getDescription = () => {
    switch (action) {
      case 'complete':
        return `Record the results for ${plate.plate_name}.`
      case 'fail':
        return `Mark ${plate.plate_name} as failed. You can optionally add notes about the failure.`
      case 'cancel':
        return `Cancel ${plate.plate_name}. This will mark it as no longer needed.`
    }
  }

  const getIcon = () => {
    switch (action) {
      case 'complete':
        return <CheckCircle className="h-4 w-4" />
      case 'fail':
        return <XCircle className="h-4 w-4" />
      case 'cancel':
        return <Ban className="h-4 w-4" />
    }
  }

  const getButtonText = () => {
    switch (action) {
      case 'complete':
        return 'Complete Plate'
      case 'fail':
        return 'Mark as Failed'
      case 'cancel':
        return 'Cancel Plate'
    }
  }

  const getButtonVariant = (): 'default' | 'destructive' => {
    return action === 'complete' ? 'default' : 'destructive'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getIcon()}
            {getTitle()}
          </DialogTitle>
          <DialogDescription>{getDescription()}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Complete Form */}
          {action === 'complete' && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="successful_prints">Successful Prints</Label>
                  <Input
                    id="successful_prints"
                    type="number"
                    min="0"
                    max={plate.prints_per_plate}
                    value={completeData.successful_prints}
                    onChange={(e) =>
                      setCompleteData((prev) => ({
                        ...prev,
                        successful_prints: parseInt(e.target.value) || 0,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="failed_prints">Failed Prints</Label>
                  <Input
                    id="failed_prints"
                    type="number"
                    min="0"
                    max={plate.prints_per_plate}
                    value={completeData.failed_prints || 0}
                    onChange={(e) =>
                      setCompleteData((prev) => ({
                        ...prev,
                        failed_prints: parseInt(e.target.value) || 0,
                      }))
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="actual_print_time_minutes">Actual Time (min)</Label>
                  <Input
                    id="actual_print_time_minutes"
                    type="number"
                    min="0"
                    placeholder="Optional"
                    value={completeData.actual_print_time_minutes ?? ''}
                    onChange={(e) =>
                      setCompleteData((prev) => ({
                        ...prev,
                        actual_print_time_minutes: e.target.value
                          ? parseInt(e.target.value)
                          : undefined,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="actual_material_weight_grams">Actual Material (g)</Label>
                  <Input
                    id="actual_material_weight_grams"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="Optional"
                    value={completeData.actual_material_weight_grams ?? ''}
                    onChange={(e) =>
                      setCompleteData((prev) => ({
                        ...prev,
                        actual_material_weight_grams: e.target.value
                          ? parseFloat(e.target.value)
                          : undefined,
                      }))
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="complete_notes">Notes</Label>
                <Textarea
                  id="complete_notes"
                  placeholder="Optional notes..."
                  value={completeData.notes || ''}
                  onChange={(e) =>
                    setCompleteData((prev) => ({
                      ...prev,
                      notes: e.target.value || undefined,
                    }))
                  }
                />
              </div>
            </>
          )}

          {/* Fail/Cancel Form */}
          {(action === 'fail' || action === 'cancel') && (
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                placeholder={
                  action === 'fail'
                    ? 'What went wrong? e.g., Nozzle clog, bed adhesion issue...'
                    : 'Why is this being cancelled?'
                }
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          )}

          {/* Error Display */}
          {mutation.isError && (
            <div className="bg-destructive/10 border border-destructive rounded-md p-3">
              <p className="text-sm text-destructive">
                Failed to {action} plate:{' '}
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
            <Button type="submit" variant={getButtonVariant()} disabled={isPending}>
              {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {getButtonText()}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
