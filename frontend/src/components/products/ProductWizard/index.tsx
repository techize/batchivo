/**
 * ProductWizard Component
 *
 * Multi-step wizard for creating products from models.
 * Steps:
 * 1. Model Selection - Search and select models to include
 * 2. Product Details - Name, SKU, description (prefilled from model)
 * 3. Category Selection - Assign to categories
 * 4. Packaging - Configure packaging options
 * 5. Review - Review and submit
 */

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Check, ChevronLeft, ChevronRight, Loader2, Package, Layers, Tags, Box, ClipboardCheck } from 'lucide-react'

import { createProduct, addProductModel, type ProductCreateRequest } from '@/lib/api/products'
import { assignProductToCategory } from '@/lib/api/categories'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

import { WizardModelSelection } from './WizardModelSelection'
import { WizardProductDetails } from './WizardProductDetails'
import { WizardCategorySelection } from './WizardCategorySelection'
import { WizardPackaging } from './WizardPackaging'
import { WizardReview } from './WizardReview'

// ==================== Types ====================

export interface SelectedModel {
  id: string
  name: string
  sku: string
  description?: string
  image_url?: string
  total_cost?: string
  quantity: number
}

export interface SelectedCategory {
  id: string
  name: string
}

export interface WizardData {
  // Step 1: Models
  selectedModels: SelectedModel[]

  // Step 2: Product Details
  sku: string
  name: string
  description: string

  // Step 3: Categories
  selectedCategories: SelectedCategory[]

  // Step 4: Packaging
  packagingCost: string
  packagingConsumableId: string | null
  packagingQuantity: number
  assemblyMinutes: number
}

export interface ProductWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// ==================== Step Configuration ====================

interface WizardStep {
  id: string
  title: string
  description: string
  icon: React.ReactNode
}

const WIZARD_STEPS: WizardStep[] = [
  {
    id: 'models',
    title: 'Select Models',
    description: 'Choose models to include',
    icon: <Layers className="h-4 w-4" />,
  },
  {
    id: 'details',
    title: 'Product Details',
    description: 'Name and description',
    icon: <Package className="h-4 w-4" />,
  },
  {
    id: 'categories',
    title: 'Categories',
    description: 'Organize your product',
    icon: <Tags className="h-4 w-4" />,
  },
  {
    id: 'packaging',
    title: 'Packaging',
    description: 'Configure packaging',
    icon: <Box className="h-4 w-4" />,
  },
  {
    id: 'review',
    title: 'Review',
    description: 'Confirm and create',
    icon: <ClipboardCheck className="h-4 w-4" />,
  },
]

// ==================== Initial State ====================

const INITIAL_WIZARD_DATA: WizardData = {
  selectedModels: [],
  sku: '',
  name: '',
  description: '',
  selectedCategories: [],
  packagingCost: '0',
  packagingConsumableId: null,
  packagingQuantity: 1,
  assemblyMinutes: 0,
}

// ==================== Component ====================

export function ProductWizard({ open, onOpenChange }: ProductWizardProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [currentStep, setCurrentStep] = useState(0)
  const [wizardData, setWizardData] = useState<WizardData>(INITIAL_WIZARD_DATA)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Mutation for creating the product
  const createProductMutation = useMutation({
    mutationFn: async (data: WizardData) => {
      // Step 1: Create the product
      const productData: ProductCreateRequest = {
        sku: data.sku,
        name: data.name,
        description: data.description || undefined,
        packaging_cost: data.packagingCost || '0',
        packaging_consumable_id: data.packagingConsumableId || undefined,
        packaging_quantity: data.packagingQuantity,
        assembly_minutes: data.assemblyMinutes,
        is_active: true,
      }

      const product = await createProduct(productData)

      // Step 2: Add models to the product
      for (const model of data.selectedModels) {
        await addProductModel(product.id, {
          model_id: model.id,
          quantity: model.quantity,
        })
      }

      // Step 3: Assign categories
      for (const category of data.selectedCategories) {
        await assignProductToCategory(category.id, product.id)
      }

      return product
    },
    onSuccess: (product) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      onOpenChange(false)
      resetWizard()
      navigate({ to: '/products/$productId', params: { productId: product.id } })
    },
  })

  // Update wizard data
  const updateWizardData = useCallback((updates: Partial<WizardData>) => {
    setWizardData((prev) => ({ ...prev, ...updates }))
  }, [])

  // Navigation
  const goToNextStep = useCallback(() => {
    if (currentStep < WIZARD_STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1)
    }
  }, [currentStep])

  const goToPreviousStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1)
    }
  }, [currentStep])

  const goToStep = useCallback((step: number) => {
    if (step >= 0 && step < WIZARD_STEPS.length) {
      setCurrentStep(step)
    }
  }, [])

  // Reset wizard
  const resetWizard = useCallback(() => {
    setCurrentStep(0)
    setWizardData(INITIAL_WIZARD_DATA)
    setIsSubmitting(false)
  }, [])

  // Handle dialog close
  const handleOpenChange = useCallback(
    (newOpen: boolean) => {
      if (!newOpen) {
        resetWizard()
      }
      onOpenChange(newOpen)
    },
    [onOpenChange, resetWizard]
  )

  // Submit the wizard
  const handleSubmit = useCallback(async () => {
    setIsSubmitting(true)
    try {
      await createProductMutation.mutateAsync(wizardData)
    } finally {
      setIsSubmitting(false)
    }
  }, [createProductMutation, wizardData])

  // Validation for each step
  const isStepValid = useCallback(
    (step: number): boolean => {
      switch (step) {
        case 0: // Models
          return wizardData.selectedModels.length > 0
        case 1: // Details
          return wizardData.sku.trim() !== '' && wizardData.name.trim() !== ''
        case 2: // Categories
          return true // Categories are optional
        case 3: // Packaging
          return true // Packaging is optional
        case 4: // Review
          return true
        default:
          return false
      }
    },
    [wizardData]
  )

  const canProceed = isStepValid(currentStep)
  const isLastStep = currentStep === WIZARD_STEPS.length - 1

  // Render current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <WizardModelSelection
            selectedModels={wizardData.selectedModels}
            onModelsChange={(models) => updateWizardData({ selectedModels: models })}
          />
        )
      case 1:
        return (
          <WizardProductDetails
            sku={wizardData.sku}
            name={wizardData.name}
            description={wizardData.description}
            selectedModels={wizardData.selectedModels}
            onDetailsChange={(details) => updateWizardData(details)}
          />
        )
      case 2:
        return (
          <WizardCategorySelection
            selectedCategories={wizardData.selectedCategories}
            onCategoriesChange={(categories) => updateWizardData({ selectedCategories: categories })}
          />
        )
      case 3:
        return (
          <WizardPackaging
            packagingCost={wizardData.packagingCost}
            packagingConsumableId={wizardData.packagingConsumableId}
            packagingQuantity={wizardData.packagingQuantity}
            assemblyMinutes={wizardData.assemblyMinutes}
            onPackagingChange={(packaging) => updateWizardData(packaging)}
          />
        )
      case 4:
        return <WizardReview wizardData={wizardData} onEditStep={goToStep} />
      default:
        return null
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Create New Product</DialogTitle>
          <DialogDescription>
            Follow the steps to create a new product from your models
          </DialogDescription>
        </DialogHeader>

        {/* Progress Steps */}
        <div className="py-4 border-b">
          <nav aria-label="Progress">
            <ol className="flex items-center justify-between">
              {WIZARD_STEPS.map((step, index) => {
                const isCompleted = index < currentStep
                const isCurrent = index === currentStep

                return (
                  <li key={step.id} className="flex-1">
                    <button
                      type="button"
                      onClick={() => index <= currentStep && goToStep(index)}
                      disabled={index > currentStep}
                      className={cn(
                        'group flex flex-col items-center gap-2 w-full',
                        index <= currentStep ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
                      )}
                    >
                      {/* Step indicator */}
                      <span
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors',
                          isCompleted
                            ? 'border-primary bg-primary text-primary-foreground'
                            : isCurrent
                              ? 'border-primary bg-background text-primary'
                              : 'border-muted bg-background text-muted-foreground'
                        )}
                      >
                        {isCompleted ? (
                          <Check className="h-5 w-5" />
                        ) : (
                          step.icon
                        )}
                      </span>

                      {/* Step label */}
                      <span className="hidden sm:block">
                        <span
                          className={cn(
                            'text-xs font-medium',
                            isCurrent ? 'text-primary' : 'text-muted-foreground'
                          )}
                        >
                          {step.title}
                        </span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </nav>
        </div>

        {/* Step Content */}
        <div className="flex-1 overflow-y-auto py-4 min-h-[300px]">
          {renderStepContent()}
        </div>

        {/* Navigation Footer */}
        <div className="flex items-center justify-between pt-4 border-t">
          <Button
            type="button"
            variant="outline"
            onClick={goToPreviousStep}
            disabled={currentStep === 0 || isSubmitting}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back
          </Button>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Step {currentStep + 1} of {WIZARD_STEPS.length}
            </span>
          </div>

          {isLastStep ? (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={!canProceed || isSubmitting}
            >
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Product
            </Button>
          ) : (
            <Button
              type="button"
              onClick={goToNextStep}
              disabled={!canProceed}
            >
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Error display */}
        {createProductMutation.isError && (
          <div className="mt-4 p-4 bg-destructive/10 border border-destructive rounded-lg">
            <p className="text-sm text-destructive">
              Failed to create product: {createProductMutation.error?.message || 'Unknown error'}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default ProductWizard
