/**
 * DeletePrinterDialog Component
 *
 * Confirmation dialog for deleting a printer.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deletePrinter } from '@/lib/api/printers'
import type { Printer } from '@/types/printer'
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

interface DeletePrinterDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  printer: Printer | null
}

export function DeletePrinterDialog({ open, onOpenChange, printer }: DeletePrinterDialogProps) {
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: () => (printer ? deletePrinter(printer.id) : Promise.reject('No printer')),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['printers'] })
      onOpenChange(false)
    },
  })

  if (!printer) return null

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Printer</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete <strong>{printer.name}</strong>? This action cannot be
            undone.
            {printer.manufacturer && (
              <span className="block mt-2 text-muted-foreground">
                {printer.manufacturer} {printer.model}
              </span>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {deleteMutation.isError && (
          <div className="bg-destructive/10 border border-destructive rounded-md p-3">
            <p className="text-sm text-destructive">
              Failed to delete printer:{' '}
              {deleteMutation.error instanceof Error
                ? deleteMutation.error.message
                : 'Unknown error'}
            </p>
          </div>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault()
              deleteMutation.mutate()
            }}
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
