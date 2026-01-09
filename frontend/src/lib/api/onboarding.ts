/**
 * Onboarding API client
 */

import { api } from '@/lib/api'

export interface TenantRegistrationRequest {
  email: string
  password: string
  full_name: string
  business_name: string
  tenant_type?: 'GENERIC' | 'THREED_PRINT' | 'HAND_KNITTING' | 'MACHINE_KNITTING'
}

export interface TenantRegistrationResponse {
  message: string
  email: string
}

export interface EmailVerificationResponse {
  message: string
  tenant_id: string
  tenant_name: string
  tenant_slug: string
  user_id: string
  access_token: string
  refresh_token: string
  token_type: string
}

export interface ResendVerificationResponse {
  message: string
}

export interface OnboardingStatusResponse {
  current_step: number
  completed_steps: number[]
  is_completed: boolean
  step_data: {
    step_1?: Record<string, unknown>
    step_2?: Record<string, unknown>
    step_3?: Record<string, unknown>
    step_4?: Record<string, unknown>
  } | null
  tenant_id: string
  tenant_name: string
  tenant_type: string
}

/**
 * Register a new tenant
 */
export async function registerTenant(
  data: TenantRegistrationRequest
): Promise<TenantRegistrationResponse> {
  const response = await api.post('/onboarding/register', data)
  return response.data
}

/**
 * Verify email with token
 */
export async function verifyEmail(token: string): Promise<EmailVerificationResponse> {
  const response = await api.post('/onboarding/verify-email', { token })
  return response.data
}

/**
 * Resend verification email
 */
export async function resendVerification(email: string): Promise<ResendVerificationResponse> {
  const response = await api.post('/onboarding/resend-verification', { email })
  return response.data
}

/**
 * Get onboarding wizard status
 */
export async function getOnboardingStatus(): Promise<OnboardingStatusResponse> {
  const response = await api.get('/onboarding/wizard/status')
  return response.data
}

/**
 * Update onboarding step 1 - Business information
 */
export async function updateOnboardingStep1(data: {
  business_name: string
  slug?: string
  business_description?: string
}): Promise<{ message: string; step_completed: number; next_step: number | null; is_completed: boolean }> {
  const response = await api.put('/onboarding/wizard/step/1', data)
  return response.data
}

/**
 * Update onboarding step 2 - Business type
 */
export async function updateOnboardingStep2(data: {
  tenant_type: 'GENERIC' | 'THREED_PRINT' | 'HAND_KNITTING' | 'MACHINE_KNITTING'
}): Promise<{ message: string; step_completed: number; next_step: number | null; is_completed: boolean }> {
  const response = await api.put('/onboarding/wizard/step/2', data)
  return response.data
}

/**
 * Update onboarding step 3 - Shop setup
 */
export async function updateOnboardingStep3(data: {
  shop_display_name?: string
  currency?: string
  timezone?: string
  primary_color?: string
}): Promise<{ message: string; step_completed: number; next_step: number | null; is_completed: boolean }> {
  const response = await api.put('/onboarding/wizard/step/3', data)
  return response.data
}

/**
 * Update onboarding step 4 - First product (optional)
 */
export async function updateOnboardingStep4(data: {
  skip?: boolean
  product_name?: string
  product_description?: string
  product_price?: number
}): Promise<{ message: string; step_completed: number; next_step: number | null; is_completed: boolean }> {
  const response = await api.put('/onboarding/wizard/step/4', data)
  return response.data
}

/**
 * Upload tenant logo
 */
export async function uploadLogo(file: File): Promise<{ message: string; logo_url: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/onboarding/wizard/logo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}
