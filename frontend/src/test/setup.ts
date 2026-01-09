import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock @tanstack/react-router to avoid router context requirements
vi.mock('@tanstack/react-router', async () => {
  const actual = await vi.importActual('@tanstack/react-router')
  const React = await import('react')
  return {
    ...actual,
    Link: React.forwardRef(({ children, to, ...props }: { children?: React.ReactNode; to?: string | object; [key: string]: unknown }, ref: React.Ref<HTMLAnchorElement>) =>
      React.createElement('a', { href: typeof to === 'string' ? to : '#', ref, ...props }, children)
    ),
    useNavigate: () => vi.fn(),
    useRouter: () => ({
      navigate: vi.fn(),
      state: {
        location: { pathname: '/settings' },
        matches: [],
        isLoading: false,
      },
    }),
    useRouterState: () => ({
      location: { pathname: '/settings' },
      matches: [],
      isLoading: false,
    }),
  }
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

// Mock scrollTo and scrollIntoView
window.scrollTo = vi.fn()
Element.prototype.scrollIntoView = vi.fn()

// Mock pointer capture APIs (needed for Radix UI)
Element.prototype.hasPointerCapture = vi.fn().mockReturnValue(false)
Element.prototype.setPointerCapture = vi.fn()
Element.prototype.releasePointerCapture = vi.fn()

// Mock crypto.randomUUID (used by some UI components)
Object.defineProperty(globalThis, 'crypto', {
  value: {
    randomUUID: () => Math.random().toString(36).substring(2),
  },
})
