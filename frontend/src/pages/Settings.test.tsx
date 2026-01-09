/**
 * Tests for Settings page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Settings } from './Settings'
import * as settingsApi from '@/lib/api/settings'
import * as ordersApi from '@/lib/api/orders'

// Mock the APIs
vi.mock('@/lib/api/settings', () => ({
  getTenant: vi.fn(),
  updateTenant: vi.fn(),
  getSquareSettings: vi.fn(),
  updateSquareSettings: vi.fn(),
  testSquareConnection: vi.fn(),
  listTenantMembers: vi.fn(),
  inviteTenantMember: vi.fn(),
  updateMemberRole: vi.fn(),
  removeTenantMember: vi.fn(),
}))

vi.mock('@/lib/api/orders', () => ({
  getOrderCounts: vi.fn(),
}))

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'test@example.com' },
    logout: vi.fn(),
  }),
}))

const mockTenant = {
  id: 'tenant-123',
  name: 'Test Organization',
  slug: 'test-org',
  description: 'A test organization',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockSquareSettings = {
  enabled: false,
  environment: 'sandbox' as const,
  is_configured: false,
  access_token_masked: null,
  app_id: null,
  location_id_masked: null,
  updated_at: null,
}

const mockMembers = {
  members: [
    {
      id: 'user-1',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'owner' as const,
      is_active: true,
      joined_at: '2024-01-01T00:00:00Z',
    },
  ],
  total: 1,
}

function renderWithQueryClient(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(settingsApi.getTenant).mockResolvedValue(mockTenant)
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSquareSettings)
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue(mockMembers)
    vi.mocked(ordersApi.getOrderCounts).mockResolvedValue({
      pending: 0,
      processing: 0,
      shipped: 0,
      completed: 0,
      cancelled: 0,
    })
  })

  it('renders page title and description', async () => {
    renderWithQueryClient(<Settings />)

    // Use heading role for the main title
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(
      screen.getByText('Manage your organization settings and integrations')
    ).toBeInTheDocument()
  })

  it('renders all three tabs', async () => {
    renderWithQueryClient(<Settings />)

    expect(screen.getByRole('tab', { name: /general/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /payments/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /team/i })).toBeInTheDocument()
  })

  it('shows General tab content by default', async () => {
    renderWithQueryClient(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Organization Details')).toBeInTheDocument()
    })
  })

  it('switches to Payments tab when clicked', async () => {
    const user = userEvent.setup()

    renderWithQueryClient(<Settings />)

    await user.click(screen.getByRole('tab', { name: /payments/i }))

    await waitFor(() => {
      expect(screen.getByText('Square Payments')).toBeInTheDocument()
    })
  })

  it('switches to Team tab when clicked', async () => {
    const user = userEvent.setup()

    renderWithQueryClient(<Settings />)

    await user.click(screen.getByRole('tab', { name: /team/i }))

    await waitFor(() => {
      expect(screen.getByText('Team Members')).toBeInTheDocument()
    })
  })

  it('loads data for General tab on mount', async () => {
    renderWithQueryClient(<Settings />)

    await waitFor(() => {
      expect(settingsApi.getTenant).toHaveBeenCalled()
    })
  })

  it('loads Square settings when Payments tab is shown', async () => {
    const user = userEvent.setup()

    renderWithQueryClient(<Settings />)

    await user.click(screen.getByRole('tab', { name: /payments/i }))

    await waitFor(() => {
      expect(settingsApi.getSquareSettings).toHaveBeenCalled()
    })
  })

  it('loads team members when Team tab is shown', async () => {
    const user = userEvent.setup()

    renderWithQueryClient(<Settings />)

    await user.click(screen.getByRole('tab', { name: /team/i }))

    await waitFor(() => {
      expect(settingsApi.listTenantMembers).toHaveBeenCalled()
    })
  })
})
