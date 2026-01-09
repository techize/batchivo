/**
 * CancelRunDialog Component
 *
 * Dialog for cancelling or marking a production run as failed.
 * Supports two modes:
 * - Cancel: Full reversal or record partial usage
 * - Fail: Record waste with failure reason
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, X, AlertCircle } from 'lucide-react'

import {
  cancelProductionRun,
  failProductionRun,
  getFailureReasons,
  type MaterialUsageEntry,
  type CancelProductionRunRequest,
  type FailProductionRunRequest,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface CancelRunDialogProps {
  run: ProductionRunDetail
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

type DialogMode = 'cancel' | 'fail'
type CancelMode = 'full_reversal' | 'record_partial'

export function CancelRunDialog({
  run,
  open,
  onOpenChange,
  onSuccess,
}: CancelRunDialogProps) {
  const queryClient = useQueryClient()

  // Dialog state
  const [mode, setMode] = useState<DialogMode>('cancel')
  const [cancelMode, setCancelMode] = useState<CancelMode>('full_reversal')
  const [failureReason, setFailureReason] = useState<string>('')
  const [notes, setNotes] = useState<string>('')
  const [materialUsage, setMaterialUsage] = useState<Record<string, number>>({})

  // Initialize material usage from run materials
  const initializeMaterialUsage = () => {
    const usage: Record<string, number> = {}
    run.materials.forEach((material) => {
      usage[material.spool_id] = 0
    })
    setMaterialUsage(usage)
  }

  // Reset form when dialog opens
  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setMode('cancel')
      setCancelMode('full_reversal')
      setFailureReason('')
      setNotes('')
      initializeMaterialUsage()
    }
    onOpenChange(newOpen)
  }

  // Fetch failure reasons
  const { data: failureReasons = [] } = useQuery({
    queryKey: ['failure-reasons'],
    queryFn: getFailureReasons,
    staleTime: 1000 * 60 * 60, // 1 hour
  })

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: (request: CancelProductionRunRequest) =>
      cancelProductionRun(run.id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-runs'] })
      queryClient.invalidateQueries({ queryKey: ['production-run', run.id] })
      onOpenChange(false)
      onSuccess?.()
    },
  })

  // Fail mutation
  const failMutation = useMutation({
    mutationFn: (request: FailProductionRunRequest) =>
      failProductionRun(run.id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-runs'] })
      queryClient.invalidateQueries({ queryKey: ['production-run', run.id] })
      onOpenChange(false)
      onSuccess?.()
    },
  })

  const isLoading = cancelMutation.isPending || failMutation.isPending
  const error = cancelMutation.error || failMutation.error

  // Handle material usage change
  const handleMaterialUsageChange = (spoolId: string, value: string) => {
    const numValue = parseFloat(value) || 0
    setMaterialUsage((prev) => ({
      ...prev,
      [spoolId]: numValue,
    }))
  }

  // Build material entries from state
  const buildMaterialEntries = (): MaterialUsageEntry[] => {
    return Object.entries(materialUsage)
      .filter(([, grams]) => grams > 0)
      .map(([spool_id, grams]) => ({ spool_id, grams }))
  }

  // Handle submit
  const handleSubmit = () => {
    if (mode === 'cancel') {
      const request: CancelProductionRunRequest = {
        cancel_mode: cancelMode,
        partial_usage: cancelMode === 'record_partial' ? buildMaterialEntries() : undefined,
      }
      cancelMutation.mutate(request)
    } else {
      if (!failureReason) return

      const wasteEntries = buildMaterialEntries()
      if (wasteEntries.length === 0) return

      const request: FailProductionRunRequest = {
        failure_reason: failureReason,
        waste_materials: wasteEntries,
        notes: notes || undefined,
      }
      failMutation.mutate(request)
    }
  }

  // Validate form
  const isValid = () => {
    if (mode === 'cancel') {
      if (cancelMode === 'record_partial') {
        return buildMaterialEntries().length > 0
      }
      return true
    } else {
      return failureReason && buildMaterialEntries().length > 0
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {mode === 'cancel' ? (
              <>
                <X className="h-5 w-5 text-muted-foreground" />
                Cancel Production Run
              </>
            ) : (
              <>
                <AlertTriangle className="h-5 w-5 text-destructive" />
                Mark Run as Failed
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            Run: <span className="font-mono font-medium">{run.run_number}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Mode Selection */}
          <div className="space-y-2">
            <Label>Action Type</Label>
            <RadioGroup
              value={mode}
              onValueChange={(v) => setMode(v as DialogMode)}
              className="grid grid-cols-2 gap-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="cancel" id="mode-cancel" />
                <Label htmlFor="mode-cancel" className="cursor-pointer">
                  Cancel Run
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="fail" id="mode-fail" />
                <Label htmlFor="mode-fail" className="cursor-pointer">
                  Mark as Failed
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Cancel Mode Options */}
          {mode === 'cancel' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>How should materials be handled?</Label>
                <RadioGroup
                  value={cancelMode}
                  onValueChange={(v) => setCancelMode(v as CancelMode)}
                  className="space-y-2"
                >
                  <div className="flex items-start space-x-2 p-3 rounded-md border">
                    <RadioGroupItem value="full_reversal" id="cancel-full" className="mt-1" />
                    <div>
                      <Label htmlFor="cancel-full" className="cursor-pointer font-medium">
                        Full Reversal
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        No materials were used. Spools remain unchanged.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-2 p-3 rounded-md border">
                    <RadioGroupItem value="record_partial" id="cancel-partial" className="mt-1" />
                    <div>
                      <Label htmlFor="cancel-partial" className="cursor-pointer font-medium">
                        Record Partial Usage
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Deduct actual filament used before cancellation.
                      </p>
                    </div>
                  </div>
                </RadioGroup>
              </div>

              {/* Partial Usage Entry */}
              {cancelMode === 'record_partial' && run.materials.length > 0 && (
                <div className="space-y-3">
                  <Label>Material Usage (grams)</Label>
                  {run.materials.map((material) => (
                    <div key={material.id} className="flex items-center gap-3">
                      <span className="text-sm flex-1 truncate">
                        Spool: {material.spool_id.substring(0, 8)}...
                      </span>
                      <Input
                        type="number"
                        min="0"
                        step="0.1"
                        placeholder="0"
                        className="w-24"
                        value={materialUsage[material.spool_id] || ''}
                        onChange={(e) =>
                          handleMaterialUsageChange(material.spool_id, e.target.value)
                        }
                      />
                      <span className="text-sm text-muted-foreground">g</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Fail Mode Options */}
          {mode === 'fail' && (
            <div className="space-y-4">
              {/* Failure Reason */}
              <div className="space-y-2">
                <Label htmlFor="failure-reason">Failure Reason *</Label>
                <Select value={failureReason} onValueChange={setFailureReason}>
                  <SelectTrigger id="failure-reason">
                    <SelectValue placeholder="Select a reason..." />
                  </SelectTrigger>
                  <SelectContent>
                    {failureReasons.map((reason) => (
                      <SelectItem key={reason.value} value={reason.value}>
                        {reason.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {failureReason && failureReasons.find((r) => r.value === failureReason)?.description && (
                  <p className="text-xs text-muted-foreground">
                    {failureReasons.find((r) => r.value === failureReason)?.description}
                  </p>
                )}
              </div>

              {/* Waste Entry */}
              <div className="space-y-3">
                <Label>Wasted Filament (grams) *</Label>
                <p className="text-xs text-muted-foreground">
                  Enter the amount of filament wasted for each spool used in this run.
                </p>
                {run.materials.map((material) => (
                  <div key={material.id} className="flex items-center gap-3">
                    <span className="text-sm flex-1 truncate">
                      Spool: {material.spool_id.substring(0, 8)}...
                    </span>
                    <Input
                      type="number"
                      min="0"
                      step="0.1"
                      placeholder="0"
                      className="w-24"
                      value={materialUsage[material.spool_id] || ''}
                      onChange={(e) =>
                        handleMaterialUsageChange(material.spool_id, e.target.value)
                      }
                    />
                    <span className="text-sm text-muted-foreground">g</span>
                  </div>
                ))}
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label htmlFor="notes">Additional Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="Describe what happened..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {(error as Error).message || 'An error occurred'}
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant={mode === 'fail' ? 'destructive' : 'default'}
            onClick={handleSubmit}
            disabled={isLoading || !isValid()}
          >
            {isLoading ? (
              'Processing...'
            ) : mode === 'cancel' ? (
              'Cancel Run'
            ) : (
              'Mark as Failed'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
