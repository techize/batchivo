/**
 * PlatesSection Component
 *
 * Displays and manages plates within a production run.
 * Shows plate status, allows starting, completing, failing, and cancelling plates.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Loader2,
  Plus,
  Play,
  CheckCircle,
  XCircle,
  Ban,
  Trash2,
  LayoutGrid,
} from 'lucide-react'

import {
  listProductionRunPlates,
  startProductionRunPlate,
  deleteProductionRunPlate,
  formatPlateStatus,
  getPlateStatusColor,
} from '@/lib/api/production-runs'
import type { ProductionRunPlate } from '@/types/production-run-plate'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { PlateFormDialog } from './PlateFormDialog'
import { PlateActionsDialog } from './PlateActionsDialog'

interface PlatesSectionProps {
  runId: string
  runStatus: string
}

export function PlatesSection({ runId, runStatus }: PlatesSectionProps) {
  const queryClient = useQueryClient()

  const [formDialogOpen, setFormDialogOpen] = useState(false)
  const [editingPlateId, setEditingPlateId] = useState<string | null>(null)
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionType, setActionType] = useState<'complete' | 'fail' | 'cancel'>('complete')
  const [selectedPlate, setSelectedPlate] = useState<ProductionRunPlate | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingPlate, setDeletingPlate] = useState<ProductionRunPlate | null>(null)

  // Fetch plates
  const { data, isLoading, error } = useQuery({
    queryKey: ['production-run-plates', runId],
    queryFn: () => listProductionRunPlates(runId, { limit: 100 }),
  })

  // Start plate mutation
  const startMutation = useMutation({
    mutationFn: (plateId: string) => startProductionRunPlate(runId, plateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
    },
  })

  // Delete plate mutation
  const deleteMutation = useMutation({
    mutationFn: (plateId: string) => deleteProductionRunPlate(runId, plateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production-run', runId] })
      queryClient.invalidateQueries({ queryKey: ['production-run-plates', runId] })
      setDeleteDialogOpen(false)
    },
  })

  const plates = data?.plates || []
  const nextPlateNumber = plates.length + 1

  const handleAddPlate = () => {
    setEditingPlateId(null)
    setFormDialogOpen(true)
  }

  const handleStartPlate = (plate: ProductionRunPlate) => {
    startMutation.mutate(plate.id)
  }

  const handleCompletePlate = (plate: ProductionRunPlate) => {
    setSelectedPlate(plate)
    setActionType('complete')
    setActionDialogOpen(true)
  }

  const handleFailPlate = (plate: ProductionRunPlate) => {
    setSelectedPlate(plate)
    setActionType('fail')
    setActionDialogOpen(true)
  }

  const handleCancelPlate = (plate: ProductionRunPlate) => {
    setSelectedPlate(plate)
    setActionType('cancel')
    setActionDialogOpen(true)
  }

  const handleDeletePlate = (plate: ProductionRunPlate) => {
    setDeletingPlate(plate)
    setDeleteDialogOpen(true)
  }

  const getStatusBadgeClass = (status: string): string => {
    const color = getPlateStatusColor(status)
    switch (color) {
      case 'blue':
        return 'bg-blue-500/10 text-blue-600 border-blue-200'
      case 'green':
        return 'bg-green-500/10 text-green-600 border-green-200'
      case 'red':
        return 'bg-red-500/10 text-red-600 border-red-200'
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-200'
    }
  }

  const canAddPlate = runStatus === 'in_progress'
  const canModifyPlates = runStatus === 'in_progress'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <LayoutGrid className="h-5 w-5" />
            <CardTitle>Print Plates</CardTitle>
            <Badge variant="secondary">{plates.length}</Badge>
          </div>
          {canAddPlate && (
            <Button size="sm" onClick={handleAddPlate}>
              <Plus className="mr-2 h-4 w-4" />
              Add Plate
            </Button>
          )}
        </div>
        <CardDescription>
          Individual print jobs within this production run. Each plate represents one print on a
          specific printer.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Loading State */}
        {isLoading && (
          <div className="flex h-[100px] items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="ml-3">Loading plates...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-8 text-destructive">
            Error loading plates: {(error as Error).message}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && plates.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <LayoutGrid className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4">No plates added yet.</p>
            {canAddPlate && (
              <Button onClick={handleAddPlate} className="mt-4" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add First Plate
              </Button>
            )}
          </div>
        )}

        {/* Mobile Card View */}
        {!isLoading && !error && plates.length > 0 && (
          <div className="lg:hidden space-y-3">
            {plates.map((plate) => (
              <div key={plate.id} className="rounded-lg border p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="font-medium">{plate.plate_name}</div>
                    <p className="text-sm text-muted-foreground">
                      {plate.model?.name || 'Unknown Model'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {plate.printer?.name || 'Unknown Printer'}
                    </p>
                  </div>
                  <Badge variant="outline" className={getStatusBadgeClass(plate.status)}>
                    {formatPlateStatus(plate.status)}
                  </Badge>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <span>
                    {plate.successful_prints}/{plate.prints_per_plate} prints
                  </span>
                  {plate.print_time_minutes && <span>• {plate.print_time_minutes} min</span>}
                </div>

                {canModifyPlates && (
                  <div className="flex flex-wrap gap-2">
                    {plate.status === 'pending' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleStartPlate(plate)}
                        disabled={startMutation.isPending}
                      >
                        <Play className="h-3 w-3 mr-1" />
                        Start
                      </Button>
                    )}
                    {(plate.status === 'pending' || plate.status === 'printing') && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCompletePlate(plate)}
                        >
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Complete
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleFailPlate(plate)}>
                          <XCircle className="h-3 w-3 mr-1" />
                          Fail
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelPlate(plate)}
                        >
                          <Ban className="h-3 w-3 mr-1" />
                          Cancel
                        </Button>
                      </>
                    )}
                    {plate.status === 'pending' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-destructive"
                        onClick={() => handleDeletePlate(plate)}
                      >
                        <Trash2 className="h-3 w-3 mr-1" />
                        Delete
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Desktop Table View */}
        {!isLoading && !error && plates.length > 0 && (
          <div className="hidden lg:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Plate</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Printer</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  <TableHead className="text-right w-[100px]">Prints</TableHead>
                  <TableHead className="text-right w-[100px]">Time (min)</TableHead>
                  <TableHead className="w-[200px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plates.map((plate) => (
                  <TableRow key={plate.id} className="group">
                    <TableCell className="font-medium">{plate.plate_name}</TableCell>
                    <TableCell>
                      {plate.model ? (
                        <div>
                          <div className="font-medium">{plate.model.name}</div>
                          <div className="text-xs text-muted-foreground">{plate.model.sku}</div>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">Unknown</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {plate.printer ? (
                        <span>{plate.printer.name}</span>
                      ) : (
                        <span className="text-muted-foreground">Unknown</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={getStatusBadgeClass(plate.status)}>
                        {formatPlateStatus(plate.status)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {plate.successful_prints}/{plate.prints_per_plate}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {plate.actual_print_time_minutes ||
                        plate.print_time_minutes ||
                        '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {canModifyPlates && (
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {plate.status === 'pending' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleStartPlate(plate)}
                              disabled={startMutation.isPending}
                              title="Start printing"
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          {(plate.status === 'pending' || plate.status === 'printing') && (
                            <>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleCompletePlate(plate)}
                                title="Mark complete"
                              >
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleFailPlate(plate)}
                                title="Mark failed"
                              >
                                <XCircle className="h-4 w-4 text-red-600" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleCancelPlate(plate)}
                                title="Cancel plate"
                              >
                                <Ban className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                          {plate.status === 'pending' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeletePlate(plate)}
                              title="Delete plate"
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>

      {/* Dialogs */}
      <PlateFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        runId={runId}
        plateId={editingPlateId}
        plateNumber={nextPlateNumber}
      />

      <PlateActionsDialog
        open={actionDialogOpen}
        onOpenChange={setActionDialogOpen}
        runId={runId}
        plate={selectedPlate}
        action={actionType}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Plate</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{deletingPlate?.plate_name}</strong>? This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault()
                if (deletingPlate) {
                  deleteMutation.mutate(deletingPlate.id)
                }
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
    </Card>
  )
}
