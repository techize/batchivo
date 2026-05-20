/**
 * FilamentTypeCard component tests.
 * Covers rendering, badge variants, and interaction with stopPropagation.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FilamentTypeCard } from './FilamentTypeCard'
import type { FilamentTypeListItem } from '@/types/filament-type'

const mockFilamentType: FilamentTypeListItem = {
  id: 'ft-1',
  brand: 'JAYO',
  color: 'Black',
  color_hex: 'FF000000',
  material_type_name: 'PETG',
  material_type_code: 'PETG',
  has_sample: false,
  spool_count: 3,
  labeled_count: 1,
}

describe('FilamentTypeCard', () => {
  it('renders brand and color name', () => {
    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    expect(screen.getByText('JAYO')).toBeInTheDocument()
    expect(screen.getByText('Black')).toBeInTheDocument()
  })

  it('renders material type name', () => {
    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    expect(screen.getByText('PETG')).toBeInTheDocument()
  })

  it('renders spool count badge', () => {
    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    expect(screen.getByText('3 spools')).toBeInTheDocument()
  })

  it('renders labeled count badge with partial status', () => {
    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    // labeled_count=1, spool_count=3
    expect(screen.getByText('1/3 labeled')).toBeInTheDocument()
  })

  it('renders No sample badge when has_sample is false', () => {
    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    expect(screen.getByText('No sample')).toBeInTheDocument()
  })

  it('renders Sample checkmark badge when has_sample is true', () => {
    render(
      <FilamentTypeCard
        filamentType={{ ...mockFilamentType, has_sample: true }}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    expect(screen.getByText('Sample ✓')).toBeInTheDocument()
  })

  it('clicking card calls onRowClick with filamentType id', () => {
    const mockOnRowClick = vi.fn()

    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={mockOnRowClick}
        onToggleSample={vi.fn()}
      />,
    )

    // Click the brand text (part of the card, not the toggle button)
    fireEvent.click(screen.getByText('JAYO'))

    expect(mockOnRowClick).toHaveBeenCalledWith('ft-1')
  })

  it('clicking has_sample toggle calls onToggleSample but not onRowClick (stopPropagation)', () => {
    const mockOnRowClick = vi.fn()
    const mockOnToggleSample = vi.fn()

    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={mockOnRowClick}
        onToggleSample={mockOnToggleSample}
      />,
    )

    // Find the toggle button by its aria-label (contains "sample")
    const toggleBtn = screen.getByLabelText(/Mark sample printed for JAYO Black/i)
    fireEvent.click(toggleBtn)

    expect(mockOnToggleSample).toHaveBeenCalledWith('ft-1', true)
    // stopPropagation must prevent onRowClick from firing
    expect(mockOnRowClick).not.toHaveBeenCalled()
  })

  it('renders color swatch when color_hex is present', () => {
    render(
      <FilamentTypeCard
        filamentType={mockFilamentType}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    // The swatch is an aria-hidden span with a background-color style
    const swatches = document
      .querySelectorAll('[aria-hidden="true"]')
    const colorSwatch = Array.from(swatches).find(
      (el) => (el as HTMLElement).style.backgroundColor !== '',
    )

    expect(colorSwatch).toBeTruthy()
  })

  it('does not render color swatch when color_hex is absent', () => {
    render(
      <FilamentTypeCard
        filamentType={{ ...mockFilamentType, color_hex: null }}
        onRowClick={vi.fn()}
        onToggleSample={vi.fn()}
      />,
    )

    // No aria-hidden span with a background-color style should exist
    const swatches = document.querySelectorAll('[aria-hidden="true"]')
    const colorSwatch = Array.from(swatches).find(
      (el) => (el as HTMLElement).style.backgroundColor !== '',
    )

    expect(colorSwatch).toBeUndefined()
  })
})
