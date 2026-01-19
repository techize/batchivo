/**
 * Model API client
 *
 * Provides TypeScript functions for interacting with the models API endpoints.
 * Models are printed items with BOM (Bill of Materials).
 */

import { apiClient } from '../api'
import { config } from '../config'

// ==================== Types ====================

export interface CostBreakdown {
  material_cost: string
  component_cost: string
  labor_cost: string
  overhead_cost: string
  total_cost: string
}

export interface ModelMaterial {
  id: string
  spool_id: string
  weight_grams: string
  cost_per_gram: string
  created_at: string
  updated_at: string
}

export interface ModelComponent {
  id: string
  component_name: string
  quantity: number
  unit_cost: string
  supplier?: string
  notes?: string
  created_at: string
  updated_at: string
}

// File types for 3D model files
export type ModelFileType = 'source_stl' | 'source_3mf' | 'slicer_project' | 'gcode' | 'plate_layout'

// Where the file is stored
export type FileLocation = 'uploaded' | 'local_reference'

export interface ModelFile {
  id: string
  model_id: string
  file_type: ModelFileType
  file_location: FileLocation
  file_url?: string
  local_path?: string
  local_path_exists?: boolean
  original_filename: string
  file_size?: number
  content_type?: string
  part_name?: string
  version?: string
  is_primary: boolean
  notes?: string
  uploaded_at: string
  uploaded_by_user_id?: string
  created_at: string
  updated_at: string
}

export interface LocalPathValidationResponse {
  path: string
  exists: boolean
  is_file: boolean
  file_size?: number
  filename?: string
}

export interface ModelFileListResponse {
  files: ModelFile[]
  total: number
}

export interface Model {
  id: string
  tenant_id: string
  sku: string
  name: string
  description?: string
  category?: string
  image_url?: string
  labor_hours: string
  labor_rate_override?: string
  overhead_percentage: string
  is_active: boolean
  // Metadata fields
  designer?: string
  source?: string
  print_time_minutes?: number
  prints_per_plate: number
  machine?: string
  last_printed_date?: string
  units_in_stock: number
  created_at: string
  updated_at: string
  // Computed cost (from list endpoint)
  total_cost?: string
  // Production cost tracking (Phase 2)
  actual_production_cost?: string
  production_cost_count: number
  production_cost_updated_at?: string
}

export interface ModelDetail extends Model {
  materials: ModelMaterial[]
  components: ModelComponent[]
  cost_breakdown: CostBreakdown
  files?: ModelFile[]
}

export interface ModelListResponse {
  models: Model[]
  total: number
  skip: number
  limit: number
}

export interface ModelCreateRequest {
  sku: string
  name: string
  description?: string
  category?: string
  image_url?: string
  labor_hours?: string
  labor_rate_override?: string
  overhead_percentage?: string
  designer?: string
  source?: string
  print_time_minutes?: number
  prints_per_plate?: number
  machine?: string
  units_in_stock?: number
}

export interface ModelUpdateRequest {
  sku?: string
  name?: string
  description?: string
  category?: string
  image_url?: string
  labor_hours?: string
  labor_rate_override?: string
  overhead_percentage?: string
  is_active?: boolean
  designer?: string
  source?: string
  print_time_minutes?: number
  prints_per_plate?: number
  machine?: string
  last_printed_date?: string
  units_in_stock?: number
}

export interface ModelMaterialCreateRequest {
  spool_id: string
  weight_grams: string
  cost_per_gram: string
}

export interface ModelComponentCreateRequest {
  component_name: string
  quantity: number
  unit_cost: string
  supplier?: string
  notes?: string
}

export interface ModelListParams {
  skip?: number
  limit?: number
  search?: string
  category?: string
  is_active?: boolean
}

// Production Defaults (for auto-populating production runs)
export interface BOMSpoolSuggestion {
  spool_id: string
  spool_name: string
  material_type_code: string
  color: string
  color_hex?: string
  weight_grams: string
  cost_per_gram: string
  current_weight: string
  is_active: boolean
}

export interface ModelProductionDefaults {
  model_id: string
  sku: string
  name: string
  machine?: string
  print_time_minutes?: number
  prints_per_plate: number
  bom_materials: BOMSpoolSuggestion[]
}

// ==================== API Functions ====================

/**
 * List all models with pagination and filtering
 */
export async function listModels(params?: ModelListParams): Promise<ModelListResponse> {
  const queryParams = new URLSearchParams()

  if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString())
  if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString())
  if (params?.search) queryParams.append('search', params.search)
  if (params?.category) queryParams.append('category', params.category)
  if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString())

  const url = `/api/v1/models${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
  return apiClient.get<ModelListResponse>(url)
}

/**
 * Get a single model by ID with full details (materials, components, cost breakdown)
 */
export async function getModel(modelId: string): Promise<ModelDetail> {
  return apiClient.get<ModelDetail>(`/api/v1/models/${modelId}`)
}

/**
 * Get production defaults for a model (BOM materials with inventory, printer, print time)
 *
 * Used to auto-populate production run creation wizard with suggested materials and settings.
 * Returns model defaults including BOM materials with current spool inventory.
 */
export async function getModelProductionDefaults(modelId: string): Promise<ModelProductionDefaults> {
  return apiClient.get<ModelProductionDefaults>(`/api/v1/models/${modelId}/production-defaults`)
}

/**
 * Create a new model
 */
export async function createModel(data: ModelCreateRequest): Promise<ModelDetail> {
  return apiClient.post<ModelDetail>('/api/v1/models', data)
}

/**
 * Update an existing model
 */
export async function updateModel(modelId: string, data: ModelUpdateRequest): Promise<ModelDetail> {
  return apiClient.put<ModelDetail>(`/api/v1/models/${modelId}`, data)
}

/**
 * Delete a model (soft delete - sets is_active=false)
 */
export async function deleteModel(modelId: string): Promise<void> {
  return apiClient.delete(`/api/v1/models/${modelId}`)
}

// ==================== BOM (Materials) Operations ====================

/**
 * Add a material to model's Bill of Materials
 */
export async function addModelMaterial(
  modelId: string,
  data: ModelMaterialCreateRequest
): Promise<ModelMaterial> {
  return apiClient.post<ModelMaterial>(`/api/v1/models/${modelId}/materials`, data)
}

/**
 * Remove a material from model's BOM
 */
export async function removeModelMaterial(modelId: string, materialId: string): Promise<void> {
  return apiClient.delete(`/api/v1/models/${modelId}/materials/${materialId}`)
}

// ==================== Component Operations ====================

/**
 * Add a component to model (magnets, inserts, etc.)
 */
export async function addModelComponent(
  modelId: string,
  data: ModelComponentCreateRequest
): Promise<ModelComponent> {
  return apiClient.post<ModelComponent>(`/api/v1/models/${modelId}/components`, data)
}

/**
 * Remove a component from model
 */
export async function removeModelComponent(modelId: string, componentId: string): Promise<void> {
  return apiClient.delete(`/api/v1/models/${modelId}/components/${componentId}`)
}

// ==================== Import/Export Operations ====================

export interface ImportModelsResponse {
  success: boolean
  created: number
  updated: number
  skipped: number
  total_rows: number
  errors?: string[]
}

/**
 * Import models from CSV file
 */
export async function importModels(file: File): Promise<ImportModelsResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${config.apiBaseUrl}/api/v1/models/import`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Import failed')
  }

  return response.json()
}

/**
 * Export all models to CSV file
 */
export async function exportModels(): Promise<Blob> {
  const response = await fetch(`${config.apiBaseUrl}/api/v1/models/export`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
    },
  })

  if (!response.ok) {
    throw new Error('Export failed')
  }

  return response.blob()
}

// ==================== Model File Operations ====================

/**
 * Get all files for a model
 */
export async function getModelFiles(modelId: string): Promise<ModelFile[]> {
  const response = await apiClient.get<ModelFileListResponse>(`/api/v1/models/${modelId}/files`)
  return response.files
}

/**
 * Upload a file for a model
 */
export async function uploadModelFile(
  modelId: string,
  file: File,
  fileType: ModelFileType,
  options?: {
    partName?: string
    version?: string
    isPrimary?: boolean
    notes?: string
  }
): Promise<ModelFile> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('file_type', fileType)
  if (options?.partName) formData.append('part_name', options.partName)
  if (options?.version) formData.append('version', options.version)
  if (options?.isPrimary) formData.append('is_primary', 'true')
  if (options?.notes) formData.append('notes', options.notes)

  const response = await fetch(`${config.apiBaseUrl}/api/v1/models/${modelId}/files`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Upload failed')
  }

  const result = await response.json()
  return result.file
}

/**
 * Update file metadata
 */
export async function updateModelFile(
  modelId: string,
  fileId: string,
  data: {
    part_name?: string
    version?: string
    is_primary?: boolean
    notes?: string
  }
): Promise<ModelFile> {
  return apiClient.patch(`/api/v1/models/${modelId}/files/${fileId}`, data)
}

/**
 * Delete a model file
 */
export async function deleteModelFile(modelId: string, fileId: string): Promise<void> {
  return apiClient.delete(`/api/v1/models/${modelId}/files/${fileId}`)
}

/**
 * Get download URL for a file
 */
export function getModelFileDownloadUrl(modelId: string, fileId: string): string {
  return `${config.apiBaseUrl}/api/v1/models/${modelId}/files/${fileId}/download`
}

/**
 * Link a local file to a model (no upload, just store path reference)
 */
export async function linkLocalModelFile(
  modelId: string,
  localPath: string,
  fileType: ModelFileType,
  options?: {
    partName?: string
    version?: string
    isPrimary?: boolean
    notes?: string
  }
): Promise<ModelFile> {
  const response = await apiClient.post<{ file: ModelFile; message: string }>(
    `/api/v1/models/${modelId}/files/link-local`,
    {
      local_path: localPath,
      file_type: fileType,
      part_name: options?.partName,
      version: options?.version,
      is_primary: options?.isPrimary ?? false,
      notes: options?.notes,
    }
  )
  return response.file
}

/**
 * Validate a local file path
 */
export async function validateLocalPath(path: string): Promise<LocalPathValidationResponse> {
  return apiClient.post<LocalPathValidationResponse>('/api/v1/models/validate-local-path', {
    path,
  })
}
