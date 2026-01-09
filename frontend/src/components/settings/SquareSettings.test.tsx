/**
 * Tests for SquareSettings component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SquareSettings } from './SquareSettings'
import * as settingsApi from '@/lib/api/settings'

// Mock the settings API
vi.mock('@/lib/api/settings', () => ({
  getSquareSettings: vi.fn(),
  updateSquareSettings: vi.fn(),
  testSquareConnection: vi.fn(),
}))

const mockSettingsNotConfigured = {
  enabled: false,
  environment: 'sandbox' as const,
  is_configured: false,
  access_token_masked: null,
  app_id: null,
  location_id_masked: null,
  updated_at: null,
}

const mockSettingsConfigured = {
  enabled: true,
  environment: 'sandbox' as const,
  is_configured: true,
  access_token_masked: '...5678',
  app_id: 'sq0idp-test',
  location_id_masked: '...1234',
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

describe('SquareSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(settingsApi.getSquareSettings).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    renderWithQueryClient(<SquareSettings />)

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('shows not configured state', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsNotConfigured)

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Square Payments')).toBeInTheDocument()
    })

    expect(screen.getByText('Credentials not configured')).toBeInTheDocument()
    expect(screen.getByText('Configure Credentials')).toBeInTheDocument()
  })

  it('shows configured state with masked credentials', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsConfigured)

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Credentials configured')).toBeInTheDocument()
    })

    expect(screen.getByText('Update Credentials')).toBeInTheDocument()
    expect(screen.getByText('Test Connection')).toBeInTheDocument()
  })

  it('shows error state when API fails', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockRejectedValue(new Error('API Error'))

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument()
    })

    expect(screen.getByText('Failed to load Square settings')).toBeInTheDocument()
  })

  it('allows toggling enabled state', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsNotConfigured)
    vi.mocked(settingsApi.updateSquareSettings).mockResolvedValue({
      ...mockSettingsNotConfigured,
      enabled: true,
    })

    const user = userEvent.setup()

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Square Payments')).toBeInTheDocument()
    })

    // Find and click the switch
    const switchElement = screen.getByRole('switch')
    await user.click(switchElement)

    await waitFor(() => {
      expect(settingsApi.updateSquareSettings).toHaveBeenCalledWith({ enabled: true })
    })
  })

  it('displays environment selector', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsNotConfigured)

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Environment')).toBeInTheDocument()
    })

    // Verify the select trigger is present
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    // Verify current value is shown
    expect(screen.getByText('Sandbox (Test)')).toBeInTheDocument()
  })

  it('expands credentials form when clicked', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsNotConfigured)

    const user = userEvent.setup()

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Configure Credentials')).toBeInTheDocument()
    })

    // Click to expand
    await user.click(screen.getByText('Configure Credentials'))

    await waitFor(() => {
      expect(screen.getByLabelText('Access Token')).toBeInTheDocument()
    })

    expect(screen.getByLabelText('Application ID')).toBeInTheDocument()
    expect(screen.getByLabelText('Location ID')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save credentials/i })).toBeInTheDocument()
  })

  it('tests connection when button clicked', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsConfigured)
    vi.mocked(settingsApi.testSquareConnection).mockResolvedValue({
      success: true,
      message: 'Connection successful',
      environment: 'sandbox',
      location_name: 'Test Location',
    })

    const user = userEvent.setup()

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Test Connection')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Test Connection'))

    await waitFor(() => {
      expect(settingsApi.testSquareConnection).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText('Success')).toBeInTheDocument()
      expect(screen.getByText('Connection successful')).toBeInTheDocument()
    })
  })

  it('shows failed connection test result', async () => {
    vi.mocked(settingsApi.getSquareSettings).mockResolvedValue(mockSettingsConfigured)
    vi.mocked(settingsApi.testSquareConnection).mockResolvedValue({
      success: false,
      message: 'Invalid credentials',
      environment: null,
      location_name: null,
    })

    const user = userEvent.setup()

    renderWithQueryClient(<SquareSettings />)

    await waitFor(() => {
      expect(screen.getByText('Test Connection')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Test Connection'))

    await waitFor(() => {
      expect(screen.getByText('Failed')).toBeInTheDocument()
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })
})
