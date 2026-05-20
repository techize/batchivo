import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AddFilamentDialog } from './AddFilamentDialog'

// Mock Radix UI Select with a native <select> so userEvent can interact with it in jsdom.
// Radix UI Select relies on pointer events and portals that are not supported in jsdom.
vi.mock('@/components/ui/select', () => ({
  Select: ({ children, onValueChange, value }: { children: React.ReactNode; onValueChange?: (v: string) => void; value?: string }) => (
    <div data-testid="select-wrapper">
      {/* Render a native select so tests can interact with it */}
      <select
        data-testid="native-select"
        value={value ?? ''}
        onChange={(e) => onValueChange?.(e.target.value)}
        aria-label="Material type"
      >
        {children}
      </select>
    </div>
  ),
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
  SelectContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectItem: ({ value, children }: { value: string; children: React.ReactNode }) => (
    <option value={value}>{children}</option>
  ),
}))

const mockBulkMutateAsync = vi.fn().mockResolvedValue({
  filament_type_id: 'ft-1',
  spool_ids: ['FIL-001', 'FIL-002'],
})
const mockBatchMutateAsync = vi.fn().mockResolvedValue({
  results: [{ filament_type_id: 'ft-1', spool_id: 'FIL-001' }],
})

vi.mock('@/hooks/useFilamentTypes', () => ({
  useBulkCreateFilamentType: () => ({
    mutateAsync: mockBulkMutateAsync,
    isPending: false,
    isError: false,
    error: null,
  }),
  useBatchCreateFilamentTypes: () => ({
    mutateAsync: mockBatchMutateAsync,
    isPending: false,
    isError: false,
    error: null,
  }),
}))

vi.mock('@/lib/api/spools', () => ({
  materialTypesApi: {
    list: () => Promise.resolve([{ id: 'mat-1', name: 'PLA', code: 'PLA' }]),
  },
}))

function renderDialog(props?: { open?: boolean; onOpenChange?: (open: boolean) => void }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onOpenChange = props?.onOpenChange ?? vi.fn()
  render(
    <QueryClientProvider client={qc}>
      <AddFilamentDialog open={props?.open ?? true} onOpenChange={onOpenChange} />
    </QueryClientProvider>
  )
  return { onOpenChange }
}

describe('AddFilamentDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders mode selector when open', () => {
    renderDialog()
    expect(screen.getByText('How would you like to add filament?')).toBeInTheDocument()
    expect(screen.getByText('Batch of identical spools')).toBeInTheDocument()
    expect(screen.getByText('Multiple color variants')).toBeInTheDocument()
  })

  it('does not render dialog content when closed', () => {
    renderDialog({ open: false })
    expect(screen.queryByText('How would you like to add filament?')).not.toBeInTheDocument()
  })

  it('clicking bulk card shows bulk form', async () => {
    const user = userEvent.setup()
    renderDialog()
    await user.click(screen.getByText('Batch of identical spools'))
    expect(screen.getByText('Add filament — batch')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add spools/i })).toBeInTheDocument()
  })

  it('clicking batch card shows batch form', async () => {
    const user = userEvent.setup()
    renderDialog()
    await user.click(screen.getByText('Multiple color variants'))
    expect(screen.getByText('Add filament — color variants')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit all/i })).toBeInTheDocument()
  })

  it('back button from bulk form returns to mode selector', async () => {
    const user = userEvent.setup()
    renderDialog()
    await user.click(screen.getByText('Batch of identical spools'))
    expect(screen.getByText('Add filament — batch')).toBeInTheDocument()
    const backBtn = screen.getByRole('button', { name: /back to mode selector/i })
    await user.click(backBtn)
    expect(screen.getByText('How would you like to add filament?')).toBeInTheDocument()
  })

  it('back button from batch form returns to mode selector', async () => {
    const user = userEvent.setup()
    renderDialog()
    await user.click(screen.getByText('Multiple color variants'))
    expect(screen.getByText('Add filament — color variants')).toBeInTheDocument()
    const backBtn = screen.getByRole('button', { name: /back to mode selector/i })
    await user.click(backBtn)
    expect(screen.getByText('How would you like to add filament?')).toBeInTheDocument()
  })

  it('Submit all is disabled when batch rows are empty', async () => {
    const user = userEvent.setup()
    renderDialog()
    await user.click(screen.getByText('Multiple color variants'))
    expect(screen.getByRole('button', { name: /submit all/i })).toBeDisabled()
  })

  it('Add color appends a row and enables Submit all', async () => {
    const user = userEvent.setup()
    renderDialog()

    await user.click(screen.getByText('Multiple color variants'))

    // Fill required text fields
    await user.type(screen.getByRole('textbox', { name: /brand/i }), 'JAYO')
    await user.type(screen.getByRole('textbox', { name: /color/i }), 'Red')

    // Set material_type_id via the mocked native select (aria-label set in mock)
    const nativeSelect = screen.getByRole('combobox', { name: /material type/i })
    fireEvent.change(nativeSelect, { target: { value: 'mat-1' } })

    // Submit the batch entry form — "Add color" is the submit button in the batch entry form
    await user.click(screen.getByRole('button', { name: /add color/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit all/i })).not.toBeDisabled()
    })
  })

  it('Submit all calls batchCreate mutation with accumulated entries', async () => {
    const user = userEvent.setup()
    renderDialog()

    await user.click(screen.getByText('Multiple color variants'))

    // Fill required text fields
    await user.type(screen.getByRole('textbox', { name: /brand/i }), 'JAYO')
    await user.type(screen.getByRole('textbox', { name: /color/i }), 'Red')

    // Set material_type_id via the mocked native select
    const nativeSelect = screen.getByRole('combobox', { name: /material type/i })
    fireEvent.change(nativeSelect, { target: { value: 'mat-1' } })

    // Add the row
    await user.click(screen.getByRole('button', { name: /add color/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit all/i })).not.toBeDisabled()
    })

    await user.click(screen.getByRole('button', { name: /submit all/i }))

    await waitFor(() => {
      expect(mockBatchMutateAsync).toHaveBeenCalledOnce()
    })
    const callArg = mockBatchMutateAsync.mock.calls[0][0]
    expect(callArg).toHaveProperty('entries')
    expect(callArg.entries.length).toBeGreaterThan(0)
  })
})
