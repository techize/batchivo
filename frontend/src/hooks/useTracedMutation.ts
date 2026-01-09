/**
 * useTracedMutation Hook
 *
 * Wraps React Query's useMutation with OpenTelemetry tracing.
 * Automatically creates spans for mutation operations.
 */

import {
  useMutation,
  type UseMutationOptions,
  type UseMutationResult,
} from '@tanstack/react-query'
import { withSpan, recordError, getTracer } from '@/lib/telemetry'
import { SpanStatusCode } from '@opentelemetry/api'

interface TracedMutationOptions<TData, TError, TVariables, TContext>
  extends UseMutationOptions<TData, TError, TVariables, TContext> {
  /**
   * Name for the span (e.g., 'createSpool', 'updateWeight')
   */
  spanName: string
  /**
   * Function to extract span attributes from variables
   */
  getSpanAttributes?: (
    variables: TVariables
  ) => Record<string, string | number | boolean>
}

/**
 * A wrapper around useMutation that adds OpenTelemetry tracing.
 *
 * @example
 * ```tsx
 * const mutation = useTracedMutation({
 *   spanName: 'createSpool',
 *   mutationFn: (data) => api.createSpool(data),
 *   getSpanAttributes: (data) => ({
 *     'spool.material': data.material,
 *     'spool.color': data.color,
 *   }),
 * })
 * ```
 */
export function useTracedMutation<
  TData = unknown,
  TError = Error,
  TVariables = void,
  TContext = unknown,
>(
  options: TracedMutationOptions<TData, TError, TVariables, TContext>
): UseMutationResult<TData, TError, TVariables, TContext> {
  const { spanName, getSpanAttributes, mutationFn, onSuccess, onError, ...rest } =
    options

  const tracedMutationFn = async (variables: TVariables): Promise<TData> => {
    const attributes = getSpanAttributes ? getSpanAttributes(variables) : {}

    return withSpan(
      `mutation.${spanName}`,
      async (span) => {
        // Add mutation name as attribute
        span.setAttribute('mutation.name', spanName)

        // Execute the actual mutation
        const result = await mutationFn!(variables)

        // Add result attributes if available
        if (result && typeof result === 'object' && 'id' in result) {
          span.setAttribute('mutation.result_id', String((result as { id: unknown }).id))
        }

        return result
      },
      attributes
    )
  }

  return useMutation({
    ...rest,
    mutationFn: mutationFn ? tracedMutationFn : undefined,
    onSuccess: (data, variables, context) => {
      // Record success metric
      const tracer = getTracer()
      const span = tracer.startSpan(`mutation.${spanName}.success`)
      span.setStatus({ code: SpanStatusCode.OK })
      span.end()

      onSuccess?.(data, variables, context)
    },
    onError: (error, variables, context) => {
      // Record error in a span
      const tracer = getTracer()
      const span = tracer.startSpan(`mutation.${spanName}.error`)
      recordError(span, error)
      span.end()

      onError?.(error, variables, context)
    },
  })
}

/**
 * Pre-configured traced mutations for common operations
 */

// Create Spool mutation wrapper
export function useCreateSpoolMutation<TData, TError = Error>(
  options: Omit<
    TracedMutationOptions<TData, TError, { material?: string; color?: string }, unknown>,
    'spanName' | 'getSpanAttributes'
  >
) {
  return useTracedMutation({
    ...options,
    spanName: 'createSpool',
    getSpanAttributes: (variables) => ({
      'spool.material': variables.material || 'unknown',
      'spool.color': variables.color || 'unknown',
    }),
  })
}

// Update Weight mutation wrapper
export function useUpdateWeightMutation<TData, TError = Error>(
  options: Omit<
    TracedMutationOptions<
      TData,
      TError,
      { spoolId: string; newWeight: number },
      unknown
    >,
    'spanName' | 'getSpanAttributes'
  >
) {
  return useTracedMutation({
    ...options,
    spanName: 'updateWeight',
    getSpanAttributes: (variables) => ({
      'spool.id': variables.spoolId,
      'spool.new_weight': variables.newWeight,
    }),
  })
}

// Complete Production Run mutation wrapper
export function useCompleteProductionRunMutation<TData, TError = Error>(
  options: Omit<
    TracedMutationOptions<
      TData,
      TError,
      { runId: string; quantity?: number },
      unknown
    >,
    'spanName' | 'getSpanAttributes'
  >
) {
  return useTracedMutation({
    ...options,
    spanName: 'completeProductionRun',
    getSpanAttributes: (variables) => ({
      'production_run.id': variables.runId,
      'production_run.quantity': variables.quantity || 0,
    }),
  })
}
