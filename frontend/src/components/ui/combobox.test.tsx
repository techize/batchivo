import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Combobox, type ComboboxOption } from './combobox'

const mockOptions: ComboboxOption[] = [
  { value: 'apple', label: 'Apple' },
  { value: 'banana', label: 'Banana' },
  { value: 'cherry', label: 'Cherry' },
  { value: 'disabled', label: 'Disabled Option', disabled: true },
]

describe('Combobox', () => {
  it('renders with placeholder', () => {
    render(<Combobox options={mockOptions} placeholder="Select a fruit..." />)
    expect(screen.getByRole('combobox')).toHaveTextContent('Select a fruit...')
  })

  it('renders with selected value', () => {
    render(<Combobox options={mockOptions} value="banana" />)
    expect(screen.getByRole('combobox')).toHaveTextContent('Banana')
  })

  it('opens dropdown on click', async () => {
    const user = userEvent.setup()
    render(<Combobox options={mockOptions} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
    expect(screen.getByText('Apple')).toBeInTheDocument()
    expect(screen.getByText('Banana')).toBeInTheDocument()
    expect(screen.getByText('Cherry')).toBeInTheDocument()
  })

  it('calls onValueChange when option selected', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()

    render(<Combobox options={mockOptions} onValueChange={handleChange} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    const option = screen.getByText('Banana')
    await user.click(option)

    expect(handleChange).toHaveBeenCalledWith('banana')
  })

  it('clears value when selecting same option', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()

    render(
      <Combobox options={mockOptions} value="banana" onValueChange={handleChange} />
    )

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // Get all Banana texts - one in trigger, one in dropdown
    const bananaTexts = screen.getAllByText('Banana')
    // Click the one in the dropdown (last one)
    const option = bananaTexts[bananaTexts.length - 1]
    await user.click(option)

    expect(handleChange).toHaveBeenCalledWith('')
  })

  it('filters options by search', async () => {
    const user = userEvent.setup()
    render(<Combobox options={mockOptions} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    const searchInput = screen.getByPlaceholderText('Search...')
    await user.type(searchInput, 'ban')

    // Only Banana should be visible
    expect(screen.getByText('Banana')).toBeInTheDocument()
    expect(screen.queryByText('Apple')).not.toBeInTheDocument()
    expect(screen.queryByText('Cherry')).not.toBeInTheDocument()
  })

  it('shows empty message when no results', async () => {
    const user = userEvent.setup()
    render(<Combobox options={mockOptions} emptyText="Nothing found" />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    const searchInput = screen.getByPlaceholderText('Search...')
    await user.type(searchInput, 'xyz')

    expect(screen.getByText('Nothing found')).toBeInTheDocument()
  })

  it('respects disabled state', () => {
    render(<Combobox options={mockOptions} disabled />)

    const trigger = screen.getByRole('combobox')
    expect(trigger).toBeDisabled()
  })

  it('uses custom searchPlaceholder', async () => {
    const user = userEvent.setup()
    render(<Combobox options={mockOptions} searchPlaceholder="Type to search..." />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    expect(screen.getByPlaceholderText('Type to search...')).toBeInTheDocument()
  })

  it('uses custom renderValue', () => {
    const renderValue = (option: ComboboxOption | undefined) => {
      return option ? `Selected: ${option.label}` : 'Pick one'
    }

    render(<Combobox options={mockOptions} value="apple" renderValue={renderValue} />)

    expect(screen.getByRole('combobox')).toHaveTextContent('Selected: Apple')
  })

  it('uses custom renderOption', async () => {
    const user = userEvent.setup()
    const renderOption = (option: ComboboxOption, isSelected: boolean) => {
      return (
        <span data-testid={`option-${option.value}`}>
          {isSelected ? 'SELECTED ' : ''}{option.label} (custom)
        </span>
      )
    }

    render(<Combobox options={mockOptions} value="banana" renderOption={renderOption} />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    expect(screen.getByTestId('option-banana')).toHaveTextContent('SELECTED Banana (custom)')
    expect(screen.getByTestId('option-apple')).toHaveTextContent('Apple (custom)')
  })

  it('shows check mark for selected option', async () => {
    const user = userEvent.setup()
    render(<Combobox options={mockOptions} value="cherry" />)

    const trigger = screen.getByRole('combobox')
    await user.click(trigger)

    // The selected option should be in the dropdown
    const cherryOptions = screen.getAllByText('Cherry')
    expect(cherryOptions.length).toBeGreaterThan(0)

    // Check that there's a visible check icon (opacity-100)
    const checkIcons = document.querySelectorAll('[class*="opacity-100"]')
    expect(checkIcons.length).toBeGreaterThan(0)
  })

  it('applies custom className', () => {
    render(<Combobox options={mockOptions} className="custom-class" />)

    const trigger = screen.getByRole('combobox')
    expect(trigger).toHaveClass('custom-class')
  })
})
