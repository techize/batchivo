import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button, buttonVariants } from './button'

describe('Button', () => {
  it('renders children correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('applies default variant and size classes', () => {
    render(<Button>Default</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-primary')
    expect(button).toHaveClass('h-9')
    expect(button).toHaveClass('px-4')
  })

  it('applies destructive variant classes', () => {
    render(<Button variant="destructive">Delete</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-destructive')
  })

  it('applies outline variant classes', () => {
    render(<Button variant="outline">Outline</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('border')
    expect(button).toHaveClass('bg-background')
  })

  it('applies secondary variant classes', () => {
    render(<Button variant="secondary">Secondary</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-secondary')
  })

  it('applies ghost variant classes', () => {
    render(<Button variant="ghost">Ghost</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('hover:bg-accent')
    expect(button).not.toHaveClass('bg-primary')
  })

  it('applies link variant classes', () => {
    render(<Button variant="link">Link</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('underline-offset-4')
  })

  it('applies small size classes', () => {
    render(<Button size="sm">Small</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('h-8')
    expect(button).toHaveClass('px-3')
  })

  it('applies large size classes', () => {
    render(<Button size="lg">Large</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('h-10')
    expect(button).toHaveClass('px-8')
  })

  it('applies icon size classes', () => {
    render(<Button size="icon">Icon</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('h-9')
    expect(button).toHaveClass('w-9')
  })

  it('handles click events', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click</Button>)
    
    await user.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled when disabled prop is passed', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()
    render(<Button onClick={handleClick} disabled>Disabled</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveClass('disabled:opacity-50')
    
    await user.click(button)
    expect(handleClick).not.toHaveBeenCalled()
  })

  it('merges custom className with default classes', () => {
    render(<Button className="custom-class">Custom</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
    expect(button).toHaveClass('bg-primary')
  })

  it('forwards ref correctly', () => {
    const ref = vi.fn()
    render(<Button ref={ref}>Ref</Button>)
    expect(ref).toHaveBeenCalled()
    expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLButtonElement)
  })

  it('passes through native button props', () => {
    render(<Button type="submit" name="test-button">Submit</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('type', 'submit')
    expect(button).toHaveAttribute('name', 'test-button')
  })
})

describe('buttonVariants', () => {
  it('generates correct classes for default variant', () => {
    const classes = buttonVariants({ variant: 'default', size: 'default' })
    expect(classes).toContain('bg-primary')
    expect(classes).toContain('h-9')
  })

  it('generates correct classes for destructive variant', () => {
    const classes = buttonVariants({ variant: 'destructive' })
    expect(classes).toContain('bg-destructive')
  })

  it('returns base classes when no variants specified', () => {
    const classes = buttonVariants()
    expect(classes).toContain('inline-flex')
    expect(classes).toContain('items-center')
  })
})
