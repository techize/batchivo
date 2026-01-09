/**
 * Step indicator for onboarding wizard
 * Shows progress through multi-step form
 */
/* eslint-disable react-refresh/only-export-components */

import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Step {
  number: number
  title: string
  description?: string
}

interface StepIndicatorProps {
  steps: Step[]
  currentStep: number
  completedSteps: number[]
}

export function StepIndicator({ steps, currentStep, completedSteps }: StepIndicatorProps) {
  return (
    <nav aria-label="Progress" className="mb-8">
      <ol className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = completedSteps.includes(step.number)
          const isCurrent = currentStep === step.number
          const isLast = index === steps.length - 1

          return (
            <li key={step.number} className={cn('relative', !isLast && 'flex-1')}>
              <div className="flex items-center">
                {/* Step circle */}
                <div
                  className={cn(
                    'relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors',
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
                    <span className="text-sm font-medium">{step.number}</span>
                  )}
                </div>

                {/* Connector line */}
                {!isLast && (
                  <div
                    className={cn(
                      'mx-2 h-0.5 flex-1 transition-colors',
                      isCompleted ? 'bg-primary' : 'bg-muted'
                    )}
                  />
                )}
              </div>

              {/* Step label */}
              <div className="mt-2">
                <p
                  className={cn(
                    'text-sm font-medium',
                    isCurrent || isCompleted ? 'text-foreground' : 'text-muted-foreground'
                  )}
                >
                  {step.title}
                </p>
                {step.description && (
                  <p className="text-xs text-muted-foreground mt-0.5 hidden sm:block">
                    {step.description}
                  </p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

// Default steps configuration for the onboarding wizard
export const ONBOARDING_STEPS: Step[] = [
  { number: 1, title: 'Business Info', description: 'Name and URL' },
  { number: 2, title: 'Craft Type', description: 'What you make' },
  { number: 3, title: 'Shop Setup', description: 'Branding' },
  { number: 4, title: 'First Product', description: 'Optional' },
]
