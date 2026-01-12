/**
 * Onboarding Wizard Page
 * Multi-step wizard for new tenant setup
 */

import { useState, useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Sparkles } from 'lucide-react'
import { StepIndicator, ONBOARDING_STEPS } from '@/components/onboarding/StepIndicator'
import { Step1BusinessInfo } from '@/components/onboarding/Step1BusinessInfo'
import { Step2CraftType } from '@/components/onboarding/Step2CraftType'
import { Step3ShopSetup } from '@/components/onboarding/Step3ShopSetup'
import { Step4FirstProduct } from '@/components/onboarding/Step4FirstProduct'
import {
  getOnboardingStatus,
  updateOnboardingStep1,
  updateOnboardingStep2,
  updateOnboardingStep3,
  updateOnboardingStep4,
  type OnboardingStatusResponse,
} from '@/lib/api/onboarding'

export function Onboarding() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [currentStep, setCurrentStep] = useState(1)
  const [error, setError] = useState<string | null>(null)

  // Fetch onboarding status
  const { data: status, isLoading: isLoadingStatus } = useQuery<OnboardingStatusResponse>({
    queryKey: ['onboarding-status'],
    queryFn: getOnboardingStatus,
    retry: 1,
  })

  // Initialize step from status
  useEffect(() => {
    if (status) {
      // If onboarding is complete, redirect to dashboard
      if (status.is_completed) {
        navigate({ to: '/dashboard' })
        return
      }
      // Set current step based on status
      setCurrentStep(status.current_step || 1)
    }
  }, [status, navigate])

  // Step mutations
  const step1Mutation = useMutation({
    mutationFn: updateOnboardingStep1,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-status'] })
      if (data.next_step) {
        setCurrentStep(data.next_step)
      }
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to save. Please try again.')
    },
  })

  const step2Mutation = useMutation({
    mutationFn: updateOnboardingStep2,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-status'] })
      if (data.next_step) {
        setCurrentStep(data.next_step)
      }
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to save. Please try again.')
    },
  })

  const step3Mutation = useMutation({
    mutationFn: updateOnboardingStep3,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-status'] })
      if (data.next_step) {
        setCurrentStep(data.next_step)
      }
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to save. Please try again.')
    },
  })

  const step4Mutation = useMutation({
    mutationFn: updateOnboardingStep4,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-status'] })
      if (data.is_completed) {
        // Onboarding complete - redirect to dashboard
        navigate({ to: '/dashboard' })
      }
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to save. Please try again.')
    },
  })

  // Navigation handlers
  function goBack() {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
      setError(null)
    }
  }

  // Get completed steps array
  const completedSteps = status?.completed_steps || []

  // Get step data for initial values
  const stepData = status?.step_data || {}

  // Check if any mutation is loading
  const isLoading =
    step1Mutation.isPending ||
    step2Mutation.isPending ||
    step3Mutation.isPending ||
    step4Mutation.isPending

  // Show loading state while fetching status
  if (isLoadingStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 text-primary mb-2">
            <Sparkles className="h-5 w-5" />
            <span className="text-sm font-medium">Welcome to Batchivo</span>
          </div>
          <h1 className="text-2xl font-bold">Set Up Your Shop</h1>
          <p className="text-muted-foreground mt-1">
            Complete these steps to get your shop ready for business.
          </p>
        </div>

        {/* Step Indicator */}
        <StepIndicator
          steps={ONBOARDING_STEPS}
          currentStep={currentStep}
          completedSteps={completedSteps}
        />

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Step Content */}
        <Card>
          <CardHeader>
            <CardTitle>{ONBOARDING_STEPS[currentStep - 1]?.title}</CardTitle>
          </CardHeader>
          <CardContent>
            {currentStep === 1 && (
              <Step1BusinessInfo
                initialData={stepData.step_1 as Record<string, string> | undefined}
                onSubmit={step1Mutation.mutate}
                isLoading={isLoading}
              />
            )}

            {currentStep === 2 && (
              <Step2CraftType
                initialData={stepData.step_2 as { tenant_type?: 'GENERIC' | 'THREED_PRINT' | 'HAND_KNITTING' | 'MACHINE_KNITTING' } | undefined}
                onSubmit={step2Mutation.mutate}
                onBack={goBack}
                isLoading={isLoading}
              />
            )}

            {currentStep === 3 && (
              <Step3ShopSetup
                initialData={stepData.step_3 as Record<string, string> | undefined}
                onSubmit={step3Mutation.mutate}
                onBack={goBack}
                isLoading={isLoading}
              />
            )}

            {currentStep === 4 && (
              <Step4FirstProduct
                initialData={stepData.step_4 as { product_name?: string; product_description?: string; product_price?: number } | undefined}
                onSubmit={step4Mutation.mutate}
                onBack={goBack}
                isLoading={isLoading}
                currency={(stepData.step_3 as Record<string, string>)?.currency}
              />
            )}
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          Your progress is saved automatically. You can come back to finish setup anytime.
        </p>
      </div>
    </div>
  )
}
