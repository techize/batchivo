/**
 * WizardReview Component
 *
 * Step 5: Review before creating the product.
 * Summary of all selections with edit buttons.
 */

import { Pencil, Layers, Package, Tags, Box } from 'lucide-react'

import { useCurrency } from '@/hooks/useCurrency'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

import type { WizardData } from './index'

interface WizardReviewProps {
  wizardData: WizardData
  onEditStep: (step: number) => void
}

export function WizardReview({ wizardData, onEditStep }: WizardReviewProps) {
  const { formatCurrency } = useCurrency()

  // Calculate costs
  const modelsCost = wizardData.selectedModels.reduce((total, model) => {
    return total + parseFloat(model.total_cost || '0') * model.quantity
  }, 0)

  const packagingCost = parseFloat(wizardData.packagingCost) || 0
  const laborCost = (wizardData.assemblyMinutes / 60) * 10
  const totalCost = modelsCost + packagingCost + laborCost

  return (
    <div className="space-y-4">
      <div className="text-center mb-6">
        <h3 className="text-lg font-semibold">Review Your Product</h3>
        <p className="text-sm text-muted-foreground">
          Please review the details before creating your product
        </p>
      </div>

      {/* Models Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Models
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEditStep(0)}
              className="h-8"
            >
              <Pencil className="h-3 w-3 mr-1" />
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {wizardData.selectedModels.length === 0 ? (
            <p className="text-sm text-muted-foreground">No models selected</p>
          ) : (
            <div className="space-y-2">
              {wizardData.selectedModels.map((model) => (
                <div key={model.id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span>{model.name}</span>
                    <Badge variant="outline" className="text-xs">
                      x{model.quantity}
                    </Badge>
                  </div>
                  <span className="font-medium">
                    {formatCurrency(parseFloat(model.total_cost || '0') * model.quantity)}
                  </span>
                </div>
              ))}
              <Separator className="my-2" />
              <div className="flex justify-between font-medium">
                <span>Models Total</span>
                <span>{formatCurrency(modelsCost)}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Product Details Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Package className="h-4 w-4" />
              Product Details
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEditStep(1)}
              className="h-8"
            >
              <Pencil className="h-3 w-3 mr-1" />
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0 space-y-2">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">SKU:</span>
              <span className="ml-2 font-mono">{wizardData.sku || '-'}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Name:</span>
              <span className="ml-2">{wizardData.name || '-'}</span>
            </div>
          </div>
          {wizardData.description && (
            <div className="text-sm">
              <span className="text-muted-foreground">Description:</span>
              <div
                className="mt-1 text-xs text-muted-foreground line-clamp-2"
                dangerouslySetInnerHTML={{ __html: wizardData.description }}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Categories Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Tags className="h-4 w-4" />
              Categories
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEditStep(2)}
              className="h-8"
            >
              <Pencil className="h-3 w-3 mr-1" />
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {wizardData.selectedCategories.length === 0 ? (
            <p className="text-sm text-muted-foreground">No categories selected</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {wizardData.selectedCategories.map((category) => (
                <Badge key={category.id} variant="secondary">
                  {category.name}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Packaging Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Box className="h-4 w-4" />
              Packaging & Assembly
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEditStep(3)}
              className="h-8"
            >
              <Pencil className="h-3 w-3 mr-1" />
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0 space-y-2">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Packaging Cost:</span>
              <span className="ml-2">{formatCurrency(packagingCost)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Assembly:</span>
              <span className="ml-2">{wizardData.assemblyMinutes} min</span>
            </div>
          </div>
          <div className="text-sm">
            <span className="text-muted-foreground">Labor Cost:</span>
            <span className="ml-2">{formatCurrency(laborCost)}</span>
          </div>
        </CardContent>
      </Card>

      {/* Total Cost Summary */}
      <Card className="bg-primary/5 border-primary/20">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-semibold">Estimated Total Cost</h4>
              <p className="text-xs text-muted-foreground">
                Models + Packaging + Labor
              </p>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold">{formatCurrency(totalCost)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground text-center">
        Click "Create Product" to finalize. You can add more details (pricing, images) after creation.
      </p>
    </div>
  )
}
