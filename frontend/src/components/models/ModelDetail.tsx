/**
 * ModelDetail Component
 *
 * Displays full model information including BOM (materials), components, and cost breakdown.
 * Models are printed items with bill of materials.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, Edit, Loader2, Trash2, Package } from 'lucide-react'

import { getModel, deleteModel } from '@/lib/api/models'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { BOMEditor } from './BOMEditor'
import { ComponentsEditor } from './ComponentsEditor'

interface ModelDetailProps {
  modelId: string
}

function StatCard({ label, value, subValue }: { label: string; value: string; subValue?: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      {subValue && <div className="text-xs text-muted-foreground mt-1">{subValue}</div>}
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string | React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export function ModelDetail({ modelId }: ModelDetailProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: model, isLoading, error } = useQuery({
    queryKey: ['model', modelId],
    queryFn: () => getModel(modelId),
  })

  const deleteMutation = useMutation({
    mutationFn: () => deleteModel(modelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] })
      navigate({ to: '/models' })
    },
  })

  const formatCurrency = (value: string | number) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    return `£${numValue.toFixed(3)}`
  }

  if (isLoading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3">Loading model...</span>
      </div>
    )
  }

  if (error || !model) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading model</p>
          <p className="text-sm text-muted-foreground">{error ? (error as Error).message : 'Model not found'}</p>
        </div>
      </div>
    )
  }

  const costBreakdown = model.cost_breakdown
  // Use correct field names (singular) and handle null/undefined with || 0
  const totalCost = parseFloat(costBreakdown?.total_cost) || 0
  const materialsCost = parseFloat(costBreakdown?.material_cost) || 0
  const componentsCost = parseFloat(costBreakdown?.component_cost) || 0
  const laborCost = parseFloat(costBreakdown?.labor_cost) || 0

  // Calculate recommended sale price using common pricing formulas
  // Using 2.5x markup (150% profit margin) as default - common for handmade/craft items
  const recommendedPrice = totalCost * 2.5
  // Alternative: 40% profit margin formula: cost / (1 - 0.40) = cost / 0.60
  const marginBasedPrice = totalCost / 0.60

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/models">
                <ArrowLeft className="mr-1 h-4 w-4" />
                Models
              </Link>
            </Button>
            <span>/</span>
            <span className="font-mono">{model.sku}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{model.name}</h1>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant={model.is_active ? 'default' : 'secondary'}>
              {model.is_active ? 'Active' : 'Inactive'}
            </Badge>
            {model.category && (
              <Badge variant="outline">{model.category}</Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/models/$modelId/edit" params={{ modelId }}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="icon">
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Model</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete this model? This will set is_active to false.
                  This action can be reversed by editing the model.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
                  {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Cost Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Materials Cost"
          value={formatCurrency(materialsCost)}
          subValue={`${model.materials?.length || 0} materials`}
        />
        <StatCard
          label="Components Cost"
          value={formatCurrency(componentsCost)}
          subValue={`${model.components?.length || 0} components`}
        />
        <StatCard
          label="Labor Cost"
          value={formatCurrency(laborCost)}
          subValue={`${parseFloat(model.labor_hours || '0').toFixed(1)}h labor`}
        />
        <StatCard
          label="Total Cost"
          value={formatCurrency(totalCost)}
          subValue={costBreakdown ? `+${parseFloat(model.overhead_percentage || '0').toFixed(0)}% overhead` : undefined}
        />
      </div>

      {/* Pricing Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          label="Recommended Price"
          value={formatCurrency(recommendedPrice)}
          subValue="2.5× markup (150% margin)"
        />
        <StatCard
          label="Alternative Price"
          value={formatCurrency(marginBasedPrice)}
          subValue="40% profit margin"
        />
        <StatCard
          label="Profit at 2.5×"
          value={formatCurrency(recommendedPrice - totalCost)}
          subValue={`${totalCost > 0 ? ((recommendedPrice - totalCost) / totalCost * 100).toFixed(0) : 0}% profit`}
        />
      </div>

      {/* Model Details Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Model Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {model.description && (
            <div className="pb-3 mb-3 border-b">
              <span className="text-sm text-muted-foreground">Description</span>
              <p className="mt-1 whitespace-pre-wrap">{model.description}</p>
            </div>
          )}

          <DetailItem label="SKU" value={<span className="font-mono">{model.sku}</span>} />
          {model.designer && <DetailItem label="Designer" value={model.designer} />}
          {model.source && <DetailItem label="Source" value={model.source} />}
          {model.machine && <DetailItem label="Machine" value={model.machine} />}
          {model.print_time_minutes && (
            <DetailItem
              label="Print Time"
              value={`${Math.floor(model.print_time_minutes / 60)}h ${model.print_time_minutes % 60}m`}
            />
          )}
          <DetailItem label="Units in Stock" value={model.units_in_stock?.toString() || '0'} />

          <div className="pt-3 mt-3 border-t grid grid-cols-2 gap-4 text-xs text-muted-foreground">
            <div>
              <span>Created</span>
              <p className="font-medium text-foreground">{new Date(model.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <span>Last Updated</span>
              <p className="font-medium text-foreground">{new Date(model.updated_at).toLocaleDateString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bill of Materials */}
      <Card>
        <CardHeader>
          <CardTitle>Bill of Materials (Per Unit)</CardTitle>
          <CardDescription>
            Filament weights for a single unit. Purge tower and flush waste are tracked when creating production runs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Show per-plate calculation if prints_per_plate > 1 */}
          {model.prints_per_plate && model.prints_per_plate > 1 && model.materials && model.materials.length > 0 && (
            <div className="mb-4 rounded-lg bg-muted/50 p-3 text-sm">
              <div className="font-medium">Plate Calculation</div>
              <div className="text-muted-foreground mt-1">
                Per Unit:{' '}
                <span className="font-medium text-foreground">
                  {model.materials.reduce((sum, m) => sum + parseFloat(m.weight_grams || '0'), 0).toFixed(1)}g
                </span>
                {' · '}
                Per Plate (×{model.prints_per_plate}):{' '}
                <span className="font-medium text-foreground">
                  {(model.materials.reduce((sum, m) => sum + parseFloat(m.weight_grams || '0'), 0) * model.prints_per_plate).toFixed(1)}g
                </span>
                <span className="text-xs ml-1">(model only, + waste when running)</span>
              </div>
            </div>
          )}
          <BOMEditor modelId={modelId} materials={model.materials || []} />
        </CardContent>
      </Card>

      {/* Components */}
      <Card>
        <CardHeader>
          <CardTitle>Components</CardTitle>
          <CardDescription>Non-material components (magnets, inserts, screws, etc.)</CardDescription>
        </CardHeader>
        <CardContent>
          <ComponentsEditor modelId={modelId} components={model.components || []} />
        </CardContent>
      </Card>
    </div>
  )
}
