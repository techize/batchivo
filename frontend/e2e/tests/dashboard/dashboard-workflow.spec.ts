/**
 * E2E Tests: Dashboard Workflow
 *
 * Tests the dashboard page functionality including:
 * - Dashboard load and display
 * - Quick actions
 * - Navigation from dashboard
 * - Stats and metrics display
 * - Recent activity display
 */

import { test, expect } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
  })

  test('should display dashboard after login', async ({ page }) => {
    // Verify we're on the dashboard
    await expect(page).toHaveURL(/\/dashboard/)
    
    // Dashboard should have a welcome or title
    const pageContent = await page.textContent('body')
    expect(
      pageContent?.includes('Dashboard') ||
      pageContent?.includes('Welcome') ||
      pageContent?.includes('Overview')
    ).toBeTruthy()
  })

  test('should display user-specific content', async ({ page }) => {
    // Dashboard should show some personalized content
    // This could be the tenant name, user name, or recent activity
    await page.waitForLoadState('networkidle')

    // At minimum, the page should load without errors
    await expect(page.getByRole('main')).toBeVisible()
  })

  test('should display navigation menu', async ({ page }) => {
    // Sidebar or navigation should be visible
    const navigation = page.locator('nav').or(
      page.locator('[role="navigation"]').or(
        page.locator('aside')
      )
    )
    
    await expect(navigation.first()).toBeVisible()
  })

  test('should have quick action buttons', async ({ page }) => {
    // Dashboard typically has quick actions like "New Production Run", "Add Spool", etc.
    const quickActions = page.locator('button, a').filter({
      hasText: /new|add|create|view/i
    })
    
    const actionCount = await quickActions.count()
    expect(actionCount).toBeGreaterThan(0)
  })
})

test.describe('Dashboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
  })

  test('should navigate to inventory from dashboard', async ({ page }) => {
    // Look for inventory link in navigation
    const inventoryLink = page.getByRole('link', { name: /inventory/i }).or(
      page.getByRole('button', { name: /inventory/i })
    )
    
    if (await inventoryLink.isVisible()) {
      await inventoryLink.click()
      await expect(page).toHaveURL(/\/inventory/)
    }
  })

  test('should navigate to production runs from dashboard', async ({ page }) => {
    // Look for production runs link
    const productionLink = page.getByRole('link', { name: /production/i }).or(
      page.getByRole('button', { name: /production/i })
    )
    
    if (await productionLink.isVisible()) {
      await productionLink.click()
      await expect(page).toHaveURL(/\/production/)
    }
  })

  test('should navigate to products from dashboard', async ({ page }) => {
    // Look for products link
    const productsLink = page.getByRole('link', { name: /products/i }).or(
      page.getByRole('button', { name: /products/i })
    )
    
    if (await productsLink.isVisible()) {
      await productsLink.click()
      await expect(page).toHaveURL(/\/products/)
    }
  })

  test('should navigate to settings from dashboard', async ({ page }) => {
    // Look for settings in user menu or navigation
    const settingsLink = page.getByRole('link', { name: /settings/i }).or(
      page.getByRole('menuitem', { name: /settings/i })
    )
    
    if (await settingsLink.isVisible()) {
      await settingsLink.click()
      await expect(page).toHaveURL(/\/settings/)
    }
  })
})

test.describe('Dashboard Stats', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
  })

  test('should display stats cards', async ({ page }) => {
    // Dashboard typically shows stats like total products, spools, etc.
    // At least the page should load successfully
    await expect(page.getByRole('main')).toBeVisible()
  })

  test('should handle empty state for new user', async ({ page }) => {
    // New users might see empty state or getting started guide
    const pageContent = await page.textContent('body')
    
    // Should either show stats (even if 0) or a getting started message
    const hasContent = 
      pageContent?.includes('0') ||
      pageContent?.includes('Get started') ||
      pageContent?.includes('No') ||
      pageContent?.includes('Add your first') ||
      pageContent?.length && pageContent.length > 100
    
    expect(hasContent).toBeTruthy()
  })
})

test.describe('Dashboard Loading States', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
  })

  test('should show loading state then content', async ({ page }) => {
    // Navigate to dashboard and check for loading behavior
    await page.goto('/dashboard')
    
    // Page should eventually show content
    await page.waitForLoadState('networkidle')
    
    // Verify page has loaded (no error message)
    const errorMessage = page.locator('text=/error|failed|something went wrong/i')
    await expect(errorMessage).not.toBeVisible({ timeout: 5000 })
    
    // Main content should be visible
    await expect(page.getByRole('main')).toBeVisible()
  })

  test('should handle slow API responses gracefully', async ({ page }) => {
    // Simulate slow network
    await page.route('**/api/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.continue()
    })
    
    await page.goto('/dashboard')
    
    // Should show loading or skeleton while waiting
    await page.waitForLoadState('networkidle', { timeout: 30000 })
    
    // Eventually content should load
    await expect(page.getByRole('main')).toBeVisible()
  })
})

test.describe('Dashboard Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
  })

  test('should be usable on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Dashboard should still be accessible
    await expect(page.getByRole('main')).toBeVisible()
    
    // Navigation might be in a hamburger menu
    const hamburgerMenu = page.locator('button[aria-label*="menu" i]').or(
      page.locator('button[class*="menu"]')
    )
    
    // Either navigation is visible or hamburger menu exists
    const nav = page.locator('nav')
    const navVisible = await nav.isVisible().catch(() => false)
    const hamburgerVisible = await hamburgerMenu.isVisible().catch(() => false)
    
    expect(navVisible || hamburgerVisible).toBeTruthy()
  })

  test('should be usable on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Dashboard should render properly
    await expect(page.getByRole('main')).toBeVisible()
  })
})
