import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchableSpoolSelect } from './SearchableSpoolSelect'
import type { SpoolResponse } from '@/types/spool'

// Mock spool data
const mockSpools: SpoolResponse[] = [
  {
    id: 'spool-1',
    tenant_id: 'tenant-1',
    spool_id: 'FIL-001',
    material_type_id: 'mat-1',
    brand: 'Bambu',
    color: 'Black',
    color_hex: '000000',
    finish: null,
    diameter: 1.75,
    density: 1.24,
    extruder_temp: 220,
    bed_temp: 60,
    translucent: false,
    glow: false,
    pattern: null,
    spool_type: 'plastic',
    initial_weight: 1000,
    current_weight: 800,
    empty_spool_weight: 200,
    purchase_date: '2024-01-01',
    purchase_price: 25.0,
    supplier: 'Bambu Store',
    purchased_quantity: 1,
    spools_remaining: 1,
    storage_location: 'Shelf A',
    notes: null,
    qr_code_id: null,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    remaining_weight: 600,
    remaining_percentage: 75,
    material_type_code: 'PLA',
    material_type_name: 'PLA',
  },
  {
    id: 'spool-2',
    tenant_id: 'tenant-1',
    spool_id: 'FIL-002',
    material_type_id: 'mat-1',
    brand: 'Polymaker',
    color: 'Crimson Red',
    color_hex: 'DC143C',
    finish: 'Matte',
    diameter: 1.75,
    density: 1.24,
    extruder_temp: 220,
    bed_temp: 60,
    translucent: false,
    glow: false,
    pattern: null,
    spool_type: 'cardboard',
    initial_weight: 1000,
    current_weight: 500,
    empty_spool_weight: 150,
    purchase_date: '2024-02-01',
    purchase_price: 30.0,
    supplier: 'Amazon',
    purchased_quantity: 1,
    spools_remaining: 1,
    storage_location: 'Shelf B',
    notes: null,
    qr_code_id: null,
    is_active: true,
    created_at: '2024-02-01T00:00:00Z',
    updated_at: '2024-02-01T00:00:00Z',
    remaining_weight: 350,
    remaining_percentage: 46.7,
    material_type_code: 'PLA',
    material_type_name: 'PLA',
  },
  {
    id: 'spool-3',
    tenant_id: 'tenant-1',
    spool_id: 'FIL-003',
    material_type_id: 'mat-2',
    brand: 'Overture',
    color: 'Ocean Blue',
    color_hex: '0077BE',
    finish: null,
    diameter: 1.75,
    density: 1.08,
    extruder_temp: 250,
    bed_temp: 80,
    translucent: false,
    glow: false,
    pattern: null,
    spool_type: 'plastic',
    initial_weight: 1000,
    current_weight: 950,
    empty_spool_weight: 200,
    purchase_date: '2024-03-01',
    purchase_price: 35.0,
    supplier: 'Amazon',
    purchased_quantity: 1,
    spools_remaining: 1,
    storage_location: 'Shelf C',
    notes: null,
    qr_code_id: null,
    is_active: true,
    created_at: '2024-03-01T00:00:00Z',
    updated_at: '2024-03-01T00:00:00Z',
    remaining_weight: 750,
    remaining_percentage: 93.75,
    material_type_code: 'PETG',
    material_type_name: 'PETG',
  },
  {
    id: 'spool-4',
    tenant_id: 'tenant-1',
    spool_id: 'FIL-004',
    material_type_id: 'mat-1',
    brand: 'eSUN',
    color: 'White',
    color_hex: 'FFFFFF',
    finish: null,
    diameter: 1.75,
    density: 1.24,
    extruder_temp: 220,
    bed_temp: 60,
    translucent: false,
    glow: false,
    pattern: null,
    spool_type: 'plastic',
    initial_weight: 1000,
    current_weight: 100,
    empty_spool_weight: 200,
    purchase_date: '2024-01-15',
    purchase_price: 20.0,
    supplier: 'eBay',
    purchased_quantity: 1,
    spools_remaining: 1,
    storage_location: 'Shelf A',
    notes: 'Almost empty',
    qr_code_id: null,
    is_active: false, // Inactive spool
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2024-04-01T00:00:00Z',
    remaining_weight: 0,
    remaining_percentage: 0,
    material_type_code: 'PLA',
    material_type_name: 'PLA',
  },
]

describe('SearchableSpoolSelect', () => {
  it('renders with placeholder', () => {
    render(<SearchableSpoolSelect spools={mockSpools} placeholder="Select a spool..." />)
    expect(screen.getByRole('combobox')).toHaveTextContent('Select a spool...')
  })

  it('renders with selected value', () => {
    render(<SearchableSpoolSelect spools={mockSpools} value="spool-1" />)
    const combobox = screen.getByRole('combobox')
    expect(combobox).toHaveTextContent('FIL-001')
    expect(combobox).toHaveTextContent('Bambu Black')
    expect(combobox).toHaveTextContent('PLA')
  })

  it('opens dropdown and shows spools on click', async () => {
    const user = userEvent.setup()
    render(<SearchableSpoolSelect spools={mockSpools} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Should show search input
    expect(screen.getByPlaceholderText('Search by color...')).toBeInTheDocument()

    // Should show spool IDs
    expect(screen.getByText('FIL-001')).toBeInTheDocument()
    expect(screen.getByText('FIL-002')).toBeInTheDocument()
    expect(screen.getByText('FIL-003')).toBeInTheDocument()
  })

  it('filters spools by color name when typing', async () => {
    const user = userEvent.setup()
    render(<SearchableSpoolSelect spools={mockSpools} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    const searchInput = screen.getByPlaceholderText('Search by color...')
    await user.type(searchInput, 'red')

    // Should show Crimson Red spool
    expect(screen.getByText('FIL-002')).toBeInTheDocument()
    expect(screen.getByText(/Crimson Red/)).toBeInTheDocument()

    // Should not show other spools
    expect(screen.queryByText('FIL-001')).not.toBeInTheDocument()
    expect(screen.queryByText('FIL-003')).not.toBeInTheDocument()
  })

  it('calls onValueChange when spool selected', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()

    render(<SearchableSpoolSelect spools={mockSpools} onValueChange={handleChange} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Click on FIL-002 option
    const option = screen.getByText('FIL-002')
    await user.click(option)

    expect(handleChange).toHaveBeenCalledWith('spool-2')
  })

  it('shows empty message when no results', async () => {
    const user = userEvent.setup()
    render(<SearchableSpoolSelect spools={mockSpools} emptyText="No matching spools" />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    const searchInput = screen.getByPlaceholderText('Search by color...')
    await user.type(searchInput, 'xyz123nonexistent')

    expect(screen.getByText('No matching spools')).toBeInTheDocument()
  })

  it('respects disabled state', () => {
    render(<SearchableSpoolSelect spools={mockSpools} disabled />)
    const trigger = screen.getByRole('combobox')
    expect(trigger).toBeDisabled()
  })

  it('excludes specified spool IDs', async () => {
    const user = userEvent.setup()
    render(
      <SearchableSpoolSelect
        spools={mockSpools}
        excludeSpoolIds={['spool-1', 'spool-3']}
      />
    )

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Should not show excluded spools
    expect(screen.queryByText('FIL-001')).not.toBeInTheDocument()
    expect(screen.queryByText('FIL-003')).not.toBeInTheDocument()

    // Should show non-excluded spools
    expect(screen.getByText('FIL-002')).toBeInTheDocument()
    expect(screen.getByText('FIL-004')).toBeInTheDocument()
  })

  it('displays remaining weight in dropdown', async () => {
    const user = userEvent.setup()
    render(<SearchableSpoolSelect spools={mockSpools} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Check for remaining weights (from mock data)
    expect(screen.getByText('600g')).toBeInTheDocument() // spool-1
    expect(screen.getByText('350g')).toBeInTheDocument() // spool-2
    expect(screen.getByText('750g')).toBeInTheDocument() // spool-3
  })

  it('displays material type badges in dropdown', async () => {
    const user = userEvent.setup()
    render(<SearchableSpoolSelect spools={mockSpools} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Should show material type badges
    const plaBadges = screen.getAllByText('PLA')
    expect(plaBadges.length).toBeGreaterThan(0)
    expect(screen.getByText('PETG')).toBeInTheDocument()
  })

  it('shows finish info for spools with finish', async () => {
    const user = userEvent.setup()
    render(<SearchableSpoolSelect spools={mockSpools} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // FIL-002 has Matte finish
    expect(screen.getByText(/\(Matte\)/)).toBeInTheDocument()
  })

  it('clears value when selecting same spool', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()

    render(
      <SearchableSpoolSelect
        spools={mockSpools}
        value="spool-1"
        onValueChange={handleChange}
      />
    )

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Find and click the FIL-001 option in dropdown
    const fil001Options = screen.getAllByText('FIL-001')
    // Last one should be in the dropdown
    const option = fil001Options[fil001Options.length - 1]
    await user.click(option)

    // Should clear value
    expect(handleChange).toHaveBeenCalledWith('')
  })

  it('applies custom className to trigger', () => {
    render(<SearchableSpoolSelect spools={mockSpools} className="custom-class" />)
    const trigger = screen.getByRole('combobox')
    expect(trigger).toHaveClass('custom-class')
  })
})
