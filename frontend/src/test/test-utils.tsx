import { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create a fresh QueryClient for each test to prevent state leakage
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests
        gcTime: 0, // Garbage collect immediately
        staleTime: 0, // Always stale
      },
      mutations: {
        retry: false,
      },
    },
  })
}

interface WrapperProps {
  children: ReactNode
}

function createWrapper() {
  const queryClient = createTestQueryClient()
  return function Wrapper({ children }: WrapperProps) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

// Custom render with all providers
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: createWrapper(), ...options })
}

// Export all testing-library utilities
// eslint-disable-next-line react-refresh/only-export-components
export * from '@testing-library/react'
export { customRender as render, createTestQueryClient, createWrapper }
