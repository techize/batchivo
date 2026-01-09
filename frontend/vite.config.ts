import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      // Enable source maps for error tracking in production
      sourcemap: mode === 'production' ? 'hidden' : true,
      rollupOptions: {
        output: {
          // Code splitting for better caching
          manualChunks: {
            // Core React - rarely changes
            'vendor-react': ['react', 'react-dom'],
            // Routing & data fetching
            'vendor-router': ['@tanstack/react-router', '@tanstack/react-query'],
            // UI components (Radix)
            'vendor-ui': [
              '@radix-ui/react-dialog',
              '@radix-ui/react-select',
              '@radix-ui/react-popover',
              '@radix-ui/react-dropdown-menu',
              '@radix-ui/react-alert-dialog',
              '@radix-ui/react-tabs',
            ],
            // Charts - only needed on dashboard
            'vendor-charts': ['recharts'],
            // Rich text editor - only needed on edit pages
            'vendor-editor': ['@tiptap/react', '@tiptap/starter-kit', '@tiptap/extension-link', '@tiptap/extension-placeholder'],
            // OpenTelemetry - observability (all packages together to avoid bundling issues)
            'vendor-otel': [
              '@opentelemetry/api',
              '@opentelemetry/sdk-trace-web',
              '@opentelemetry/exporter-trace-otlp-http',
              '@opentelemetry/resources',
              '@opentelemetry/context-zone',
              '@opentelemetry/instrumentation',
              '@opentelemetry/instrumentation-fetch',
              '@opentelemetry/instrumentation-user-interaction',
              '@opentelemetry/semantic-conventions',
            ],
          },
        },
      },
    },
    server: {
      port: 5173,
      proxy: {
        // Proxy API requests to backend during development
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: true,
        },
        // Proxy OTLP traces to backend
        '/v1/traces': {
          target: apiTarget,
          changeOrigin: true,
          secure: true,
        },
      },
    },
    // Force pre-bundling of OpenTelemetry packages to avoid ESM/CJS issues
    optimizeDeps: {
      include: [
        '@opentelemetry/api',
        '@opentelemetry/sdk-trace-web',
        '@opentelemetry/exporter-trace-otlp-http',
        '@opentelemetry/resources',
        '@opentelemetry/context-zone',
        '@opentelemetry/instrumentation',
        '@opentelemetry/instrumentation-fetch',
        '@opentelemetry/instrumentation-user-interaction',
        '@opentelemetry/semantic-conventions',
        '@opentelemetry/core',
        '@opentelemetry/sdk-trace-base',
      ],
    },
    // Environment variables exposed to client
    define: {
      // Make package version available at runtime
      '__APP_VERSION__': JSON.stringify(process.env.npm_package_version || '0.0.0'),
    },
  }
})
