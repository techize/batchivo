/**
 * TanStack Query hooks for the FilamentType domain.
 * Covers aggregated list, per-type spool sheet, and the has_sample optimistic toggle.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { filamentTypesApi } from '@/lib/api/filament-types'
import type {
  FilamentTypeAggregatedListResponse,
  FilamentTypeListParams,
} from '@/types/filament-type'

/**
 * Fetch the paginated, aggregated filament type list.
 */
export function useFilamentTypes(params: FilamentTypeListParams = {}) {
  return useQuery<FilamentTypeAggregatedListResponse>({
    queryKey: ['filament-types', params],
    queryFn: () => filamentTypesApi.list(params),
  })
}

/**
 * Fetch all spools belonging to a specific filament type.
 * Query is disabled until a non-null filamentTypeId is supplied (sheet-open guard).
 */
export function useFilamentTypeSpools(filamentTypeId: string | null) {
  return useQuery({
    queryKey: ['filament-type-spools', filamentTypeId],
    queryFn: () => filamentTypesApi.getSpools(filamentTypeId!),
    enabled: filamentTypeId !== null,
  })
}

/**
 * Optimistic toggle for the has_sample flag on a filament type.
 *
 * Lifecycle:
 *  onMutate  — cancel in-flight queries, snapshot current data, apply optimistic update
 *  onError   — roll back to snapshot
 *  onSettled — invalidate so the cache is refreshed from the server
 */
export function useToggleHasSample(params: FilamentTypeListParams = {}) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, hasSample }: { id: string; hasSample: boolean }) =>
      filamentTypesApi.update(id, { has_sample: hasSample }),

    onMutate: async ({ id, hasSample }) => {
      // Cancel any outgoing refetches so they don't overwrite the optimistic update
      await queryClient.cancelQueries({ queryKey: ['filament-types'] })

      // Snapshot the previous value for rollback
      const previous = queryClient.getQueryData<FilamentTypeAggregatedListResponse>([
        'filament-types',
        params,
      ])

      // Optimistically update the cache
      queryClient.setQueryData<FilamentTypeAggregatedListResponse>(
        ['filament-types', params],
        (old) => {
          if (!old) return old
          return {
            ...old,
            filament_types: old.filament_types.map((ft) =>
              ft.id === id ? { ...ft, has_sample: hasSample } : ft
            ),
          }
        }
      )

      return { previous }
    },

    onError: (_err, _vars, context) => {
      // Restore snapshot on error
      if (context?.previous) {
        queryClient.setQueryData(['filament-types', params], context.previous)
      }
    },

    onSettled: () => {
      // Always re-sync from the server after mutation
      queryClient.invalidateQueries({ queryKey: ['filament-types'] })
    },
  })
}
