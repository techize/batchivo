import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { consumablesApi } from '@/lib/api/consumables'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Loader2 } from 'lucide-react'

interface DeleteConsumableDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  consumableId: string | null
}

export function DeleteConsumableDialog({
  open,
  onOpenChange,
  consumableId,
}: DeleteConsumableDialogProps) {
  const queryClient = useQueryClient()

  // Fetch consumable details
  const { data: consumable } = useQuery({
    queryKey: ['consumables', consumableId],
    queryFn: () => (consumableId ? consumablesApi.get(consumableId) : null),
    enabled: !!consumableId && open,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => (consumableId ? consumablesApi.delete(consumableId) : Promise.reject('No ID')),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['consumables'] })
      onOpenChange(false)
    },
  })

  const handleDelete = () => {
    deleteMutation.mutate()
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Consumable</AlertDialogTitle>
          <AlertDialogDescription>
            {consumable ? (
              <>
                Are you sure you want to delete <strong>{consumable.name}</strong> (SKU:{' '}
                {consumable.sku})?
                {consumable.quantity_on_hand > 0 && (
                  <span className="block mt-2 text-warning">
                    Warning: This consumable still has {consumable.quantity_on_hand}{' '}
                    {consumable.unit_of_measure} in stock.
                  </span>
                )}
                <span className="block mt-2">
                  This action cannot be undone. All purchase history and usage records will also be
                  deleted.
                </span>
              </>
            ) : (
              'Are you sure you want to delete this consumable?'
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {deleteMutation.isError && (
          <div className="bg-destructive/10 border border-destructive rounded-md p-3">
            <p className="text-sm text-destructive">
              Failed to delete:{' '}
              {deleteMutation.error instanceof Error
                ? deleteMutation.error.message
                : 'Unknown error'}
            </p>
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
