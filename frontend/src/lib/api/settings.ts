/**
 * Settings API client
 *
 * Provides TypeScript functions for interacting with the settings API endpoints.
 * Handles Square payment configuration and tenant management.
 */

import { apiClient } from '../api'

// ==================== Types ====================

// Square Settings
export interface SquareSettings {
  enabled: boolean
  environment: 'sandbox' | 'production'
  is_configured: boolean
  access_token_masked: string | null
  app_id: string | null
  location_id_masked: string | null
  updated_at: string | null
}

export interface SquareSettingsUpdate {
  enabled?: boolean
  environment?: 'sandbox' | 'production'
  access_token?: string
  app_id?: string
  location_id?: string
}

export interface SquareConnectionTest {
  success: boolean
  message: string
  environment: string | null
  location_name: string | null
}

// Tenant Settings
export interface Tenant {
  id: string
  name: string
  slug: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TenantUpdate {
  name?: string
  description?: string
}

// Tenant Members
export type UserRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface TenantMember {
  id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  joined_at: string
}

export interface TenantMemberListResponse {
  members: TenantMember[]
  total: number
}

export interface TenantMemberInvite {
  email: string
  role?: UserRole
}

export interface TenantMemberRoleUpdate {
  role: UserRole
}

// ==================== Square Settings API ====================

/**
 * Get Square payment settings
 */
export async function getSquareSettings(): Promise<SquareSettings> {
  return apiClient.get<SquareSettings>('/api/v1/settings/square')
}

/**
 * Update Square payment settings
 */
export async function updateSquareSettings(data: SquareSettingsUpdate): Promise<SquareSettings> {
  return apiClient.put<SquareSettings>('/api/v1/settings/square', data)
}

/**
 * Test Square connection with current credentials
 */
export async function testSquareConnection(): Promise<SquareConnectionTest> {
  return apiClient.post<SquareConnectionTest>('/api/v1/settings/square/test', {})
}

// ==================== Tenant Settings API ====================

/**
 * Get tenant details
 */
export async function getTenant(): Promise<Tenant> {
  return apiClient.get<Tenant>('/api/v1/settings/tenant')
}

/**
 * Update tenant details
 */
export async function updateTenant(data: TenantUpdate): Promise<Tenant> {
  return apiClient.put<Tenant>('/api/v1/settings/tenant', data)
}

// ==================== Tenant Members API ====================

/**
 * List all members of the current tenant
 */
export async function listTenantMembers(): Promise<TenantMemberListResponse> {
  return apiClient.get<TenantMemberListResponse>('/api/v1/tenant/members')
}

/**
 * Invite a user to the tenant
 */
export async function inviteTenantMember(data: TenantMemberInvite): Promise<TenantMember> {
  return apiClient.post<TenantMember>('/api/v1/tenant/members/invite', data)
}

/**
 * Update a member's role
 */
export async function updateMemberRole(memberId: string, data: TenantMemberRoleUpdate): Promise<TenantMember> {
  return apiClient.put<TenantMember>(`/api/v1/tenant/members/${memberId}`, data)
}

/**
 * Remove a member from the tenant
 */
export async function removeTenantMember(memberId: string): Promise<void> {
  return apiClient.delete(`/api/v1/tenant/members/${memberId}`)
}
