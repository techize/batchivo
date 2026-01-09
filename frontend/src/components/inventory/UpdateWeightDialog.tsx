import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { spoolsApi } from '@/lib/api/spools'

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
import { Loader2, Scale } from 'lucide-react'

interface UpdateWeightDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  spoolId: string | null
}

export function UpdateWeightDialog({ open, onOpenChange, spoolId }: UpdateWeightDialogProps) {
  const queryClient = useQueryClient()

  // Fetch the specific spool
  const { data: spool, isLoading: loadingSpool } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => spoolsApi.get(spoolId!),
    enabled: !!spoolId && open,
  })

  const [newWeight, setNewWeight] = useState<string>('')
  const [useGrossWeight, setUseGrossWeight] = useState(false)

  // Reset form when spool changes
  useEffect(() => {
    if (spool && open) {
      setNewWeight(spool.current_weight.toString())
      setUseGrossWeight(false)
    }
  }, [spool, open])

  // Calculate net weight from gross weight if empty_spool_weight is set
  const getNetWeight = (): number => {
    const enteredWeight = parseFloat(newWeight) || 0
    if (useGrossWeight && spool?.empty_spool_weight) {
      return Math.max(0, enteredWeight - spool.empty_spool_weight)
    }
    return enteredWeight
  }

  // Calculate changes using net weight (accounting for spool weight if gross mode)
  const netWeight = getNetWeight()

  const weightDifference = spool && newWeight
    ? netWeight - spool.current_weight
    : 0

  const newPercentage = spool && newWeight
    ? ((netWeight / spool.initial_weight) * 100).toFixed(1)
    : '0'

  const oldPercentage = spool
    ? ((spool.current_weight / spool.initial_weight) * 100).toFixed(1)
    : '0'

  // Update mutation using the specialized updateWeight endpoint
  const updateMutation = useMutation({
    mutationFn: (weight: number) => spoolsApi.updateWeight(spoolId!, weight),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['spools'] })
      queryClient.invalidateQueries({ queryKey: ['spool', spoolId] })
      onOpenChange(false)
      setNewWeight('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const enteredWeight = parseFloat(newWeight)
    if (isNaN(enteredWeight) || enteredWeight < 0) {
      alert('Please enter a valid weight')
      return
    }

    // Use net weight (subtracts spool weight if in gross mode)
    const weight = getNetWeight()

    if (!spool || weight > spool.initial_weight) {
      alert(`Filament weight cannot exceed initial weight of ${spool?.initial_weight}g`)
      return
    }

    if (weight < 0) {
      alert('Calculated filament weight cannot be negative. Check the gross weight entered.')
      return
    }

    updateMutation.mutate(weight)
  }

  const handleQuickDecrease = (amount: number) => {
    if (!spool) return
    const current = parseFloat(newWeight) || spool.current_weight
    const newValue = Math.max(0, current - amount)
    setNewWeight(newValue.toString())
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Scale className="h-5 w-5" />
            Update Weight
          </DialogTitle>
          <DialogDescription>
            {spool ? (
              <>Update current weight for {spool.spool_id} - {spool.material_type_code} {spool.color}</>
            ) : (
              'Loading spool information...'
            )}
          </DialogDescription>
        </DialogHeader>

        {loadingSpool ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3">Loading...</span>
          </div>
        ) : spool ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Current Weight Display */}
            <div className="rounded-lg border bg-muted/50 p-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Current Filament</span>
                <span className="text-lg font-semibold">{spool.current_weight}g</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Initial Filament</span>
                <span className="text-sm">{spool.initial_weight}g</span>
              </div>
              {spool.empty_spool_weight && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Empty Spool</span>
                  <span className="text-sm">{spool.empty_spool_weight}g</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Current Remaining</span>
                <span className="text-sm">{oldPercentage}%</span>
              </div>
            </div>

            {/* Weight Mode Toggle (only show if empty_spool_weight is set) */}
            {spool.empty_spool_weight && (
              <div className="flex items-center gap-4 p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="use_gross_weight"
                    checked={useGrossWeight}
                    onChange={(e) => setUseGrossWeight(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <Label htmlFor="use_gross_weight" className="text-sm font-normal cursor-pointer">
                    Enter gross weight (spool + filament)
                  </Label>
                </div>
                {useGrossWeight && (
                  <span className="text-xs text-muted-foreground">
                    Will subtract {spool.empty_spool_weight}g
                  </span>
                )}
              </div>
            )}

            {/* New Weight Input */}
            <div className="space-y-2">
              <Label htmlFor="new_weight">
                {useGrossWeight ? 'Gross Weight (g)' : 'Filament Weight (g)'} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="new_weight"
                type="number"
                step="0.1"
                placeholder={useGrossWeight ? 'Weigh spool on scale' : 'Enter filament weight'}
                value={newWeight}
                onChange={(e) => setNewWeight(e.target.value)}
                required
                autoFocus
              />
              {useGrossWeight && spool.empty_spool_weight && newWeight && (
                <p className="text-xs text-muted-foreground">
                  Filament weight: {netWeight.toFixed(1)}g (gross - {spool.empty_spool_weight}g spool)
                </p>
              )}
            </div>

            {/* Quick Decrease Buttons */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Quick Adjustments</Label>
              <div className="grid grid-cols-4 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickDecrease(10)}
                >
                  -10g
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickDecrease(25)}
                >
                  -25g
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickDecrease(50)}
                >
                  -50g
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickDecrease(100)}
                >
                  -100g
                </Button>
              </div>
            </div>

            {/* Change Summary */}
            {newWeight && !isNaN(parseFloat(newWeight)) && (
              <div className="rounded-lg border p-4 space-y-2 bg-card">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Change</span>
                  <span className={`text-lg font-semibold ${weightDifference < 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    {weightDifference > 0 ? '+' : ''}{weightDifference.toFixed(1)}g
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">New Remaining</span>
                  <span className={`text-lg font-semibold ${parseFloat(newPercentage) < 20 ? 'text-destructive' : parseFloat(newPercentage) < 50 ? 'text-yellow-600' : 'text-green-600'}`}>
                    {newPercentage}%
                  </span>
                </div>
                {parseFloat(newPercentage) < 20 && (
                  <div className="text-xs text-destructive mt-2">
                    ⚠️ Low stock! Consider reordering.
                  </div>
                )}
              </div>
            )}

            {/* Error Display */}
            {updateMutation.isError && (
              <div className="bg-destructive/10 border border-destructive rounded-md p-3">
                <p className="text-sm text-destructive">
                  Failed to update weight: {updateMutation.error instanceof Error ? updateMutation.error.message : 'Unknown error'}
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
                Update Weight
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            Failed to load spool data
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
