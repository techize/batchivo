/**
 * Modules API - Fetch tenant-specific modules from backend.
 */

import { apiClient } from '../api';
import type { ModulesResponse, Module } from '@/types/modules';

/**
 * Fetch enabled modules for the current tenant.
 *
 * Returns modules filtered by tenant type with their routes and settings.
 */
export async function getModules(): Promise<ModulesResponse> {
  return apiClient.get<ModulesResponse>('/api/v1/modules');
}

/**
 * Get a specific module by name.
 */
export async function getModule(moduleName: string): Promise<Module> {
  return apiClient.get<Module>(`/api/v1/modules/${moduleName}`);
}

/**
 * Update module settings for the current tenant.
 */
export async function updateModuleSettings(
  moduleName: string,
  settings: Record<string, unknown>
): Promise<Module> {
  return apiClient.patch<Module>(`/api/v1/modules/${moduleName}/settings`, settings);
}
