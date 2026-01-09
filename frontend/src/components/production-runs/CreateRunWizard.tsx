/**
 * CreateRunWizard Component
 *
 * Multi-step wizard for creating production runs.
 * Steps:
 * 1. Basic Info - Printer, slicer, temperatures, estimates
 * 2. Items - Product selection with quantities
 * 3. Materials - Spool selection with weight estimates
 * 4. Review - Summary and submit
 */

import { useState, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, Link } from '@tanstack/react-router'
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Plus,
  Trash2,
  Check,
  Package,
  Layers,
  Printer,
  ClipboardList,
  Info,
  HelpCircle,
} from 'lucide-react'

import { createProductionRun } from '@/lib/api/production-runs'
import {
  listModels,
  getModelProductionDefaults,
  type Model,
  type ModelProductionDefaults,
} from '@/lib/api/models'
import { spoolsApi } from '@/lib/api/spools'
import type {
  ProductionRunCreate,
  ProductionRunItemCreate,
  ProductionRunMaterialCreate,
} from '@/types/production-run'
import type { SpoolResponse } from '@/types/spool'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { SearchableSpoolSelect } from '@/components/inventory/SearchableSpoolSelect'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'


// Wizard step type
type WizardStep = 1 | 2 | 3 | 4

// Step labels
const STEP_LABELS: Record<WizardStep, { title: string; description: string; icon: React.ElementType }> = {
  1: { title: 'Basic Info', description: 'Printer and estimates', icon: Printer },
  2: { title: 'Models', description: 'Models to print', icon: Package },
  3: { title: 'Materials', description: 'Spools to use', icon: Layers },
  4: { title: 'Review', description: 'Confirm and create', icon: ClipboardList },
}

// Form data for the wizard
interface WizardFormData {
  // Step 1: Basic Info
  printer_name: string
  slicer_software: string
  bed_temperature: number | undefined
  nozzle_temperature: number | undefined
  estimated_print_time_hours: number | undefined
  // Split filament tracking at run level
  estimated_model_weight_grams: number | undefined
  estimated_flushed_grams: number | undefined
  estimated_tower_grams: number | undefined
  notes: string

  // Step 2: Models
  items: Array<{
    model_id: string
    model_name: string
    model_sku: string
    quantity: number
    bed_position: string
  }>

  // Step 3: Materials - split filament tracking per spool
  materials: Array<{
    spool_id: string
    spool_name: string // Display: brand + color
    material_type: string
    estimated_model_weight_grams: number
    estimated_flushed_grams: number
    estimated_tower_grams: number
    cost_per_gram: number
    current_weight: number
  }>
}

const initialFormData: WizardFormData = {
  printer_name: '',
  slicer_software: '',
  bed_temperature: undefined,
  nozzle_temperature: undefined,
  estimated_print_time_hours: undefined,
  estimated_model_weight_grams: undefined,
  estimated_flushed_grams: undefined,
  estimated_tower_grams: undefined,
  notes: '',
  items: [],
  materials: [],
}

export function CreateRunWizard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [currentStep, setCurrentStep] = useState<WizardStep>(1)
  const [formData, setFormData] = useState<WizardFormData>(initialFormData)
  const [modelDefaults, setModelDefaults] = useState<Record<string, ModelProductionDefaults>>({})

  // Fetch models for step 2
  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['models', 'active'],
    queryFn: () => listModels({ is_active: true, limit: 100 }),
  })

  // Fetch spools for step 3
  const { data: spoolsData, isLoading: spoolsLoading } = useQuery({
    queryKey: ['spools', 'active'],
    queryFn: () => spoolsApi.list({ is_active: true, page_size: 100 }),
  })

  const models = modelsData?.models ?? []
  const spools = spoolsData?.spools ?? []

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      const runData: ProductionRunCreate = {
        started_at: new Date().toISOString(),
        status: 'in_progress',
        printer_name: formData.printer_name || undefined,
        slicer_software: formData.slicer_software || undefined,
        bed_temperature: formData.bed_temperature,
        nozzle_temperature: formData.nozzle_temperature,
        estimated_print_time_hours: formData.estimated_print_time_hours,
        // Split filament tracking at run level
        estimated_model_weight_grams: formData.estimated_model_weight_grams,
        estimated_flushed_grams: formData.estimated_flushed_grams,
        estimated_tower_grams: formData.estimated_tower_grams,
        notes: formData.notes || undefined,
      }

      const items: ProductionRunItemCreate[] = formData.items.map((item) => ({
        model_id: item.model_id,
        quantity: item.quantity,
        bed_position: item.bed_position || undefined,
      }))

      const materials: ProductionRunMaterialCreate[] = formData.materials.map((mat) => ({
        spool_id: mat.spool_id,
        // Split filament tracking per spool
        estimated_model_weight_grams: mat.estimated_model_weight_grams,
        estimated_flushed_grams: mat.estimated_flushed_grams,
        estimated_tower_grams: mat.estimated_tower_grams,
        cost_per_gram: mat.cost_per_gram,
      }))

      return createProductionRun(runData, items, materials)
    },
    onSuccess: (newRun) => {
      queryClient.invalidateQueries({ queryKey: ['production-runs'] })
      navigate({ to: '/production-runs/$runId', params: { runId: newRun.id } })
    },
  })

  // Calculate totals for review step
  const totals = useMemo(() => {
    const totalItems = formData.items.reduce((sum, item) => sum + item.quantity, 0)
    const totalMaterialWeight = formData.materials.reduce(
      (sum, mat) => sum + mat.estimated_model_weight_grams + mat.estimated_flushed_grams + mat.estimated_tower_grams,
      0
    )
    const totalMaterialCost = formData.materials.reduce(
      (sum, mat) =>
        sum + (mat.estimated_model_weight_grams + mat.estimated_flushed_grams + mat.estimated_tower_grams) * mat.cost_per_gram,
      0
    )
    return { totalItems, totalMaterialWeight, totalMaterialCost }
  }, [formData.items, formData.materials])

  // Calculate suggested materials from Model BOM (auto-population feature)
  const suggestedMaterials = useMemo(() => {
    const suggestions: Record<string, {
      spool_id: string
      spool_name: string
      material_type: string
      color: string
      color_hex?: string
      total_weight_grams: number
      cost_per_gram: number
      current_weight: number
      is_active: boolean
      models: Array<{ model_name: string; model_sku: string; quantity: number; weight_grams: number }>
    }> = {}

    // For each selected item (model + quantity)
    formData.items.forEach((item) => {
      const defaults = modelDefaults[item.model_id]
      if (!defaults || !defaults.bom_materials.length) return

      // For each material in the model's BOM
      defaults.bom_materials.forEach((bomMaterial) => {
        const spoolId = bomMaterial.spool_id
        const weightGrams = parseFloat(bomMaterial.weight_grams) * item.quantity

        if (!suggestions[spoolId]) {
          // First time seeing this spool - create entry
          suggestions[spoolId] = {
            spool_id: bomMaterial.spool_id,
            spool_name: bomMaterial.spool_name,
            material_type: bomMaterial.material_type_code,
            color: bomMaterial.color,
            color_hex: bomMaterial.color_hex,
            total_weight_grams: weightGrams,
            cost_per_gram: parseFloat(bomMaterial.cost_per_gram),
            current_weight: parseFloat(bomMaterial.current_weight),
            is_active: bomMaterial.is_active,
            models: [{
              model_name: item.model_name,
              model_sku: item.model_sku,
              quantity: item.quantity,
              weight_grams: weightGrams,
            }],
          }
        } else {
          // Spool already in suggestions - add weight and model info
          suggestions[spoolId].total_weight_grams += weightGrams
          suggestions[spoolId].models.push({
            model_name: item.model_name,
            model_sku: item.model_sku,
            quantity: item.quantity,
            weight_grams: weightGrams,
          })
        }
      })
    })

    return Object.values(suggestions)
  }, [formData.items, modelDefaults])

  // Step validation
  const canProceed = (step: WizardStep): boolean => {
    switch (step) {
      case 1:
        // Basic info is optional, can always proceed
        return true
      case 2:
        // Must have at least one item OR allow empty for quick runs
        return true
      case 3:
        // Materials are optional
        return true
      case 4:
        // Review step - check overall validity
        return true
      default:
        return false
    }
  }

  const handleNext = () => {
    if (currentStep < 4 && canProceed(currentStep)) {
      setCurrentStep((currentStep + 1) as WizardStep)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as WizardStep)
    }
  }

  const handleSubmit = () => {
    createMutation.mutate()
  }

  // Item management
  const addItem = async (model: Model) => {
    if (formData.items.some((item) => item.model_id === model.id)) return

    // Fetch production defaults for this model (BOM materials with inventory)
    try {
      const defaults = await getModelProductionDefaults(model.id)
      setModelDefaults(prev => ({
        ...prev,
        [model.id]: defaults
      }))
    } catch (error) {
      console.error('Failed to fetch production defaults:', error)
      // Continue even if defaults fetch fails
    }

    setFormData({
      ...formData,
      items: [
        ...formData.items,
        {
          model_id: model.id,
          model_name: model.name,
          model_sku: model.sku,
          quantity: 1, // Will be enhanced in Step 3 to show suggestion from prints_per_plate
          bed_position: '',
        },
      ],
    })
  }

  const updateItemQuantity = (modelId: string, quantity: number) => {
    setFormData({
      ...formData,
      items: formData.items.map((item) =>
        item.model_id === modelId ? { ...item, quantity: Math.max(1, quantity) } : item
      ),
    })
  }

  const updateItemPosition = (modelId: string, position: string) => {
    setFormData({
      ...formData,
      items: formData.items.map((item) =>
        item.model_id === modelId ? { ...item, bed_position: position } : item
      ),
    })
  }

  const removeItem = (modelId: string) => {
    setFormData({
      ...formData,
      items: formData.items.filter((item) => item.model_id !== modelId),
    })
  }

  // Material management
  const addMaterial = (spool: SpoolResponse) => {
    if (formData.materials.some((mat) => mat.spool_id === spool.id)) return

    // Calculate cost per gram from purchase price if available
    const costPerGram =
      spool.purchase_price && spool.initial_weight
        ? spool.purchase_price / spool.initial_weight
        : 0.02 // Default fallback

    setFormData({
      ...formData,
      materials: [
        ...formData.materials,
        {
          spool_id: spool.id,
          spool_name: `${spool.brand} ${spool.color}`,
          material_type: spool.material_type_name,
          // Split filament tracking per spool
          estimated_model_weight_grams: 0,
          estimated_flushed_grams: 0,
          estimated_tower_grams: 0,
          cost_per_gram: costPerGram,
          current_weight: spool.current_weight,
        },
      ],
    })
  }

  const updateMaterialWeight = (
    spoolId: string,
    field: 'estimated_model_weight_grams' | 'estimated_flushed_grams' | 'estimated_tower_grams',
    value: number
  ) => {
    setFormData({
      ...formData,
      materials: formData.materials.map((mat) =>
        mat.spool_id === spoolId ? { ...mat, [field]: Math.max(0, value) } : mat
      ),
    })
  }

  const removeMaterial = (spoolId: string) => {
    setFormData({
      ...formData,
      materials: formData.materials.filter((mat) => mat.spool_id !== spoolId),
    })
  }

  // Apply suggested materials from Model BOM
  const applySuggestedMaterials = () => {
    const newMaterials = suggestedMaterials
      .filter(suggestion => !formData.materials.some(mat => mat.spool_id === suggestion.spool_id))
      .map(suggestion => ({
        spool_id: suggestion.spool_id,
        spool_name: suggestion.spool_name,
        material_type: suggestion.material_type,
        estimated_model_weight_grams: suggestion.total_weight_grams,
        estimated_flushed_grams: 0,
        estimated_tower_grams: 0,
        cost_per_gram: suggestion.cost_per_gram,
        current_weight: suggestion.current_weight,
      }))

    setFormData({
      ...formData,
      materials: [...formData.materials, ...newMaterials],
    })
  }

  // Progress calculation
  const progressPercentage = ((currentStep - 1) / 3) * 100

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
          <p className="text-muted-foreground">
            Step {currentStep} of 4: {STEP_LABELS[currentStep].title}
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <Progress value={progressPercentage} className="h-2" />
        <div className="flex justify-between">
          {([1, 2, 3, 4] as WizardStep[]).map((step) => {
            const StepIcon = STEP_LABELS[step].icon
            const isActive = step === currentStep
            const isCompleted = step < currentStep
            return (
              <div
                key={step}
                className={`flex items-center gap-2 text-sm ${
                  isActive
                    ? 'text-primary font-medium'
                    : isCompleted
                    ? 'text-muted-foreground'
                    : 'text-muted-foreground/50'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : isCompleted
                      ? 'bg-primary/20 text-primary'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {isCompleted ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <StepIcon className="w-4 h-4" />
                  )}
                </div>
                <span className="hidden sm:inline">{STEP_LABELS[step].title}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="min-h-[400px]">
        {currentStep === 1 && (
          <Step1BasicInfo formData={formData} setFormData={setFormData} modelDefaults={modelDefaults} />
        )}
        {currentStep === 2 && (
          <Step2Models
            formData={formData}
            models={models}
            isLoading={modelsLoading}
            addItem={addItem}
            updateItemQuantity={updateItemQuantity}
            updateItemPosition={updateItemPosition}
            removeItem={removeItem}
          />
        )}
        {currentStep === 3 && (
          <Step3Materials
            formData={formData}
            spools={spools}
            isLoading={spoolsLoading}
            suggestedMaterials={suggestedMaterials}
            applySuggestedMaterials={applySuggestedMaterials}
            addMaterial={addMaterial}
            updateMaterialWeight={updateMaterialWeight}
            removeMaterial={removeMaterial}
          />
        )}
        {currentStep === 4 && (
          <Step4Review formData={formData} totals={totals} />
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-4 border-t">
        <Button
          type="button"
          variant="outline"
          onClick={handleBack}
          disabled={currentStep === 1}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className="flex gap-2">
          <Button type="button" variant="outline" asChild>
            <Link to="/production-runs">Cancel</Link>
          </Button>

          {currentStep < 4 ? (
            <Button type="button" onClick={handleNext} disabled={!canProceed(currentStep)}>
              Next
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={createMutation.isPending}
            >
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
          )}
        </div>
      </div>

      {/* Error Display */}
      {createMutation.isError && (
        <div className="rounded-md bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Error creating production run: {(createMutation.error as Error).message}
          </p>
        </div>
      )}
    </div>
  )
}

// Predefined options for printers and slicers
const PRINTER_OPTIONS = [
  // Bambu Lab
  { value: 'Bambu Lab X1 Carbon', label: 'Bambu Lab X1 Carbon' },
  { value: 'Bambu Lab X1', label: 'Bambu Lab X1' },
  { value: 'Bambu Lab P1S', label: 'Bambu Lab P1S' },
  { value: 'Bambu Lab P1P', label: 'Bambu Lab P1P' },
  { value: 'Bambu Lab A1', label: 'Bambu Lab A1' },
  { value: 'Bambu Lab A1 Mini', label: 'Bambu Lab A1 Mini' },
  // Prusa
  { value: 'Prusa MK4', label: 'Prusa MK4' },
  { value: 'Prusa MK3S+', label: 'Prusa MK3S+' },
  { value: 'Prusa Mini+', label: 'Prusa Mini+' },
  { value: 'Prusa XL', label: 'Prusa XL' },
  // Creality
  { value: 'Creality K1 Max', label: 'Creality K1 Max' },
  { value: 'Creality K1', label: 'Creality K1' },
  { value: 'Creality Ender 3 V3', label: 'Creality Ender 3 V3' },
  { value: 'Creality Ender 3 S1', label: 'Creality Ender 3 S1' },
  // Elegoo
  { value: 'Elegoo Neptune 4 Pro', label: 'Elegoo Neptune 4 Pro' },
  { value: 'Elegoo Neptune 4', label: 'Elegoo Neptune 4' },
  // Anker
  { value: 'AnkerMake M5C', label: 'AnkerMake M5C' },
  { value: 'AnkerMake M5', label: 'AnkerMake M5' },
  // Voron
  { value: 'Voron 2.4', label: 'Voron 2.4' },
  { value: 'Voron Trident', label: 'Voron Trident' },
  { value: 'Voron 0.2', label: 'Voron 0.2' },
]

const SLICER_OPTIONS = [
  { value: 'Bambu Studio', label: 'Bambu Studio' },
  { value: 'OrcaSlicer', label: 'OrcaSlicer' },
  { value: 'PrusaSlicer', label: 'PrusaSlicer' },
  { value: 'Cura', label: 'Cura' },
  { value: 'SuperSlicer', label: 'SuperSlicer' },
  { value: 'Simplify3D', label: 'Simplify3D' },
  { value: 'IdeaMaker', label: 'IdeaMaker' },
  { value: 'Creality Print', label: 'Creality Print' },
]

// Step 1: Basic Info
function Step1BasicInfo({
  formData,
  setFormData,
  modelDefaults,
}: {
  formData: WizardFormData
  setFormData: (data: WizardFormData) => void
  modelDefaults: Record<string, ModelProductionDefaults>
}) {
  // Calculate model defaults from selected items
  const calculateModelDefaults = () => {
    let totalTime = 0
    let totalWeight = 0

    formData.items.forEach((item) => {
      const defaults = modelDefaults[item.model_id]
      if (defaults) {
        // Time: (print_time_minutes / prints_per_plate) * quantity
        const timePerItem = defaults.print_time_minutes / defaults.prints_per_plate
        totalTime += (timePerItem * item.quantity) / 60 // Convert to hours

        // Weight: Sum of BOM materials * quantity
        const weightPerItem = defaults.bom_materials.reduce(
          (sum, mat) => sum + parseFloat(mat.weight_grams),
          0
        )
        totalWeight += weightPerItem * item.quantity
      }
    })

    return {
      totalTimeHours: totalTime > 0 ? totalTime : null,
      totalWeightGrams: totalWeight > 0 ? totalWeight : null,
    }
  }

  const modelDefaultsCalc = calculateModelDefaults()

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Printer Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Printer Settings</CardTitle>
          <CardDescription>Printer and slicer information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="printer_name">Printer</Label>
            <Select
              value={formData.printer_name}
              onValueChange={(value) => setFormData({ ...formData, printer_name: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a printer" />
              </SelectTrigger>
              <SelectContent>
                {PRINTER_OPTIONS.map((printer) => (
                  <SelectItem key={printer.value} value={printer.value}>
                    {printer.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="slicer_software">Slicer Software</Label>
            <Select
              value={formData.slicer_software}
              onValueChange={(value) => setFormData({ ...formData, slicer_software: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a slicer" />
              </SelectTrigger>
              <SelectContent>
                {SLICER_OPTIONS.map((slicer) => (
                  <SelectItem key={slicer.value} value={slicer.value}>
                    {slicer.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="bed_temperature">Bed Temp (°C)</Label>
              <Input
                id="bed_temperature"
                type="number"
                step="1"
                placeholder="e.g., 60"
                value={formData.bed_temperature ?? ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    bed_temperature: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="nozzle_temperature">Nozzle Temp (°C)</Label>
              <Input
                id="nozzle_temperature"
                type="number"
                step="1"
                placeholder="e.g., 220"
                value={formData.nozzle_temperature ?? ''}
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

      {/* Slicer Estimates */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Slicer Estimates</CardTitle>
              <CardDescription>Copy from your slicer (optional)</CardDescription>
            </div>
            {modelDefaultsCalc.totalTimeHours !== null && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setFormData({
                    ...formData,
                    estimated_print_time_hours: modelDefaultsCalc.totalTimeHours || undefined,
                    estimated_model_weight_grams: modelDefaultsCalc.totalWeightGrams || undefined,
                  })
                }}
              >
                <Info className="h-4 w-4 mr-2" />
                Use Model Defaults
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Print Time</Label>
            <div className="flex items-center gap-2">
              <Input
                id="estimated_print_time_hours_part"
                type="number"
                min="0"
                step="1"
                placeholder="0"
                className="w-20"
                value={formData.estimated_print_time_hours !== undefined
                  ? Math.floor(formData.estimated_print_time_hours)
                  : ''}
                onChange={(e) => {
                  const hours = e.target.value ? parseInt(e.target.value) : 0
                  const currentMinutes = formData.estimated_print_time_hours !== undefined
                    ? Math.round((formData.estimated_print_time_hours % 1) * 60)
                    : 0
                  const totalHours = hours + currentMinutes / 60
                  setFormData({
                    ...formData,
                    estimated_print_time_hours: totalHours > 0 ? totalHours : undefined,
                  })
                }}
              />
              <span className="text-sm text-muted-foreground">h</span>
              <Input
                id="estimated_print_time_minutes_part"
                type="number"
                min="0"
                max="59"
                step="1"
                placeholder="0"
                className="w-20"
                value={formData.estimated_print_time_hours !== undefined
                  ? Math.round((formData.estimated_print_time_hours % 1) * 60)
                  : ''}
                onChange={(e) => {
                  const minutes = e.target.value ? Math.min(59, parseInt(e.target.value)) : 0
                  const currentHours = formData.estimated_print_time_hours !== undefined
                    ? Math.floor(formData.estimated_print_time_hours)
                    : 0
                  const totalHours = currentHours + minutes / 60
                  setFormData({
                    ...formData,
                    estimated_print_time_hours: totalHours > 0 ? totalHours : undefined,
                  })
                }}
              />
              <span className="text-sm text-muted-foreground">m</span>
            </div>
            {modelDefaultsCalc.totalTimeHours !== null && (
              <div className="flex items-start gap-2 mt-2 p-2 bg-blue-50 dark:bg-blue-950/20 rounded-md border border-blue-200 dark:border-blue-800">
                <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <span className="text-muted-foreground">Model default: </span>
                  <span className="font-medium text-blue-600 dark:text-blue-400">
                    {Math.floor(modelDefaultsCalc.totalTimeHours)}h {Math.round((modelDefaultsCalc.totalTimeHours % 1) * 60)}m
                  </span>
                  <span className="text-muted-foreground text-xs block">
                    Calculated from selected models × quantity
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label>Filament Usage (g)</Label>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label htmlFor="estimated_model_weight_grams" className="text-xs text-muted-foreground">
                  Model
                </Label>
                <Input
                  id="estimated_model_weight_grams"
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder="0"
                  value={formData.estimated_model_weight_grams ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      estimated_model_weight_grams: e.target.value
                        ? parseFloat(e.target.value)
                        : undefined,
                    })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="estimated_flushed_grams" className="text-xs text-muted-foreground">
                  Flushed
                </Label>
                <Input
                  id="estimated_flushed_grams"
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder="0"
                  value={formData.estimated_flushed_grams ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      estimated_flushed_grams: e.target.value
                        ? parseFloat(e.target.value)
                        : undefined,
                    })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="estimated_tower_grams" className="text-xs text-muted-foreground">
                  Tower
                </Label>
                <Input
                  id="estimated_tower_grams"
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder="0"
                  value={formData.estimated_tower_grams ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      estimated_tower_grams: e.target.value
                        ? parseFloat(e.target.value)
                        : undefined,
                    })
                  }
                />
              </div>
            </div>
            {(formData.estimated_model_weight_grams || formData.estimated_flushed_grams || formData.estimated_tower_grams) && (
              <div className="flex items-center justify-between mt-2 p-2 bg-muted rounded-md">
                <span className="text-sm text-muted-foreground">Total:</span>
                <span className="text-sm font-medium">
                  {((formData.estimated_model_weight_grams || 0) + (formData.estimated_flushed_grams || 0) + (formData.estimated_tower_grams || 0)).toFixed(1)}g
                </span>
              </div>
            )}
            {modelDefaultsCalc.totalWeightGrams !== null && (
              <div className="flex items-start gap-2 mt-2 p-2 bg-blue-50 dark:bg-blue-950/20 rounded-md border border-blue-200 dark:border-blue-800">
                <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <span className="text-muted-foreground">Model BOM total: </span>
                  <span className="font-medium text-blue-600 dark:text-blue-400">
                    {modelDefaultsCalc.totalWeightGrams.toFixed(1)}g
                  </span>
                  <span className="text-muted-foreground text-xs block">
                    From model BOMs × quantity (excludes waste)
                  </span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>Notes</CardTitle>
          <CardDescription>Any additional information (optional)</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            id="notes"
            placeholder="e.g., First attempt at multi-color print..."
            rows={3}
            value={formData.notes}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          />
        </CardContent>
      </Card>
    </div>
  )
}

// Step 2: Models
function Step2Models({
  formData,
  models,
  isLoading,
  addItem,
  updateItemQuantity,
  updateItemPosition,
  removeItem,
}: {
  formData: WizardFormData
  models: Model[]
  isLoading: boolean
  addItem: (model: Model) => void
  updateItemQuantity: (modelId: string, quantity: number) => void
  updateItemPosition: (modelId: string, position: string) => void
  removeItem: (modelId: string) => void
}) {
  const [selectedModelId, setSelectedModelId] = useState<string>('')

  const availableModels = models.filter(
    (m) => !formData.items.some((item) => item.model_id === m.id)
  )

  const handleAddSelected = () => {
    const model = models.find((m) => m.id === selectedModelId)
    if (model) {
      addItem(model)
      setSelectedModelId('')
    }
  }

  return (
    <div className="space-y-6">
      {/* Add Model */}
      <Card>
        <CardHeader>
          <CardTitle>Add Models</CardTitle>
          <CardDescription>Select models to include in this production run</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Select
              value={selectedModelId}
              onValueChange={setSelectedModelId}
              disabled={isLoading || availableModels.length === 0}
            >
              <SelectTrigger className="flex-1">
                <SelectValue
                  placeholder={
                    isLoading
                      ? 'Loading models...'
                      : availableModels.length === 0
                      ? 'All models added'
                      : 'Select a model'
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <span className="font-medium">{model.sku}</span>
                    <span className="text-muted-foreground ml-2">{model.name}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={handleAddSelected} disabled={!selectedModelId}>
              <Plus className="h-4 w-4 mr-2" />
              Add
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Selected Items */}
      <Card>
        <CardHeader>
          <CardTitle>Selected Models ({formData.items.length})</CardTitle>
          <CardDescription>
            {formData.items.length === 0
              ? 'No models selected yet. You can add models or skip to materials.'
              : 'Adjust quantities and bed positions'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {formData.items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Package className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>No models added yet</p>
              <p className="text-sm">Select models above to track what you're printing</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead className="w-32">Quantity</TableHead>
                  <TableHead className="w-32">Bed Position</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {formData.items.map((item) => (
                  <TableRow key={item.model_id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{item.model_sku}</div>
                        <div className="text-sm text-muted-foreground">{item.model_name}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min="1"
                        value={item.quantity}
                        onChange={(e) =>
                          updateItemQuantity(item.model_id, parseInt(e.target.value) || 1)
                        }
                        className="w-20"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        placeholder="e.g., A1"
                        value={item.bed_position}
                        onChange={(e) => updateItemPosition(item.model_id, e.target.value)}
                        className="w-20"
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeItem(item.model_id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Step 3: Materials
function Step3Materials({
  formData,
  spools,
  isLoading,
  suggestedMaterials,
  applySuggestedMaterials,
  addMaterial,
  updateMaterialWeight,
  removeMaterial,
}: {
  formData: WizardFormData
  spools: SpoolResponse[]
  isLoading: boolean
  suggestedMaterials: Array<{
    spool_id: string
    spool_name: string
    material_type: string
    color: string
    color_hex?: string
    total_weight_grams: number
    cost_per_gram: number
    current_weight: number
    is_active: boolean
    models: Array<{ model_name: string; model_sku: string; quantity: number; weight_grams: number }>
  }>
  applySuggestedMaterials: () => void
  addMaterial: (spool: SpoolResponse) => void
  updateMaterialWeight: (
    spoolId: string,
    field: 'estimated_model_weight_grams' | 'estimated_flushed_grams' | 'estimated_tower_grams',
    value: number
  ) => void
  removeMaterial: (spoolId: string) => void
}) {
  const [selectedSpoolId, setSelectedSpoolId] = useState<string>('')

  const availableSpools = spools.filter(
    (s) => !formData.materials.some((mat) => mat.spool_id === s.id)
  )

  const handleAddSelected = () => {
    const spool = spools.find((s) => s.id === selectedSpoolId)
    if (spool) {
      addMaterial(spool)
      setSelectedSpoolId('')
    }
  }

  return (
    <div className="space-y-6">
      {/* Explanatory info card */}
      <Alert className="border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
        <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <AlertTitle className="text-blue-800 dark:text-blue-200">Material Usage Breakdown</AlertTitle>
        <AlertDescription className="text-blue-700 dark:text-blue-300">
          <strong>Model Weight</strong>: Filament that ends up in the prints (auto-calculated from BOM).{' '}
          <strong>Flush/Purge</strong>: Waste from color changes.{' '}
          <strong>Tower</strong>: Purge tower weight (typically 10-20g per plate for multi-color).
        </AlertDescription>
      </Alert>

      {/* Suggested Materials from Model BOM */}
      {suggestedMaterials.length > 0 && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5 text-primary" />
                  Suggested Materials from Model BOM
                </CardTitle>
                <CardDescription>
                  Materials from selected models' Bill of Materials (scaled by quantity)
                </CardDescription>
              </div>
              <Button onClick={applySuggestedMaterials} size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Apply All Suggestions
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {suggestedMaterials.map((suggestion) => {
                const alreadyAdded = formData.materials.some(mat => mat.spool_id === suggestion.spool_id)
                const isLowInventory = suggestion.current_weight < suggestion.total_weight_grams
                const isInactive = !suggestion.is_active

                return (
                  <div
                    key={suggestion.spool_id}
                    className={`p-3 rounded-md border ${
                      alreadyAdded
                        ? 'bg-muted/50 opacity-60'
                        : isInactive || isLowInventory
                        ? 'bg-destructive/10 border-destructive/20'
                        : 'bg-background'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {suggestion.color_hex && (
                            <div
                              className="w-4 h-4 rounded-full border"
                              style={{ backgroundColor: suggestion.color_hex }}
                            />
                          )}
                          <span className="font-medium">{suggestion.spool_name}</span>
                          <Badge variant="outline" className="text-xs">
                            {suggestion.material_type}
                          </Badge>
                          {alreadyAdded && <Badge variant="secondary" className="text-xs">Added</Badge>}
                          {isInactive && <Badge variant="destructive" className="text-xs">Inactive</Badge>}
                          {isLowInventory && !isInactive && (
                            <Badge variant="destructive" className="text-xs">Low Inventory</Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground space-y-1">
                          <div>
                            Suggested weight: <span className="font-medium">{suggestion.total_weight_grams.toFixed(1)}g</span>
                            {' · '}
                            Available: <span className="font-medium">{suggestion.current_weight.toFixed(0)}g</span>
                          </div>
                          <details className="text-xs">
                            <summary className="cursor-pointer hover:text-foreground">
                              Used in {suggestion.models.length} model{suggestion.models.length > 1 ? 's' : ''}
                            </summary>
                            <ul className="mt-1 ml-4 space-y-0.5">
                              {suggestion.models.map((model, idx) => (
                                <li key={idx}>
                                  {model.model_sku}: {model.weight_grams.toFixed(1)}g (qty: {model.quantity})
                                </li>
                              ))}
                            </ul>
                          </details>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Spool */}
      <Card>
        <CardHeader>
          <CardTitle>Add Materials</CardTitle>
          <CardDescription>Select spools that will be used in this run</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <SearchableSpoolSelect
              spools={availableSpools}
              value={selectedSpoolId}
              onValueChange={setSelectedSpoolId}
              placeholder={
                isLoading
                  ? 'Loading spools...'
                  : availableSpools.length === 0
                  ? 'All spools added'
                  : 'Search for a spool...'
              }
              disabled={isLoading || availableSpools.length === 0}
              className="flex-1"
            />
            <Button onClick={handleAddSelected} disabled={!selectedSpoolId}>
              <Plus className="h-4 w-4 mr-2" />
              Add
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Selected Materials */}
      <Card>
        <CardHeader>
          <CardTitle>Selected Materials ({formData.materials.length})</CardTitle>
          <CardDescription>
            {formData.materials.length === 0
              ? 'No spools selected. Add spools to track material usage.'
              : 'Enter estimated weights from your slicer'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {formData.materials.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Layers className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>No materials added yet</p>
              <p className="text-sm">Select spools above to track material usage</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Spool</TableHead>
                  <TableHead>Available</TableHead>
                  <TableHead className="w-24">
                    <div className="flex items-center gap-1">
                      Model (g)
                      <Popover>
                        <PopoverTrigger asChild>
                          <button className="text-muted-foreground hover:text-foreground">
                            <HelpCircle className="h-3 w-3" />
                          </button>
                        </PopoverTrigger>
                        <PopoverContent className="w-64 text-sm">
                          <p className="font-medium mb-1">Model Weight</p>
                          <p className="text-muted-foreground">
                            Total filament from BOM × quantity. This becomes your finished prints.
                          </p>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </TableHead>
                  <TableHead className="w-24">
                    <div className="flex items-center gap-1">
                      Flushed (g)
                      <Popover>
                        <PopoverTrigger asChild>
                          <button className="text-muted-foreground hover:text-foreground">
                            <HelpCircle className="h-3 w-3" />
                          </button>
                        </PopoverTrigger>
                        <PopoverContent className="w-64 text-sm">
                          <p className="font-medium mb-1">Flush/Purge Waste</p>
                          <p className="text-muted-foreground">
                            Waste filament from color transitions. Check your slicer's purge settings.
                          </p>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </TableHead>
                  <TableHead className="w-24">
                    <div className="flex items-center gap-1">
                      Tower (g)
                      <Popover>
                        <PopoverTrigger asChild>
                          <button className="text-muted-foreground hover:text-foreground">
                            <HelpCircle className="h-3 w-3" />
                          </button>
                        </PopoverTrigger>
                        <PopoverContent className="w-64 text-sm">
                          <p className="font-medium mb-1">Purge Tower</p>
                          <p className="text-muted-foreground">
                            Tower weight shared per plate. For multi-color, typically 10-20g regardless of item count.
                          </p>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </TableHead>
                  <TableHead className="w-20">Total</TableHead>
                  <TableHead className="w-20">Cost</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {formData.materials.map((mat) => {
                  const totalWeight = mat.estimated_model_weight_grams + mat.estimated_flushed_grams + mat.estimated_tower_grams
                  const estCost = totalWeight * mat.cost_per_gram
                  return (
                    <TableRow key={mat.spool_id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{mat.spool_name}</div>
                          <Badge variant="outline" className="text-xs">
                            {mat.material_type}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">{mat.current_weight.toFixed(0)}g</span>
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.1"
                          value={mat.estimated_model_weight_grams || ''}
                          onChange={(e) =>
                            updateMaterialWeight(
                              mat.spool_id,
                              'estimated_model_weight_grams',
                              parseFloat(e.target.value) || 0
                            )
                          }
                          className="w-20"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.1"
                          value={mat.estimated_flushed_grams || ''}
                          onChange={(e) =>
                            updateMaterialWeight(
                              mat.spool_id,
                              'estimated_flushed_grams',
                              parseFloat(e.target.value) || 0
                            )
                          }
                          className="w-20"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="0.1"
                          value={mat.estimated_tower_grams || ''}
                          onChange={(e) =>
                            updateMaterialWeight(
                              mat.spool_id,
                              'estimated_tower_grams',
                              parseFloat(e.target.value) || 0
                            )
                          }
                          className="w-20"
                        />
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium">{totalWeight.toFixed(1)}g</span>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-medium">£{estCost.toFixed(2)}</span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeMaterial(mat.spool_id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Step 4: Review
function Step4Review({
  formData,
  totals,
}: {
  formData: WizardFormData
  totals: { totalItems: number; totalMaterialWeight: number; totalMaterialCost: number }
}) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totals.totalItems}</div>
            <p className="text-xs text-muted-foreground">
              across {formData.items.length} model(s)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Est. Material
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totals.totalMaterialWeight.toFixed(1)}g</div>
            <p className="text-xs text-muted-foreground">
              from {formData.materials.length} spool(s)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Est. Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">£{totals.totalMaterialCost.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">material cost only</p>
          </CardContent>
        </Card>
      </div>

      {/* Printer Info */}
      {(formData.printer_name ||
        formData.slicer_software ||
        formData.estimated_print_time_hours) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Printer className="h-5 w-5" />
              Printer Settings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {formData.printer_name && (
                <div>
                  <p className="text-sm text-muted-foreground">Printer</p>
                  <p className="font-medium">{formData.printer_name}</p>
                </div>
              )}
              {formData.slicer_software && (
                <div>
                  <p className="text-sm text-muted-foreground">Slicer</p>
                  <p className="font-medium">{formData.slicer_software}</p>
                </div>
              )}
              {formData.estimated_print_time_hours && (
                <div>
                  <p className="text-sm text-muted-foreground">Est. Print Time</p>
                  <p className="font-medium">
                    {Math.floor(formData.estimated_print_time_hours)}h {Math.round((formData.estimated_print_time_hours % 1) * 60)}m
                  </p>
                </div>
              )}
              {formData.bed_temperature && (
                <div>
                  <p className="text-sm text-muted-foreground">Bed Temp</p>
                  <p className="font-medium">{formData.bed_temperature}°C</p>
                </div>
              )}
              {formData.nozzle_temperature && (
                <div>
                  <p className="text-sm text-muted-foreground">Nozzle Temp</p>
                  <p className="font-medium">{formData.nozzle_temperature}°C</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Items List */}
      {formData.items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Models ({formData.items.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Position</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {formData.items.map((item) => (
                  <TableRow key={item.model_id}>
                    <TableCell>
                      <span className="font-medium">{item.model_sku}</span>
                      <span className="text-muted-foreground ml-2">{item.model_name}</span>
                    </TableCell>
                    <TableCell>{item.quantity}</TableCell>
                    <TableCell>{item.bed_position || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Materials List */}
      {formData.materials.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Materials ({formData.materials.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Spool</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Flushed</TableHead>
                  <TableHead>Tower</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Cost</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {formData.materials.map((mat) => {
                  const totalWeight = mat.estimated_model_weight_grams + mat.estimated_flushed_grams + mat.estimated_tower_grams
                  const estCost = totalWeight * mat.cost_per_gram
                  return (
                    <TableRow key={mat.spool_id}>
                      <TableCell className="font-medium">{mat.spool_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{mat.material_type}</Badge>
                      </TableCell>
                      <TableCell>{mat.estimated_model_weight_grams.toFixed(1)}g</TableCell>
                      <TableCell>{mat.estimated_flushed_grams.toFixed(1)}g</TableCell>
                      <TableCell>{mat.estimated_tower_grams.toFixed(1)}g</TableCell>
                      <TableCell className="font-medium">{totalWeight.toFixed(1)}g</TableCell>
                      <TableCell>£{estCost.toFixed(2)}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Notes */}
      {formData.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap">{formData.notes}</p>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {formData.items.length === 0 && formData.materials.length === 0 && (
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">
              <ClipboardList className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p className="font-medium">Quick Run Mode</p>
              <p className="text-sm">
                Creating a production run without items or materials.
                <br />
                You can add them later after the run is created.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
