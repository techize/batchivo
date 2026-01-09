/**
 * ProductionRunForm Component
 *
 * Form for creating a new production run
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, Link } from '@tanstack/react-router'
import { ArrowLeft, Loader2, Plus } from 'lucide-react'

import { createProductionRun } from '@/lib/api/production-runs'
import type { ProductionRunCreate } from '@/types/production-run'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function ProductionRunForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState<Partial<ProductionRunCreate>>({
    started_at: new Date().toISOString(),
    status: 'in_progress',
  })

  const createMutation = useMutation({
    mutationFn: (data: ProductionRunCreate) => createProductionRun(data),
    onSuccess: (newRun) => {
      queryClient.invalidateQueries({ queryKey: ['production-runs'] })
      navigate({ to: '/production-runs/$runId', params: { runId: newRun.id } })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Create production run with current timestamp
    const runData: ProductionRunCreate = {
      started_at: new Date().toISOString(),
      status: 'in_progress',
      printer_name: formData.printer_name,
      slicer_software: formData.slicer_software,
      bed_temperature: formData.bed_temperature,
      nozzle_temperature: formData.nozzle_temperature,
      estimated_print_time_hours: formData.estimated_print_time_hours,
      estimated_total_filament_grams: formData.estimated_total_filament_grams,
      estimated_total_purge_grams: formData.estimated_total_purge_grams,
      notes: formData.notes,
    }

    createMutation.mutate(runData)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/production-runs">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Production Run</h1>
          <p className="text-muted-foreground">Start tracking a new print job</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Run number will be auto-generated when you create the run
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="printer_name">Printer Name</Label>
                <Input
                  id="printer_name"
                  placeholder="e.g., Bambu X1C"
                  value={formData.printer_name || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, printer_name: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="slicer_software">Slicer Software</Label>
                <Input
                  id="slicer_software"
                  placeholder="e.g., Bambu Studio 1.7.0"
                  value={formData.slicer_software || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, slicer_software: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="bed_temperature">Bed Temperature (°C)</Label>
                <Input
                  id="bed_temperature"
                  type="number"
                  step="1"
                  placeholder="e.g., 60"
                  value={formData.bed_temperature || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      bed_temperature: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="nozzle_temperature">Nozzle Temperature (°C)</Label>
                <Input
                  id="nozzle_temperature"
                  type="number"
                  step="1"
                  placeholder="e.g., 220"
                  value={formData.nozzle_temperature || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      nozzle_temperature: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Estimates */}
        <Card>
          <CardHeader>
            <CardTitle>Slicer Estimates</CardTitle>
            <CardDescription>
              Copy these values from your slicer (optional, can add later)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="estimated_print_time_hours">Print Time (hours)</Label>
                <Input
                  id="estimated_print_time_hours"
                  type="number"
                  step="0.01"
                  placeholder="e.g., 4.5"
                  value={formData.estimated_print_time_hours || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      estimated_print_time_hours: e.target.value
                        ? parseFloat(e.target.value)
                        : undefined,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="estimated_total_filament_grams">
                  Filament Weight (g)
                </Label>
                <Input
                  id="estimated_total_filament_grams"
                  type="number"
                  step="0.1"
                  placeholder="e.g., 125.5"
                  value={formData.estimated_total_filament_grams || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      estimated_total_filament_grams: e.target.value
                        ? parseFloat(e.target.value)
                        : undefined,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="estimated_total_purge_grams">Purge/Waste (g)</Label>
                <Input
                  id="estimated_total_purge_grams"
                  type="number"
                  step="0.1"
                  placeholder="e.g., 15.0"
                  value={formData.estimated_total_purge_grams || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      estimated_total_purge_grams: e.target.value
                        ? parseFloat(e.target.value)
                        : undefined,
                    })
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notes */}
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
            <CardDescription>
              Any additional information about this run (optional)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              id="notes"
              placeholder="e.g., First attempt at multi-color print..."
              rows={4}
              value={formData.notes || ''}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            />
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" asChild>
            <Link to="/production-runs">Cancel</Link>
          </Button>
          <Button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Create Production Run
              </>
            )}
          </Button>
        </div>

        {/* Error Display */}
        {createMutation.isError && (
          <div className="rounded-md bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              Error creating production run: {(createMutation.error as Error).message}
            </p>
          </div>
        )}
      </form>
    </div>
  )
}
