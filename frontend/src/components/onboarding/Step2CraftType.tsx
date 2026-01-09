/**
 * Step 2: Craft Type Selection
 * Visual card selection for business/craft type
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Printer, Sparkles, Scissors, Cog } from 'lucide-react'
import { cn } from '@/lib/utils'

type TenantType = 'GENERIC' | 'THREED_PRINT' | 'HAND_KNITTING' | 'MACHINE_KNITTING'

interface CraftTypeOption {
  type: TenantType
  title: string
  description: string
  icon: React.ReactNode
  features: string[]
}

const CRAFT_TYPES: CraftTypeOption[] = [
  {
    type: 'THREED_PRINT',
    title: '3D Printing',
    description: 'For 3D print shops and makers',
    icon: <Printer className="h-8 w-8" />,
    features: [
      'Filament spool tracking',
      'Print time estimation',
      'Material cost calculation',
      'Production run management',
    ],
  },
  {
    type: 'HAND_KNITTING',
    title: 'Hand Knitting',
    description: 'For knitters and crocheters',
    icon: <Sparkles className="h-8 w-8" />,
    features: [
      'Yarn stash inventory',
      'Needle collection',
      'Pattern library',
      'Project tracking',
    ],
  },
  {
    type: 'MACHINE_KNITTING',
    title: 'Machine Knitting',
    description: 'For machine knitting businesses',
    icon: <Cog className="h-8 w-8" />,
    features: [
      'Yarn inventory',
      'Machine management',
      'Tension tracking',
      'Production runs',
    ],
  },
  {
    type: 'GENERIC',
    title: 'General Crafts',
    description: 'For other craft businesses',
    icon: <Scissors className="h-8 w-8" />,
    features: [
      'Product catalog',
      'Order management',
      'Inventory tracking',
      'Sales channels',
    ],
  },
]

interface Step2CraftTypeProps {
  initialData?: {
    tenant_type?: TenantType
  }
  onSubmit: (data: { tenant_type: TenantType }) => void
  onBack: () => void
  isLoading?: boolean
}

export function Step2CraftType({ initialData, onSubmit, onBack, isLoading }: Step2CraftTypeProps) {
  const [selectedType, setSelectedType] = useState<TenantType | null>(
    initialData?.tenant_type || null
  )

  function handleSubmit() {
    if (selectedType) {
      onSubmit({ tenant_type: selectedType })
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <p className="text-muted-foreground">
          Select the type of craft business you run. This customizes your dashboard and features.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {CRAFT_TYPES.map((craft) => (
          <Card
            key={craft.type}
            className={cn(
              'cursor-pointer transition-all hover:border-primary/50',
              selectedType === craft.type
                ? 'border-primary ring-2 ring-primary ring-offset-2'
                : 'border-border'
            )}
            onClick={() => !isLoading && setSelectedType(craft.type)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div
                  className={cn(
                    'p-2 rounded-lg',
                    selectedType === craft.type
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
                  {craft.icon}
                </div>
                {selectedType === craft.type && (
                  <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                    <svg
                      className="h-3 w-3 text-primary-foreground"
                      fill="currentColor"
                      viewBox="0 0 12 12"
                    >
                      <path d="M10.28 2.28L3.989 8.575 1.695 6.28A1 1 0 00.28 7.695l3 3a1 1 0 001.414 0l7-7A1 1 0 0010.28 2.28z" />
                    </svg>
                  </div>
                )}
              </div>
              <CardTitle className="text-lg mt-2">{craft.title}</CardTitle>
              <CardDescription>{craft.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm text-muted-foreground space-y-1">
                {craft.features.map((feature, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary/60" />
                    {feature}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-between pt-4">
        <Button type="button" variant="outline" onClick={onBack} disabled={isLoading}>
          Back
        </Button>
        <Button onClick={handleSubmit} disabled={!selectedType || isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            'Continue'
          )}
        </Button>
      </div>
    </div>
  )
}
