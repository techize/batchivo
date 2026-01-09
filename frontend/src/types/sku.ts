/**
 * SKU-related types for the frontend
 */

/** Entity types that support SKU generation */
export type SKUEntityType = 'PROD' | 'MOD' | 'COM' | 'FIL';

/** Response from the next SKU endpoint */
export interface NextSKUResponse {
  entity_type: SKUEntityType;
  next_sku: string;
  highest_existing: number;
}

/** Response from the SKU availability check endpoint */
export interface SKUAvailabilityResponse {
  sku: string;
  available: boolean;
}
