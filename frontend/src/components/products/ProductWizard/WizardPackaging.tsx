/**
 * WizardPackaging Component
 *
 * Step 4: Packaging configuration for the product wizard.
 * Set packaging consumable, cost, and assembly time.
 */

import { useQuery } from '@tanstack/react-query'
import { Package, Clock, X } from 'lucide-react'

import { consumablesApi } from '@/lib/api/consumables'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface WizardPackagingProps {
  packagingCost: string
  packagingConsumableId: string | null
  packagingQuantity: number
  assemblyMinutes: number
  onPackagingChange: (packaging: {
    packagingCost?: string
    packagingConsumableId?: string | null
    packagingQuantity?: number
    assemblyMinutes?: number
  }) => void
}

export function WizardPackaging({
  packagingCost,
  packagingConsumableId,
  packagingQuantity,
  assemblyMinutes,
  onPackagingChange,
}: WizardPackagingProps) {
  // Fetch packaging consumables
  const { data: packagingConsumables } = useQuery({
    queryKey: ['consumables', 'packaging'],
    queryFn: () => consumablesApi.list({ category: 'packaging', is_active: true, page_size: 100 }),
  })

  const consumables = packagingConsumables?.consumables || []

  // Calculate estimated packaging cost
  const selectedConsumable = consumables.find((c) => c.id === packagingConsumableId)
  const estimatedCost = selectedConsumable
    ? (selectedConsumable.current_cost_per_unit || 0) * packagingQuantity
    : parseFloat(packagingCost) || 0

  // Calculate labor cost (£10/hr)
  const laborCost = (assemblyMinutes / 60) * 10

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Packaging
          </CardTitle>
          <CardDescription>
            Configure packaging materials and costs
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Packaging Consumable */}
          <div className="space-y-2">
            <Label>Packaging Consumable</Label>
            <div className="flex gap-2">
              <Select
                value={packagingConsumableId || ''}
                onValueChange={(value) =>
                  onPackagingChange({ packagingConsumableId: value || null })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select packaging..." />
                </SelectTrigger>
                <SelectContent>
                  {consumables.map((consumable) => (
                    <SelectItem key={consumable.id} value={consumable.id}>
                      {consumable.name}
                      {consumable.current_cost_per_unit && (
                        <span className="ml-2 text-muted-foreground">
                          (£{consumable.current_cost_per_unit.toFixed(2)}/ea)
                        </span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {packagingConsumableId && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => onPackagingChange({ packagingConsumableId: null })}
                  title="Clear selection"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Select a packaging consumable (e.g., box, bag)
            </p>
          </div>

          {/* Quantity or Manual Cost */}
          {packagingConsumableId ? (
            <div className="space-y-2">
              <Label htmlFor="packagingQuantity">Quantity per Product</Label>
              <Input
                id="packagingQuantity"
                type="number"
                min="1"
                value={packagingQuantity}
                onChange={(e) =>
                  onPackagingChange({ packagingQuantity: parseInt(e.target.value) || 1 })
                }
              />
              <p className="text-sm text-muted-foreground">
                How many of this consumable per product
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="packagingCost">Manual Packaging Cost (£)</Label>
              <Input
                id="packagingCost"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={packagingCost}
                onChange={(e) => onPackagingChange({ packagingCost: e.target.value })}
              />
              <p className="text-sm text-muted-foreground">
                Enter cost if no consumable selected
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Assembly
          </CardTitle>
          <CardDescription>
            Time needed to assemble and package this product
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="assemblyMinutes">Assembly Time (minutes)</Label>
            <Input
              id="assemblyMinutes"
              type="number"
              min="0"
              placeholder="0"
              value={assemblyMinutes || ''}
              onChange={(e) =>
                onPackagingChange({ assemblyMinutes: parseInt(e.target.value) || 0 })
              }
            />
            <p className="text-sm text-muted-foreground">
              Time to assemble/package (calculated at £10/hr)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Cost Summary */}
      <Card className="bg-muted/50">
        <CardContent className="py-4">
          <h4 className="font-medium mb-3">Cost Summary</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Packaging Cost:</span>
              <span className="font-medium">£{estimatedCost.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                Labor Cost ({assemblyMinutes} min @ £10/hr):
              </span>
              <span className="font-medium">£{laborCost.toFixed(2)}</span>
            </div>
            <div className="flex justify-between pt-2 border-t">
              <span className="font-medium">Total (excl. models):</span>
              <span className="font-bold">£{(estimatedCost + laborCost).toFixed(2)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Help text */}
      <p className="text-sm text-muted-foreground text-center">
        Packaging configuration is optional. You can update these settings later.
      </p>
    </div>
  )
}
