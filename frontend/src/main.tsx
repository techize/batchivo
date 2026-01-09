import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initTelemetry } from '@/lib/telemetry'
import { ErrorBoundary, initGlobalErrorHandlers } from '@/components/ErrorBoundary'

// Initialize OpenTelemetry in production
if (import.meta.env.PROD) {
  initTelemetry()
  initGlobalErrorHandlers()
}

// Also init in dev if explicitly enabled
if (import.meta.env.DEV && import.meta.env.VITE_OTEL_ENABLED === 'true') {
  initTelemetry()
  initGlobalErrorHandlers()
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
