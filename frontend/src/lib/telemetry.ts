/**
 * OpenTelemetry Frontend Instrumentation
 *
 * Provides browser-based tracing for user interactions, API calls, and errors.
 * Sends traces to backend OTLP endpoint for correlation with backend spans.
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { resourceFromAttributes } from '@opentelemetry/resources'
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
} from '@opentelemetry/semantic-conventions'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-web'
import { ZoneContextManager } from '@opentelemetry/context-zone'
import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch'
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction'
import { context, trace, SpanStatusCode, type Span } from '@opentelemetry/api'
import { onCLS, onINP, onLCP, onFCP, onTTFB, type Metric } from 'web-vitals'

// Configuration from environment
const OTEL_ENDPOINT = import.meta.env.VITE_OTEL_ENDPOINT || '/v1/traces'
const SERVICE_NAME = import.meta.env.VITE_SERVICE_NAME || 'batchivo-frontend'
const SERVICE_VERSION = import.meta.env.VITE_SERVICE_VERSION || '1.0.0'

let tracerProvider: WebTracerProvider | null = null
let isInitialized = false

/**
 * Initialize OpenTelemetry instrumentation for the browser.
 * Should be called once at application startup.
 */
export function initTelemetry(): void {
  if (isInitialized) {
    console.warn('Telemetry already initialized')
    return
  }

  try {
    // Create resource with service attributes
    const resource = resourceFromAttributes({
      [ATTR_SERVICE_NAME]: SERVICE_NAME,
      [ATTR_SERVICE_VERSION]: SERVICE_VERSION,
      'deployment.environment': import.meta.env.MODE,
      'browser.user_agent': navigator.userAgent,
      'browser.language': navigator.language,
    })

    // Create OTLP exporter
    const exporter = new OTLPTraceExporter({
      url: OTEL_ENDPOINT,
      headers: {},
    })

    // Create tracer provider
    tracerProvider = new WebTracerProvider({
      resource,
    })

    // Add batch span processor for efficient export
    tracerProvider.addSpanProcessor(
      new BatchSpanProcessor(exporter, {
        maxQueueSize: 100,
        maxExportBatchSize: 10,
        scheduledDelayMillis: 500,
        exportTimeoutMillis: 30000,
      })
    )

    // Register the provider globally
    tracerProvider.register({
      contextManager: new ZoneContextManager(),
    })

    // Register automatic instrumentations
    registerInstrumentations({
      instrumentations: [
        // Auto-instrument fetch/XHR calls
        new FetchInstrumentation({
          propagateTraceHeaderCorsUrls: [
            // Allow trace propagation to same-origin API
            new RegExp(`${window.location.origin}/api/.*`),
            // Allow trace propagation to configured API base URL
            new RegExp(import.meta.env.VITE_API_BASE_URL || ''),
          ],
          clearTimingResources: true,
          applyCustomAttributesOnSpan: (span, request, response) => {
            // Add custom attributes to fetch spans
            if (request instanceof Request) {
              span.setAttribute('http.request.url', request.url)
            }
            if (response) {
              span.setAttribute('http.response.status_code', response.status)
            }
          },
        }),
        // Auto-instrument user interactions (clicks, form submits)
        new UserInteractionInstrumentation({
          eventNames: ['click', 'submit', 'change'],
          shouldPreventSpanCreation: (eventType, element) => {
            // Skip spans for non-interactive elements
            if (eventType === 'click') {
              const tagName = element.tagName.toLowerCase()
              return !['button', 'a', 'input', 'select'].includes(tagName)
            }
            return false
          },
        }),
      ],
    })

    // Initialize web vitals tracking
    initWebVitals()

    isInitialized = true
    console.info('OpenTelemetry initialized for frontend tracing')
  } catch (error) {
    console.error('Failed to initialize OpenTelemetry:', error)
  }
}

/**
 * Get a tracer instance for creating custom spans.
 */
export function getTracer(name = 'batchivo-frontend') {
  return trace.getTracer(name, SERVICE_VERSION)
}

/**
 * Create a custom span for tracking operations.
 * Returns a span that must be ended when the operation completes.
 */
export function startSpan(
  name: string,
  attributes?: Record<string, string | number | boolean>
): Span {
  const tracer = getTracer()
  const span = tracer.startSpan(name)

  if (attributes) {
    Object.entries(attributes).forEach(([key, value]) => {
      span.setAttribute(key, value)
    })
  }

  return span
}

/**
 * Execute a function within a span context.
 * Automatically handles span lifecycle and error recording.
 */
export async function withSpan<T>(
  name: string,
  fn: (span: Span) => Promise<T>,
  attributes?: Record<string, string | number | boolean>
): Promise<T> {
  const tracer = getTracer()
  const span = tracer.startSpan(name)

  if (attributes) {
    Object.entries(attributes).forEach(([key, value]) => {
      span.setAttribute(key, value)
    })
  }

  return context.with(trace.setSpan(context.active(), span), async () => {
    try {
      const result = await fn(span)
      span.setStatus({ code: SpanStatusCode.OK })
      return result
    } catch (error) {
      recordError(span, error)
      throw error
    } finally {
      span.end()
    }
  })
}

/**
 * Record an error on a span.
 */
export function recordError(span: Span, error: unknown): void {
  span.setStatus({
    code: SpanStatusCode.ERROR,
    message: error instanceof Error ? error.message : String(error),
  })

  if (error instanceof Error) {
    span.recordException(error)
  } else {
    span.recordException(new Error(String(error)))
  }
}

/**
 * Record a page view span.
 */
export function recordPageView(path: string, title?: string): void {
  const span = startSpan('page_view', {
    'page.path': path,
    'page.title': title || document.title,
    'page.url': window.location.href,
  })
  span.end()
}

/**
 * Initialize Core Web Vitals tracking.
 * Sends metrics as spans with timing information.
 */
function initWebVitals(): void {
  const handleMetric = (metric: Metric) => {
    const span = startSpan(`web_vital.${metric.name}`, {
      'web_vital.name': metric.name,
      'web_vital.value': metric.value,
      'web_vital.rating': metric.rating,
      'web_vital.id': metric.id,
      'web_vital.navigation_type': metric.navigationType,
    })
    span.end()
  }

  // Track Core Web Vitals
  onCLS(handleMetric) // Cumulative Layout Shift
  onINP(handleMetric) // Interaction to Next Paint (replaced FID)
  onLCP(handleMetric) // Largest Contentful Paint
  onFCP(handleMetric) // First Contentful Paint
  onTTFB(handleMetric) // Time to First Byte
}

/**
 * Shutdown telemetry and flush any pending spans.
 * Call this when the application is unmounting.
 */
export async function shutdownTelemetry(): Promise<void> {
  if (tracerProvider) {
    await tracerProvider.shutdown()
    isInitialized = false
    console.info('OpenTelemetry shutdown complete')
  }
}

// Type declarations for Vite environment variables
declare global {
  interface ImportMetaEnv {
    VITE_OTEL_ENDPOINT?: string
    VITE_SERVICE_NAME?: string
    VITE_SERVICE_VERSION?: string
    VITE_API_BASE_URL?: string
  }
}
