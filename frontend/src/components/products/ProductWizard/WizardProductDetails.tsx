/**
 * WizardProductDetails Component
 *
 * Step 2: Product details for the product wizard.
 * Name, SKU, and description - prefilled from selected models.
 */

import { useEffect, useState } from 'react'
import { RefreshCw, Wand2 } from 'lucide-react'

import { useNextSKU } from '@/hooks/useSKU'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { RichTextEditor } from '@/components/ui/rich-text-editor'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import type { SelectedModel } from './index'

interface WizardProductDetailsProps {
  sku: string
  name: string
  description: string
  selectedModels: SelectedModel[]
  onDetailsChange: (details: { sku?: string; name?: string; description?: string }) => void
}

export function WizardProductDetails({
  sku,
  name,
  description,
  selectedModels,
  onDetailsChange,
}: WizardProductDetailsProps) {
  const [hasAutoFilled, setHasAutoFilled] = useState(false)

  // Auto-generate SKU
  const { nextSKU, isLoading: isLoadingSKU, refetch: refetchSKU } = useNextSKU('PROD', true)

  // Auto-fill SKU when it's fetched
  useEffect(() => {
    if (nextSKU && !sku) {
      onDetailsChange({ sku: nextSKU })
    }
  }, [nextSKU, sku, onDetailsChange])

  // Auto-fill name and description from first model (if not already filled)
  useEffect(() => {
    if (selectedModels.length > 0 && !hasAutoFilled && !name && !description) {
      const firstModel = selectedModels[0]

      // Generate name from model(s)
      let autoName = ''
      if (selectedModels.length === 1) {
        autoName = firstModel.name
      } else {
        // For multiple models, create a combined name
        autoName = selectedModels.map((m) => m.name).join(' + ')
      }

      // Use first model's description
      const autoDescription = firstModel.description || ''

      onDetailsChange({ name: autoName, description: autoDescription })
      setHasAutoFilled(true)
    }
  }, [selectedModels, hasAutoFilled, name, description, onDetailsChange])

  // Generate name from models
  const generateNameFromModels = () => {
    if (selectedModels.length === 0) return

    let autoName = ''
    if (selectedModels.length === 1) {
      autoName = selectedModels[0].name
    } else {
      autoName = selectedModels.map((m) => m.name).join(' + ')
    }
    onDetailsChange({ name: autoName })
  }

  // Generate description from models
  const generateDescriptionFromModels = () => {
    if (selectedModels.length === 0) return

    const descriptions = selectedModels
      .filter((m) => m.description)
      .map((m) => m.description)

    if (descriptions.length > 0) {
      onDetailsChange({ description: descriptions.join('\n\n') })
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Product Identification</CardTitle>
          <CardDescription>
            Set the SKU and name for this product
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* SKU */}
          <div className="space-y-2">
            <Label htmlFor="sku">SKU *</Label>
            <div className="flex gap-2">
              <Input
                id="sku"
                placeholder={isLoadingSKU ? 'Loading...' : 'PROD-001'}
                value={sku}
                onChange={(e) => onDetailsChange({ sku: e.target.value })}
                disabled={isLoadingSKU}
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => refetchSKU()}
                disabled={isLoadingSKU}
                title="Generate new SKU"
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingSKU ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Unique identifier for this product
            </p>
          </div>

          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Product Name *</Label>
            <div className="flex gap-2">
              <Input
                id="name"
                placeholder="Product name"
                value={name}
                onChange={(e) => onDetailsChange({ name: e.target.value })}
              />
              {selectedModels.length > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={generateNameFromModels}
                  title="Generate from models"
                >
                  <Wand2 className="h-4 w-4" />
                </Button>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              The display name for this product
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Description</CardTitle>
          <CardDescription>
            Add a description for this product (optional)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="description">Product Description</Label>
              {selectedModels.length > 0 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={generateDescriptionFromModels}
                  className="text-xs"
                >
                  <Wand2 className="h-3 w-3 mr-1" />
                  Generate from models
                </Button>
              )}
            </div>
            <RichTextEditor
              value={description}
              onChange={(value) => onDetailsChange({ description: value })}
              placeholder="Product description..."
            />
            <p className="text-sm text-muted-foreground">
              Supports formatting: bold, italic, lists, and links
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Model summary */}
      {selectedModels.length > 0 && (
        <Card className="bg-muted/50">
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">
              This product will include {selectedModels.length} model{selectedModels.length !== 1 ? 's' : ''}:{' '}
              <span className="font-medium text-foreground">
                {selectedModels.map((m) => `${m.name} (x${m.quantity})`).join(', ')}
              </span>
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
