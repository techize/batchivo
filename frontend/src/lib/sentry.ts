/**
 * Sentry Error Monitoring for Batchivo Frontend
 *
 * Provides error tracking, performance monitoring, and session replay
 * with proper integration into React and the existing ErrorBoundary.
 */

import * as Sentry from '@sentry/react'
import { config } from './config'

let isInitialized = false

/**
 * Get git commit hash for release tracking.
 * This is set at build time by the Vite plugin.
 */
function getRelease(): string {
  // __SENTRY_RELEASE__ is injected by @sentry/vite-plugin
  // Falls back to app version if not available
  return (
    (typeof __SENTRY_RELEASE__ !== 'undefined' ? __SENTRY_RELEASE__ : null) ||
    `batchivo-frontend@${config.serviceVersion}`
  )
}

/**
 * Initialize Sentry error monitoring.
 * Should be called once at application startup, before React renders.
 *
 * @returns true if Sentry was initialized, false if skipped
 */
export function initSentry(): boolean {
  if (isInitialized) {
    console.warn('Sentry already initialized')
    return true
  }

  // Skip if no DSN configured
  if (!config.sentryDsn) {
    console.info('Sentry DSN not configured, skipping initialization')
    return false
  }

  try {
    // Configure sample rates based on environment
    const tracesSampleRate = config.isDev ? 1.0 : 0.1
    const replaysSessionSampleRate = config.isDev ? 1.0 : 0.1
    const replaysOnErrorSampleRate = 1.0 // Always capture replay on error

    Sentry.init({
      dsn: config.sentryDsn,
      environment: config.mode,
      release: getRelease(),

      // Performance Monitoring
      tracesSampleRate,

      // Session Replay
      replaysSessionSampleRate,
      replaysOnErrorSampleRate,

      // Integrations
      integrations: [
        // Browser tracing for performance
        Sentry.browserTracingIntegration({
          // Trace navigation and API calls
          tracePropagationTargets: [
            'localhost',
            /^https:\/\/.*\.batchivo\.com/,
            /^\/api\//,
          ],
        }),
        // Session replay for debugging
        Sentry.replayIntegration({
          // Mask all text and block all media for privacy in production
          maskAllText: config.isProd,
          blockAllMedia: config.isProd,
        }),
      ],

      // Filter events before sending
      beforeSend(event, hint) {
        // Don't send events in development unless explicitly enabled
        if (config.isDev && !import.meta.env.VITE_SENTRY_DEV_ENABLED) {
          console.debug('Sentry event (dev mode, not sent):', event)
          return null
        }

        // Filter out non-error events for common issues
        const error = hint.originalException
        if (error instanceof Error) {
          // Don't report network errors (handled by error boundaries)
          if (
            error.message.includes('Network request failed') ||
            error.message.includes('Failed to fetch')
          ) {
            return null
          }

          // Don't report ResizeObserver errors (browser quirk)
          if (error.message.includes('ResizeObserver')) {
            return null
          }
        }

        return event
      },

      // Filter breadcrumbs
      beforeBreadcrumb(breadcrumb) {
        // Don't log console breadcrumbs in production
        if (config.isProd && breadcrumb.category === 'console') {
          return null
        }
        return breadcrumb
      },

      // Additional options
      sendDefaultPii: config.isDev, // Only send PII in development
      attachStacktrace: true,
      autoSessionTracking: true,
    })

    // Set initial tags
    Sentry.setTag('app.name', 'batchivo-frontend')
    Sentry.setTag('app.version', config.serviceVersion)

    isInitialized = true
    console.info(`Sentry initialized (env=${config.mode}, release=${getRelease()})`)
    return true
  } catch (error) {
    console.error('Failed to initialize Sentry:', error)
    return false
  }
}

/**
 * Set user context for Sentry events.
 * Call when user logs in.
 */
export function setUser(user: {
  id: string
  email?: string
  username?: string
  tenantId?: string
}): void {
  Sentry.setUser({
    id: user.id,
    email: user.email,
    username: user.username,
  })

  if (user.tenantId) {
    Sentry.setTag('tenant.id', user.tenantId)
  }
}

/**
 * Clear user context.
 * Call when user logs out.
 */
export function clearUser(): void {
  Sentry.setUser(null)
}

/**
 * Capture an exception manually.
 */
export function captureException(
  error: Error | unknown,
  context?: Record<string, unknown>
): string | undefined {
  return Sentry.captureException(error, {
    extra: context,
  })
}

/**
 * Capture a message manually.
 */
export function captureMessage(
  message: string,
  level: 'fatal' | 'error' | 'warning' | 'info' | 'debug' = 'info',
  context?: Record<string, unknown>
): string | undefined {
  return Sentry.captureMessage(message, {
    level,
    extra: context,
  })
}

/**
 * Add breadcrumb for debugging.
 */
export function addBreadcrumb(
  message: string,
  category: string,
  level: 'fatal' | 'error' | 'warning' | 'info' | 'debug' = 'info',
  data?: Record<string, unknown>
): void {
  Sentry.addBreadcrumb({
    message,
    category,
    level,
    data,
  })
}

/**
 * Create a span for performance monitoring.
 */
export function startSpan<T>(
  name: string,
  callback: () => T | Promise<T>,
  options?: {
    op?: string
    description?: string
    attributes?: Record<string, string | number | boolean>
  }
): T | Promise<T> {
  return Sentry.startSpan(
    {
      name,
      op: options?.op || 'function',
      attributes: options?.attributes,
    },
    callback
  )
}

// Re-export ErrorBoundary from Sentry for use in App
export const SentryErrorBoundary = Sentry.ErrorBoundary

// Declare global for release injection
declare global {
  const __SENTRY_RELEASE__: string | undefined
}
