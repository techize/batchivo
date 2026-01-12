/**
 * IndexedDB Database Setup
 *
 * Provides offline-first data storage for inventory management.
 * Uses idb wrapper for cleaner async/await IndexedDB operations.
 */

import { openDB } from 'idb'
import type { DBSchema, IDBPDatabase } from 'idb'
import type { SpoolResponse, MaterialType } from '@/types/spool'

// Database version - increment when schema changes
const DB_VERSION = 1
const DB_NAME = 'batchivo-offline'

// Sync operation types
export type SyncOperation = 'create' | 'update' | 'delete'

// Pending sync record
export interface SyncQueueItem {
  id: string // UUID for the sync item
  entityType: 'spool' | 'material_type'
  entityId: string // ID of the entity being synced
  operation: SyncOperation
  data: unknown // The data to sync (null for deletes)
  createdAt: string // ISO timestamp
  retryCount: number
  lastError?: string
}

// Offline metadata for cached entities
export interface OfflineMetadata {
  lastSynced: string // ISO timestamp
  isStale: boolean
  pendingChanges: boolean
}

// Spool with offline metadata
export interface OfflineSpool extends SpoolResponse {
  _offline?: OfflineMetadata
}

// Database schema definition
interface BatchivoDBSchema extends DBSchema {
  spools: {
    key: string // id
    value: OfflineSpool
    indexes: {
      'by-spool-id': string
      'by-material-type': string
      'by-is-active': number // 0 or 1
      'by-updated-at': string
    }
  }
  materialTypes: {
    key: string // id
    value: MaterialType
    indexes: {
      'by-code': string
    }
  }
  syncQueue: {
    key: string // id
    value: SyncQueueItem
    indexes: {
      'by-entity': [string, string] // [entityType, entityId]
      'by-created-at': string
    }
  }
  metadata: {
    key: string // key name
    value: {
      key: string
      value: unknown
      updatedAt: string
    }
  }
}

// Database instance singleton
let dbInstance: IDBPDatabase<BatchivoDBSchema> | null = null

/**
 * Initialize and return the database instance
 */
export async function getDB(): Promise<IDBPDatabase<BatchivoDBSchema>> {
  if (dbInstance) {
    return dbInstance
  }

  dbInstance = await openDB<BatchivoDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(db, oldVersion) {
      // Handle migrations based on old version
      if (oldVersion < 1) {
        // Spools store
        const spoolStore = db.createObjectStore('spools', { keyPath: 'id' })
        spoolStore.createIndex('by-spool-id', 'spool_id')
        spoolStore.createIndex('by-material-type', 'material_type_id')
        spoolStore.createIndex('by-is-active', 'is_active')
        spoolStore.createIndex('by-updated-at', 'updated_at')

        // Material types store
        const materialStore = db.createObjectStore('materialTypes', { keyPath: 'id' })
        materialStore.createIndex('by-code', 'code')

        // Sync queue store
        const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id' })
        syncStore.createIndex('by-entity', ['entityType', 'entityId'])
        syncStore.createIndex('by-created-at', 'createdAt')

        // Metadata store for app-level data
        db.createObjectStore('metadata', { keyPath: 'key' })
      }
    },
    blocked() {
      console.warn('IndexedDB upgrade blocked - close other tabs')
    },
    blocking() {
      // Close connection when a newer version wants to upgrade
      dbInstance?.close()
      dbInstance = null
    },
  })

  return dbInstance
}

// ============================================================================
// Spool Operations
// ============================================================================

/**
 * Get all cached spools
 */
export async function getAllSpools(): Promise<OfflineSpool[]> {
  const db = await getDB()
  return db.getAll('spools')
}

/**
 * Get spools with filtering (client-side)
 */
export async function getSpools(params?: {
  isActive?: boolean
  materialTypeId?: string
  search?: string
}): Promise<OfflineSpool[]> {
  const db = await getDB()
  let spools = await db.getAll('spools')

  if (params?.isActive !== undefined) {
    spools = spools.filter((s) => s.is_active === params.isActive)
  }

  if (params?.materialTypeId) {
    spools = spools.filter((s) => s.material_type_id === params.materialTypeId)
  }

  if (params?.search) {
    const searchLower = params.search.toLowerCase()
    spools = spools.filter(
      (s) =>
        s.spool_id.toLowerCase().includes(searchLower) ||
        s.brand.toLowerCase().includes(searchLower) ||
        s.color.toLowerCase().includes(searchLower) ||
        s.material_type_name.toLowerCase().includes(searchLower)
    )
  }

  return spools
}

/**
 * Get a single spool by ID
 */
export async function getSpool(id: string): Promise<OfflineSpool | undefined> {
  const db = await getDB()
  return db.get('spools', id)
}

/**
 * Save a spool to the cache
 */
export async function saveSpool(spool: OfflineSpool): Promise<void> {
  const db = await getDB()
  await db.put('spools', {
    ...spool,
    _offline: {
      lastSynced: new Date().toISOString(),
      isStale: false,
      pendingChanges: false,
    },
  })
}

/**
 * Save multiple spools to the cache
 */
export async function saveSpools(spools: SpoolResponse[]): Promise<void> {
  const db = await getDB()
  const tx = db.transaction('spools', 'readwrite')
  const now = new Date().toISOString()

  await Promise.all([
    ...spools.map((spool) =>
      tx.store.put({
        ...spool,
        _offline: {
          lastSynced: now,
          isStale: false,
          pendingChanges: false,
        },
      })
    ),
    tx.done,
  ])
}

/**
 * Delete a spool from the cache
 */
export async function deleteSpool(id: string): Promise<void> {
  const db = await getDB()
  await db.delete('spools', id)
}

/**
 * Clear all cached spools
 */
export async function clearSpools(): Promise<void> {
  const db = await getDB()
  await db.clear('spools')
}

// ============================================================================
// Material Type Operations
// ============================================================================

/**
 * Get all cached material types
 */
export async function getAllMaterialTypes(): Promise<MaterialType[]> {
  const db = await getDB()
  return db.getAll('materialTypes')
}

/**
 * Save material types to the cache
 */
export async function saveMaterialTypes(types: MaterialType[]): Promise<void> {
  const db = await getDB()
  const tx = db.transaction('materialTypes', 'readwrite')

  await Promise.all([...types.map((type) => tx.store.put(type)), tx.done])
}

// ============================================================================
// Sync Queue Operations
// ============================================================================

/**
 * Add an item to the sync queue
 */
export async function addToSyncQueue(
  entityType: SyncQueueItem['entityType'],
  entityId: string,
  operation: SyncOperation,
  data: unknown
): Promise<void> {
  const db = await getDB()

  // Check if there's already a pending operation for this entity
  const existing = await db.getFromIndex('syncQueue', 'by-entity', [entityType, entityId])

  if (existing) {
    // Update existing queue item
    if (operation === 'delete') {
      // If deleting, remove any pending creates/updates
      if (existing.operation === 'create') {
        // Was created offline, just remove from queue entirely
        await db.delete('syncQueue', existing.id)
        return
      }
      // Update to delete operation
      await db.put('syncQueue', {
        ...existing,
        operation: 'delete',
        data: null,
      })
    } else {
      // Merge update data
      await db.put('syncQueue', {
        ...existing,
        data: { ...(existing.data as object), ...(data as object) },
      })
    }
  } else {
    // Add new queue item
    const item: SyncQueueItem = {
      id: crypto.randomUUID(),
      entityType,
      entityId,
      operation,
      data,
      createdAt: new Date().toISOString(),
      retryCount: 0,
    }
    await db.add('syncQueue', item)
  }
}

/**
 * Get all pending sync items
 */
export async function getSyncQueue(): Promise<SyncQueueItem[]> {
  const db = await getDB()
  return db.getAllFromIndex('syncQueue', 'by-created-at')
}

/**
 * Get pending sync count
 */
export async function getSyncQueueCount(): Promise<number> {
  const db = await getDB()
  return db.count('syncQueue')
}

/**
 * Remove an item from the sync queue
 */
export async function removeFromSyncQueue(id: string): Promise<void> {
  const db = await getDB()
  await db.delete('syncQueue', id)
}

/**
 * Update sync item retry count and error
 */
export async function updateSyncItemError(id: string, error: string): Promise<void> {
  const db = await getDB()
  const item = await db.get('syncQueue', id)
  if (item) {
    await db.put('syncQueue', {
      ...item,
      retryCount: item.retryCount + 1,
      lastError: error,
    })
  }
}

/**
 * Clear the entire sync queue
 */
export async function clearSyncQueue(): Promise<void> {
  const db = await getDB()
  await db.clear('syncQueue')
}

// ============================================================================
// Metadata Operations
// ============================================================================

/**
 * Get a metadata value
 */
export async function getMetadata<T>(key: string): Promise<T | undefined> {
  const db = await getDB()
  const record = await db.get('metadata', key)
  return record?.value as T | undefined
}

/**
 * Set a metadata value
 */
export async function setMetadata(key: string, value: unknown): Promise<void> {
  const db = await getDB()
  await db.put('metadata', {
    key,
    value,
    updatedAt: new Date().toISOString(),
  })
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Check if IndexedDB is available
 */
export function isIndexedDBAvailable(): boolean {
  try {
    return typeof indexedDB !== 'undefined' && indexedDB !== null
  } catch {
    return false
  }
}

/**
 * Get the total size of cached data (approximate)
 */
export async function getCacheSize(): Promise<{
  spools: number
  materialTypes: number
  syncQueue: number
}> {
  const db = await getDB()
  return {
    spools: await db.count('spools'),
    materialTypes: await db.count('materialTypes'),
    syncQueue: await db.count('syncQueue'),
  }
}

/**
 * Clear all offline data
 */
export async function clearAllOfflineData(): Promise<void> {
  const db = await getDB()
  await Promise.all([
    db.clear('spools'),
    db.clear('materialTypes'),
    db.clear('syncQueue'),
    db.clear('metadata'),
  ])
}
