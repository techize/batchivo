/**
 * WizardModelSelection Component
 *
 * Step 1: Model selection for the product wizard.
 * Allows searching and selecting models with quantity adjustment.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Plus, Minus, X, Loader2, Layers } from 'lucide-react'

import { listModels, type Model } from '@/lib/api/models'
import { formatCurrency } from '@/lib/api/products'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

import type { SelectedModel } from './index'

interface WizardModelSelectionProps {
  selectedModels: SelectedModel[]
  onModelsChange: (models: SelectedModel[]) => void
}

export function WizardModelSelection({ selectedModels, onModelsChange }: WizardModelSelectionProps) {
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch models
  const { data: modelsData, isLoading } = useQuery({
    queryKey: ['models', { limit: 100, search: searchQuery || undefined }],
    queryFn: () => listModels({ limit: 100, search: searchQuery || undefined }),
  })

  const models = modelsData?.models || []

  // Check if a model is selected
  const isSelected = (modelId: string) => selectedModels.some((m) => m.id === modelId)

  // Get selected model
  const getSelectedModel = (modelId: string) => selectedModels.find((m) => m.id === modelId)

  // Add model to selection
  const addModel = (model: Model) => {
    if (isSelected(model.id)) return

    const newModel: SelectedModel = {
      id: model.id,
      name: model.name,
      sku: model.sku,
      description: model.description,
      image_url: model.image_url,
      total_cost: model.total_cost,
      quantity: 1,
    }
    onModelsChange([...selectedModels, newModel])
  }

  // Remove model from selection
  const removeModel = (modelId: string) => {
    onModelsChange(selectedModels.filter((m) => m.id !== modelId))
  }

  // Update model quantity
  const updateQuantity = (modelId: string, delta: number) => {
    onModelsChange(
      selectedModels.map((m) => {
        if (m.id === modelId) {
          const newQuantity = Math.max(1, m.quantity + delta)
          return { ...m, quantity: newQuantity }
        }
        return m
      })
    )
  }

  return (
    <div className="space-y-4">
      {/* Selected Models Summary */}
      {selectedModels.length > 0 && (
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="py-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Selected Models ({selectedModels.length})</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onModelsChange([])}
                className="text-muted-foreground hover:text-destructive"
              >
                Clear all
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedModels.map((model) => (
                <Badge
                  key={model.id}
                  variant="secondary"
                  className="flex items-center gap-2 py-1.5 px-3"
                >
                  <span>{model.name}</span>
                  <span className="text-muted-foreground">x{model.quantity}</span>
                  <div className="flex items-center gap-1 ml-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-4 w-4 p-0"
                      onClick={() => updateQuantity(model.id, -1)}
                    >
                      <Minus className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-4 w-4 p-0"
                      onClick={() => updateQuantity(model.id, 1)}
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-4 w-4 p-0 text-destructive hover:text-destructive"
                      onClick={() => removeModel(model.id)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search models by name or SKU..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Models Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : models.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No models found</p>
          {searchQuery && (
            <p className="text-sm mt-1">Try a different search term</p>
          )}
        </div>
      ) : (
        <ScrollArea className="h-[350px]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pr-4">
            {models.map((model) => {
              const selected = isSelected(model.id)
              const selectedModel = getSelectedModel(model.id)

              return (
                <Card
                  key={model.id}
                  className={cn(
                    'cursor-pointer transition-all hover:shadow-md',
                    selected && 'ring-2 ring-primary bg-primary/5'
                  )}
                  onClick={() => !selected && addModel(model)}
                >
                  <CardContent className="p-3">
                    <div className="flex gap-3">
                      {/* Thumbnail */}
                      <div className="flex-shrink-0 w-16 h-16 rounded-md bg-muted overflow-hidden">
                        {model.image_url ? (
                          <img
                            src={model.image_url}
                            alt={model.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Layers className="h-6 w-6 text-muted-foreground" />
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <h4 className="font-medium text-sm truncate">{model.name}</h4>
                            <p className="text-xs text-muted-foreground font-mono">{model.sku}</p>
                          </div>
                          {selected && (
                            <Badge variant="default" className="flex-shrink-0">
                              x{selectedModel?.quantity}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-sm font-semibold">
                            {formatCurrency(model.total_cost || '0')}
                          </span>
                          {selected ? (
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-6 w-6 p-0"
                                onClick={() => updateQuantity(model.id, -1)}
                              >
                                <Minus className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-6 w-6 p-0"
                                onClick={() => updateQuantity(model.id, 1)}
                              >
                                <Plus className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-destructive"
                                onClick={() => removeModel(model.id)}
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            </div>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6"
                              onClick={(e) => {
                                e.stopPropagation()
                                addModel(model)
                              }}
                            >
                              <Plus className="h-3 w-3 mr-1" />
                              Add
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </ScrollArea>
      )}

      {/* Help text */}
      <p className="text-sm text-muted-foreground text-center">
        Select one or more models to include in this product. Adjust quantities as needed.
      </p>
    </div>
  )
}
