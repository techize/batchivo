/**
 * Tests for GeneralSettings component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GeneralSettings } from './GeneralSettings'
import * as settingsApi from '@/lib/api/settings'

// Mock the settings API
vi.mock('@/lib/api/settings', () => ({
  getTenant: vi.fn(),
  updateTenant: vi.fn(),
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

describe('GeneralSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(settingsApi.getTenant).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    renderWithQueryClient(<GeneralSettings />)

    // Should show a loading spinner
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('displays tenant information when loaded', async () => {
    vi.mocked(settingsApi.getTenant).mockResolvedValue(mockTenant)

    renderWithQueryClient(<GeneralSettings />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Organization')).toBeInTheDocument()
    })

    expect(screen.getByDisplayValue('A test organization')).toBeInTheDocument()
    expect(screen.getByText('test-org')).toBeInTheDocument()
  })

  it('shows error state when API fails', async () => {
    vi.mocked(settingsApi.getTenant).mockRejectedValue(new Error('API Error'))

    renderWithQueryClient(<GeneralSettings />)

    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument()
    })

    expect(screen.getByText('Failed to load organization settings')).toBeInTheDocument()
  })

  it('enables save button when form is dirty', async () => {
    vi.mocked(settingsApi.getTenant).mockResolvedValue(mockTenant)
    const user = userEvent.setup()

    renderWithQueryClient(<GeneralSettings />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Organization')).toBeInTheDocument()
    })

    const nameInput = screen.getByDisplayValue('Test Organization')
    const saveButton = screen.getByRole('button', { name: /save changes/i })

    // Button should be disabled initially
    expect(saveButton).toBeDisabled()

    // Type in the input
    await user.clear(nameInput)
    await user.type(nameInput, 'New Organization Name')

    // Button should now be enabled
    expect(saveButton).not.toBeDisabled()
  })

  it('calls updateTenant when form is submitted', async () => {
    vi.mocked(settingsApi.getTenant).mockResolvedValue(mockTenant)
    vi.mocked(settingsApi.updateTenant).mockResolvedValue({
      ...mockTenant,
      name: 'New Organization Name',
    })

    const user = userEvent.setup()

    renderWithQueryClient(<GeneralSettings />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Organization')).toBeInTheDocument()
    })

    const nameInput = screen.getByDisplayValue('Test Organization')
    await user.clear(nameInput)
    await user.type(nameInput, 'New Organization Name')

    const saveButton = screen.getByRole('button', { name: /save changes/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(settingsApi.updateTenant).toHaveBeenCalledWith({
        name: 'New Organization Name',
        description: 'A test organization',
      })
    })
  })

  it('displays read-only organization info', async () => {
    vi.mocked(settingsApi.getTenant).mockResolvedValue(mockTenant)

    renderWithQueryClient(<GeneralSettings />)

    await waitFor(() => {
      expect(screen.getByText('Organization Info')).toBeInTheDocument()
    })

    expect(screen.getByText('Slug:')).toBeInTheDocument()
    expect(screen.getByText('test-org')).toBeInTheDocument()
    expect(screen.getByText('Created:')).toBeInTheDocument()
  })
})
