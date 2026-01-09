/**
 * SKU Generation Hook
 *
 * Provides auto-generation of sequential SKUs for various entity types.
 * Returns the next available SKU that can be used as a default value,
 * while still allowing user override.
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { skuApi } from '@/lib/api/sku'
import type { SKUEntityType, NextSKUResponse, SKUAvailabilityResponse } from '@/types/sku'

/**
 * Hook to get the next available SKU for an entity type
 *
 * @param entityType - PROD, MOD, COM, or FIL
 * @param enabled - Whether to fetch (default: true)
 *
 * @example
 * const { nextSKU, isLoading } = useNextSKU('PROD')
 * // nextSKU = "PROD-043" (if PROD-042 is highest)
 */
export function useNextSKU(entityType: SKUEntityType, enabled = true) {
  const query = useQuery<NextSKUResponse>({
    queryKey: ['sku', 'next', entityType],
    queryFn: () => skuApi.getNextSKU(entityType),
    enabled,
    staleTime: 0, // Always refetch to get latest SKU
    refetchOnWindowFocus: false,
  })

  return {
    nextSKU: query.data?.next_sku,
    highestExisting: query.data?.highest_existing ?? 0,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error,
    refetch: query.refetch,
  }
}

/**
 * Hook to check if a SKU is available
 *
 * @param entityType - PROD, MOD, COM, or FIL
 *
 * @example
 * const { checkSKU, isChecking } = useSKUAvailability('PROD')
 * const isAvailable = await checkSKU('PROD-001')
 */
export function useSKUAvailability(entityType: SKUEntityType) {

  const mutation = useMutation<SKUAvailabilityResponse, Error, string>({
    mutationFn: (sku: string) => skuApi.checkAvailability(entityType, sku),
  })

  return {
    checkSKU: mutation.mutateAsync,
    isChecking: mutation.isPending,
    lastResult: mutation.data,
    error: mutation.error,
    reset: mutation.reset,
  }
}

/**
 * Combined hook for SKU generation with availability validation
 *
 * Use this for forms that need both auto-generation and validation.
 *
 * @param entityType - PROD, MOD, COM, or FIL
 *
 * @example
 * const { nextSKU, checkSKU, isLoading } = useSKUWithValidation('PROD')
 *
 * // Auto-fill with next SKU
 * form.setValue('sku', nextSKU)
 *
 * // Later, validate user input
 * const available = await checkSKU(userInput)
 */
export function useSKUWithValidation(entityType: SKUEntityType) {
  const nextSKU = useNextSKU(entityType)
  const availability = useSKUAvailability(entityType)

  return {
    // Next SKU generation
    nextSKU: nextSKU.nextSKU,
    highestExisting: nextSKU.highestExisting,
    isLoadingNextSKU: nextSKU.isLoading,
    refetchNextSKU: nextSKU.refetch,

    // Availability checking
    checkSKU: availability.checkSKU,
    isCheckingSKU: availability.isChecking,

    // Combined loading state
    isLoading: nextSKU.isLoading,
  }
}
