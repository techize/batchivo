/**
 * Tests for TeamSettings component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TeamSettings } from './TeamSettings'
import * as settingsApi from '@/lib/api/settings'

// Mock the settings API
vi.mock('@/lib/api/settings', () => ({
  listTenantMembers: vi.fn(),
  inviteTenantMember: vi.fn(),
  updateMemberRole: vi.fn(),
  removeTenantMember: vi.fn(),
}))

const mockMembers = {
  members: [
    {
      id: 'user-1',
      email: 'owner@example.com',
      full_name: 'Owner User',
      role: 'owner' as const,
      is_active: true,
      joined_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'user-2',
      email: 'admin@example.com',
      full_name: 'Admin User',
      role: 'admin' as const,
      is_active: true,
      joined_at: '2024-01-15T00:00:00Z',
    },
    {
      id: 'user-3',
      email: 'member@example.com',
      full_name: null,
      role: 'member' as const,
      is_active: true,
      joined_at: '2024-02-01T00:00:00Z',
    },
  ],
  total: 3,
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

describe('TeamSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(settingsApi.listTenantMembers).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    renderWithQueryClient(<TeamSettings />)

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('displays team members when loaded', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue(mockMembers)

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(screen.getByText('Team Members')).toBeInTheDocument()
    })

    expect(screen.getByText('Owner User')).toBeInTheDocument()
    expect(screen.getByText('Admin User')).toBeInTheDocument()
    // Member without full_name shows email - use getAllByText since email appears twice
    expect(screen.getAllByText('member@example.com').length).toBeGreaterThanOrEqual(1)
  })

  it('shows error state when API fails', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockRejectedValue(new Error('API Error'))

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument()
    })

    expect(screen.getByText('Failed to load team members')).toBeInTheDocument()
  })

  it('displays role badges correctly', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue(mockMembers)

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(screen.getByText('owner')).toBeInTheDocument()
    })

    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('member')).toBeInTheDocument()
  })

  it('opens invite dialog when button clicked', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue(mockMembers)

    const user = userEvent.setup()

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(screen.getByText('Invite Member')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Invite Member'))

    await waitFor(() => {
      expect(screen.getByText('Invite Team Member')).toBeInTheDocument()
    })

    expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
    expect(screen.getByLabelText('Role')).toBeInTheDocument()
  })

  it('shows invite form fields when dialog opened', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue(mockMembers)

    const user = userEvent.setup()

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(screen.getByText('Invite Member')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Invite Member'))

    await waitFor(() => {
      expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
    })

    expect(screen.getByLabelText('Role')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send invite/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('shows empty state when no members', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue({
      members: [],
      total: 0,
    })

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(
        screen.getByText(/no team members yet/i)
      ).toBeInTheDocument()
    })
  })

  it('renders action buttons for each member', async () => {
    vi.mocked(settingsApi.listTenantMembers).mockResolvedValue(mockMembers)

    renderWithQueryClient(<TeamSettings />)

    await waitFor(() => {
      expect(screen.getByText('Owner User')).toBeInTheDocument()
    })

    // Should have action buttons for each member
    const buttons = screen.getAllByRole('button')
    // Should include Invite Member button + action buttons for each member
    expect(buttons.length).toBeGreaterThanOrEqual(mockMembers.members.length + 1)
  })
})
