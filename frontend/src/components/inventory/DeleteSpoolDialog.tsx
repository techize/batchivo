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
import { Loader2, AlertTriangle } from 'lucide-react'

interface DeleteSpoolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  spoolId: string | null
}

export function DeleteSpoolDialog({ open, onOpenChange, spoolId }: DeleteSpoolDialogProps) {
  const queryClient = useQueryClient()

  // Fetch the specific spool to show details
  const { data: spool, isLoading: loadingSpool } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => spoolsApi.get(spoolId!),
    enabled: !!spoolId && open,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => spoolsApi.delete(spoolId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['spools'] })
      onOpenChange(false)
    },
  })

  const handleDelete = () => {
    if (!spoolId) return
    deleteMutation.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Delete Spool
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete the spool from your inventory.
          </DialogDescription>
        </DialogHeader>

        {loadingSpool ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3">Loading spool data...</span>
          </div>
        ) : spool ? (
          <div className="space-y-4">
            {/* Spool Details */}
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Spool ID</span>
                <span className="font-mono font-semibold">{spool.spool_id}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Material</span>
                <span>{spool.material_type_code}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Brand</span>
                <span>{spool.brand}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Colour</span>
                <span>{spool.color}</span>
              </div>
              {spool.finish && (
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Finish</span>
                  <span>{spool.finish}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Current Weight</span>
                <span>{spool.current_weight}g ({spool.remaining_percentage.toFixed(0)}% remaining)</span>
              </div>
            </div>

            {/* Warning Message */}
            <div className="flex items-start gap-2 p-3 rounded-md bg-muted">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="font-medium">Consider marking as inactive instead</p>
                <p className="text-muted-foreground mt-1">
                  You can mark this spool as inactive in the Edit dialog to keep historical records while removing it from active inventory.
                </p>
              </div>
            </div>

            {/* Error Display */}
            {deleteMutation.isError && (
              <div className="bg-destructive/10 border border-destructive rounded-md p-3">
                <p className="text-sm text-destructive">
                  Failed to delete spool: {deleteMutation.error instanceof Error ? deleteMutation.error.message : 'Unknown error'}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            Failed to load spool data
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteMutation.isPending || !spool}
          >
            {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Delete Permanently
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
