/**
 * ProductionRunDetail Component
 *
 * Displays detailed information about a production run including
 * items, materials, and completion status.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, Loader2, Package, Droplets, CheckCircle, Ban, Pencil, Calculator } from 'lucide-react'

import {
  getProductionRun,
  formatStatus,
  formatDuration,
  getStatusColor,
} from '@/lib/api/production-runs'
import { formatCurrency } from '@/lib/api/products'
import { CancelRunDialog } from './CancelRunDialog'
import { CompleteRunDialog } from './CompleteRunDialog'
import { EditRunDialog } from './EditRunDialog'
import { PlatesSection } from './PlatesSection'
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
import { Separator } from '@/components/ui/separator'

interface ProductionRunDetailProps {
  runId: string
}

export function ProductionRunDetail({ runId }: ProductionRunDetailProps) {
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)

  const { data: run, isLoading, error } = useQuery({
    queryKey: ['production-run', runId],
    queryFn: () => getProductionRun(runId),
  })

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error || !run) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading production run</p>
          <p className="text-sm text-muted-foreground">
            {error ? (error as Error).message : 'Production run not found'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/production-runs">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{run.run_number}</h1>
            <p className="text-muted-foreground">
              Started {new Date(run.started_at).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant={getStatusColor(run.status) === 'green' ? 'default' : 'secondary'}>
            {formatStatus(run.status)}
          </Badge>

          {/* Edit button - available for all statuses */}
          <Button
            variant="outline"
            onClick={() => setEditDialogOpen(true)}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Edit Run
          </Button>

          {/* In-progress actions */}
          {run.status === 'in_progress' && (
            <>
              <Button
                variant="outline"
                onClick={() => setCancelDialogOpen(true)}
              >
                <Ban className="mr-2 h-4 w-4" />
                Cancel / Fail
              </Button>
              <Button onClick={() => setCompleteDialogOpen(true)}>
                <CheckCircle className="mr-2 h-4 w-4" />
                Complete Run
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Run Details */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Printer Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-sm text-muted-foreground">Printer</p>
              <p className="font-medium">{run.printer_name || '—'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Slicer</p>
              <p className="font-medium">{run.slicer_software || '—'}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-sm text-muted-foreground">Bed Temp</p>
                <p className="font-medium">{run.bed_temperature ? `${run.bed_temperature}°C` : '—'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Nozzle Temp</p>
                <p className="font-medium">{run.nozzle_temperature ? `${run.nozzle_temperature}°C` : '—'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Timing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-sm text-muted-foreground">Estimated Time</p>
              <p className="font-medium">
                {run.estimated_print_time_hours ? formatDuration(run.estimated_print_time_hours) : '—'}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Actual Duration</p>
              <p className="font-medium">{run.duration_hours ? formatDuration(run.duration_hours) : '—'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Time Variance</p>
              <p className={`font-medium ${run.time_variance_percentage && Math.abs(Number(run.time_variance_percentage)) > 10 ? 'text-destructive' : ''}`}>
                {run.time_variance_percentage != null
                  ? `${Number(run.time_variance_percentage) > 0 ? '+' : ''}${Number(run.time_variance_percentage).toFixed(1)}%`
                  : '—'}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Items Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-sm text-muted-foreground">Total Planned</p>
              <p className="font-medium">{run.total_items_planned}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Successful</p>
              <p className="font-medium text-green-600">{run.total_items_successful}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Success Rate</p>
              <p className="font-medium">
                {run.overall_success_rate != null
                  ? `${Number(run.overall_success_rate).toFixed(1)}%`
                  : '—'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost Analysis Card - only shown when cost data is available */}
      {run.cost_per_gram_actual != null && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Calculator className="h-5 w-5 text-primary" />
              <CardTitle>Cost Analysis</CardTitle>
            </div>
            <CardDescription>
              Actual production costs including waste, purge, and failures
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Cost Per Gram</p>
                <p className="text-2xl font-bold text-primary">
                  {formatCurrency(Number(run.cost_per_gram_actual))}
                </p>
                <p className="text-xs text-muted-foreground">
                  Total material cost ÷ successful weight
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Successful Weight</p>
                <p className="text-2xl font-bold">
                  {Number(run.successful_weight_grams).toFixed(1)}g
                </p>
                <p className="text-xs text-muted-foreground">
                  Theoretical weight of successful items
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Waste Factor</p>
                <p className="text-2xl font-bold">
                  {run.actual_total_weight_grams && run.successful_weight_grams
                    ? `${((Number(run.actual_total_weight_grams) / Number(run.successful_weight_grams) - 1) * 100).toFixed(1)}%`
                    : '—'}
                </p>
                <p className="text-xs text-muted-foreground">
                  Extra material used (purge, tower, failures)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Items Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            <CardTitle>Print Items</CardTitle>
          </div>
          <CardDescription>Products being printed in this run</CardDescription>
        </CardHeader>
        <CardContent>
          {run.items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No items added to this run yet
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Bed Position</TableHead>
                  <TableHead className="text-right">Planned Qty</TableHead>
                  <TableHead className="text-right">Successful</TableHead>
                  <TableHead className="text-right">Failed</TableHead>
                  <TableHead className="text-right">Success Rate</TableHead>
                  <TableHead className="text-right">Unit Weight</TableHead>
                  <TableHead className="text-right">Cost/Unit</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {item.model ? (
                        <div>
                          <div className="font-medium">{item.model.name}</div>
                          <div className="text-xs text-muted-foreground">{item.model.sku}</div>
                        </div>
                      ) : (
                        <span className="font-mono text-xs text-muted-foreground">{item.model_id.slice(0, 8)}...</span>
                      )}
                    </TableCell>
                    <TableCell>{item.bed_position || '—'}</TableCell>
                    <TableCell className="text-right">{item.quantity}</TableCell>
                    <TableCell className="text-right text-green-600">{item.successful_quantity}</TableCell>
                    <TableCell className="text-right text-destructive">{item.failed_quantity}</TableCell>
                    <TableCell className="text-right">
                      {item.success_rate != null
                        ? `${Number(item.success_rate).toFixed(1)}%`
                        : '—'}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {item.model_weight_grams != null
                        ? `${Number(item.model_weight_grams).toFixed(1)}g`
                        : '—'}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {item.actual_cost_per_unit != null
                        ? formatCurrency(Number(item.actual_cost_per_unit))
                        : '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Plates Section */}
      <PlatesSection runId={runId} runStatus={run.status} />

      {/* Materials Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Droplets className="h-5 w-5" />
            <CardTitle>Filament Materials</CardTitle>
          </div>
          <CardDescription>Spool usage and weighing data</CardDescription>
        </CardHeader>
        <CardContent>
          {run.materials.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No materials added to this run yet
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Spool</TableHead>
                    <TableHead className="text-right">Est. Model (g)</TableHead>
                    <TableHead className="text-right">Est. Waste (g)</TableHead>
                    <TableHead className="text-right">Est. Total (g)</TableHead>
                    <TableHead className="text-right">Est. Cost</TableHead>
                    <TableHead className="text-right">Actual (g)</TableHead>
                    <TableHead className="text-right">Variance</TableHead>
                    <TableHead className="text-right">Actual Cost</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {run.materials.map((material) => {
                    const estWaste = Number(material.estimated_flushed_grams ?? 0) + Number(material.estimated_tower_grams ?? 0)
                    const actualWeight = Number(material.actual_total_weight ?? 0)
                    const hasActualData = actualWeight > 0
                    return (
                      <TableRow key={material.id}>
                        <TableCell>
                          {material.spool ? (
                            <div className="flex items-center gap-2">
                              {material.spool.color_hex && (
                                <div
                                  className="w-4 h-4 rounded-full border border-border"
                                  style={{ backgroundColor: `#${material.spool.color_hex}` }}
                                />
                              )}
                              <div>
                                <div className="font-medium">
                                  {material.spool.color}
                                  {material.spool.finish && ` (${material.spool.finish})`}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {material.spool.material_type?.code || 'Unknown'} · {material.spool.brand} · {material.spool.spool_id}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <span className="font-mono text-xs text-muted-foreground">{material.spool_id.slice(0, 8)}...</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {material.estimated_model_weight_grams != null ? Number(material.estimated_model_weight_grams).toFixed(1) : '—'}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {estWaste > 0 ? estWaste.toFixed(1) : '—'}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {material.estimated_total_weight != null ? Number(material.estimated_total_weight).toFixed(1) : '—'}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {formatCurrency(Number(material.estimated_cost ?? 0))}
                        </TableCell>
                        <TableCell className="text-right">
                          {hasActualData ? actualWeight.toFixed(1) : '—'}
                        </TableCell>
                        <TableCell className="text-right">
                          {hasActualData ? (
                            <span
                              className={
                                Math.abs(Number(material.variance_percentage ?? 0)) > 10
                                  ? 'text-destructive font-medium'
                                  : 'text-muted-foreground'
                              }
                            >
                              {Number(material.variance_percentage ?? 0) > 0 ? '+' : ''}
                              {Number(material.variance_percentage ?? 0).toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {hasActualData ? formatCurrency(Number(material.total_cost ?? 0)) : '—'}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>

              <Separator />

              {/* Cost Summary */}
              <div className="flex justify-end">
                <div className="space-y-2 min-w-[300px]">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Estimated Total Cost:</span>
                    <span className="font-medium">{formatCurrency(Number(run.total_estimated_cost ?? 0))}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Actual Material Cost:</span>
                    <span className="font-medium">{formatCurrency(Number(run.total_material_cost ?? 0))}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between">
                    <span className="font-semibold">Cost Variance:</span>
                    <span
                      className={`font-semibold ${
                        Number(run.total_material_cost ?? 0) > Number(run.total_estimated_cost ?? 0)
                          ? 'text-destructive'
                          : 'text-green-600'
                      }`}
                    >
                      {formatCurrency(Number(run.total_material_cost ?? 0) - Number(run.total_estimated_cost ?? 0))}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Notes */}
      {run.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap">{run.notes}</p>
          </CardContent>
        </Card>
      )}

      {/* Waste Info for Failed Runs */}
      {run.status === 'failed' && run.waste_reason && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Failure Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-sm text-muted-foreground">Failure Reason</p>
              <p className="font-medium capitalize">{run.waste_reason.replace(/_/g, ' ')}</p>
            </div>
            {run.waste_filament_grams != null && (
              <div>
                <p className="text-sm text-muted-foreground">Wasted Filament</p>
                <p className="font-medium">{Number(run.waste_filament_grams).toFixed(1)}g</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Cancel/Fail Dialog */}
      <CancelRunDialog
        run={run}
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
      />

      {/* Complete Run Dialog */}
      <CompleteRunDialog
        run={run}
        open={completeDialogOpen}
        onOpenChange={setCompleteDialogOpen}
      />

      {/* Edit Run Dialog */}
      <EditRunDialog
        run={run}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
      />
    </div>
  )
}
