import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge, badgeVariants } from './badge'

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Status</Badge>)
    expect(screen.getByText('Status')).toBeInTheDocument()
  })

  it('applies default variant classes', () => {
    render(<Badge>Default</Badge>)
    const badge = screen.getByText('Default')
    expect(badge).toHaveClass('bg-primary')
    expect(badge).toHaveClass('text-primary-foreground')
  })

  it('applies secondary variant classes', () => {
    render(<Badge variant="secondary">Secondary</Badge>)
    const badge = screen.getByText('Secondary')
    expect(badge).toHaveClass('bg-secondary')
    expect(badge).toHaveClass('text-secondary-foreground')
  })

  it('applies destructive variant classes', () => {
    render(<Badge variant="destructive">Error</Badge>)
    const badge = screen.getByText('Error')
    expect(badge).toHaveClass('bg-destructive')
    expect(badge).toHaveClass('text-destructive-foreground')
  })

  it('applies outline variant classes', () => {
    render(<Badge variant="outline">Outline</Badge>)
    const badge = screen.getByText('Outline')
    expect(badge).toHaveClass('text-foreground')
    expect(badge).not.toHaveClass('bg-primary')
  })

  it('applies success variant classes', () => {
    render(<Badge variant="success">Success</Badge>)
    const badge = screen.getByText('Success')
    expect(badge).toHaveClass('bg-green-500')
    expect(badge).toHaveClass('text-white')
  })

  it('applies warning variant classes', () => {
    render(<Badge variant="warning">Warning</Badge>)
    const badge = screen.getByText('Warning')
    expect(badge).toHaveClass('bg-yellow-500')
    expect(badge).toHaveClass('text-white')
  })

  it('merges custom className with default classes', () => {
    render(<Badge className="custom-class">Custom</Badge>)
    const badge = screen.getByText('Custom')
    expect(badge).toHaveClass('custom-class')
    expect(badge).toHaveClass('rounded-md')
  })

  it('renders as a div element', () => {
    render(<Badge data-testid="badge">Test</Badge>)
    const badge = screen.getByTestId('badge')
    expect(badge.tagName).toBe('DIV')
  })

  it('passes through native HTML attributes', () => {
    render(<Badge data-testid="badge" id="test-badge">Test</Badge>)
    const badge = screen.getByTestId('badge')
    expect(badge).toHaveAttribute('id', 'test-badge')
  })
})

describe('badgeVariants', () => {
  it('generates correct classes for default variant', () => {
    const classes = badgeVariants({ variant: 'default' })
    expect(classes).toContain('bg-primary')
  })

  it('generates correct classes for success variant', () => {
    const classes = badgeVariants({ variant: 'success' })
    expect(classes).toContain('bg-green-500')
  })

  it('returns base classes when no variant specified', () => {
    const classes = badgeVariants()
    expect(classes).toContain('inline-flex')
    expect(classes).toContain('rounded-md')
    expect(classes).toContain('text-xs')
  })
})
