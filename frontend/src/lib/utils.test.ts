import { describe, it, expect, beforeEach } from 'vitest'
import { cn, getSafeRedirectUrl } from './utils'

describe('cn', () => {
  it('merges class names correctly', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    const isActive = true
    const isHidden = false
    expect(cn('base', isActive && 'active', isHidden && 'hidden')).toBe('base active')
  })

  it('handles array of classes', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar')
  })

  it('handles undefined and null values', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })

  it('merges tailwind classes correctly (last wins)', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
  })

  it('handles conflicting tailwind classes', () => {
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
  })

  it('returns empty string for no inputs', () => {
    expect(cn()).toBe('')
  })

  it('handles object syntax', () => {
    expect(cn({ 'text-red-500': true, 'text-blue-500': false })).toBe('text-red-500')
  })
})

describe('getSafeRedirectUrl', () => {
  beforeEach(() => {
    // Mock window.location.origin
    Object.defineProperty(window, 'location', {
      value: { origin: 'https://batchivo.com' },
      writable: true,
    })
  })

  it('returns default path for null input', () => {
    expect(getSafeRedirectUrl(null)).toBe('/dashboard')
  })

  it('returns default path for empty string', () => {
    expect(getSafeRedirectUrl('')).toBe('/dashboard')
  })

  it('returns custom default path when provided', () => {
    expect(getSafeRedirectUrl(null, '/home')).toBe('/home')
  })

  it('allows relative paths starting with /', () => {
    expect(getSafeRedirectUrl('/products')).toBe('/products')
    expect(getSafeRedirectUrl('/settings/profile')).toBe('/settings/profile')
  })

  it('allows relative paths with query strings', () => {
    expect(getSafeRedirectUrl('/search?q=test')).toBe('/search?q=test')
  })

  it('blocks protocol-relative URLs (//evil.com)', () => {
    expect(getSafeRedirectUrl('//evil.com')).toBe('/dashboard')
    expect(getSafeRedirectUrl('//evil.com/path')).toBe('/dashboard')
  })

  it('blocks absolute external URLs', () => {
    expect(getSafeRedirectUrl('https://evil.com')).toBe('/dashboard')
    expect(getSafeRedirectUrl('http://evil.com/path')).toBe('/dashboard')
  })

  it('blocks javascript: URLs', () => {
    expect(getSafeRedirectUrl('javascript:alert(1)')).toBe('/dashboard')
  })

  it('blocks data: URLs', () => {
    expect(getSafeRedirectUrl('data:text/html,<script>alert(1)</script>')).toBe('/dashboard')
  })

  it('allows same-origin absolute URLs', () => {
    expect(getSafeRedirectUrl('https://batchivo.com/products')).toBe('/products')
    expect(getSafeRedirectUrl('https://batchivo.com/settings?tab=billing')).toBe('/settings?tab=billing')
  })

  it('returns default for invalid URLs', () => {
    expect(getSafeRedirectUrl('not-a-valid-url-at-all:::')).toBe('/dashboard')
  })
})
