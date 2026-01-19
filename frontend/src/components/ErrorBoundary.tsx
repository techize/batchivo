/**
 * Error Boundary Component
 *
 * Catches React errors and records them as OpenTelemetry spans.
 * Also captures errors to Sentry for error monitoring.
 * Handles unhandled promise rejections.
 */

import { Component, type ReactNode } from 'react'
import { startSpan, recordError } from '@/lib/telemetry'
import { captureException } from '@/lib/sentry'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

/**
 * Error Boundary that records errors as OpenTelemetry spans.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Record error in OpenTelemetry span
    const span = startSpan('react_error', {
      'error.type': 'react_error_boundary',
      'error.message': error.message,
      'error.name': error.name,
      'error.component_stack': errorInfo.componentStack || '',
    })
    recordError(span, error)
    span.end()

    // Capture error in Sentry with component stack
    captureException(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    })

    // Update state with error info
    this.setState({ errorInfo })

    // Call optional error handler
    this.props.onError?.(error, errorInfo)

    // Log to console in development
    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught error:', error, errorInfo)
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  handleGoHome = (): void => {
    window.location.href = '/dashboard'
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <Card className="max-w-lg w-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-6 h-6" />
                Something went wrong
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                An unexpected error occurred. Our team has been notified and is working
                on a fix.
              </p>

              {import.meta.env.DEV && this.state.error && (
                <div className="bg-muted rounded-md p-4 overflow-auto">
                  <p className="font-mono text-sm text-destructive">
                    {this.state.error.message}
                  </p>
                  {this.state.errorInfo?.componentStack && (
                    <pre className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              )}

              <div className="flex gap-3">
                <Button variant="outline" onClick={this.handleReset}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Try Again
                </Button>
                <Button onClick={this.handleGoHome}>
                  <Home className="w-4 h-4 mr-2" />
                  Go to Dashboard
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * Initialize global error handlers for unhandled errors.
 * Call this once at application startup.
 */
export function initGlobalErrorHandlers(): void {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason))

    const span = startSpan('unhandled_rejection', {
      'error.type': 'unhandled_promise_rejection',
      'error.message': error.message,
      'error.name': error.name,
    })
    recordError(span, error)
    span.end()

    // Also capture in Sentry
    captureException(error, {
      type: 'unhandled_promise_rejection',
    })

    if (import.meta.env.DEV) {
      console.error('Unhandled promise rejection:', event.reason)
    }
  })

  // Handle uncaught errors
  window.addEventListener('error', (event) => {
    const span = startSpan('uncaught_error', {
      'error.type': 'uncaught_error',
      'error.message': event.message,
      'error.filename': event.filename || '',
      'error.lineno': event.lineno || 0,
      'error.colno': event.colno || 0,
    })

    if (event.error) {
      recordError(span, event.error)
      // Also capture in Sentry
      captureException(event.error, {
        type: 'uncaught_error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      })
    }
    span.end()

    if (import.meta.env.DEV) {
      console.error('Uncaught error:', event.error)
    }
  })
}
