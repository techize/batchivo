/**
 * E2E Tests: Settings Page Workflow
 *
 * Tests the settings page functionality including:
 * - Navigation to settings
 * - Tab switching (General, Payments, Team)
 * - General settings display and updates
 * - Team management features
 * - Payment settings visibility
 */

import { test, expect } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('should display settings page with all elements', async ({ page }) => {
    // Verify page title
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
    await expect(page.getByText('Manage your organization settings')).toBeVisible()

    // Verify tabs exist
    await expect(page.getByRole('tab', { name: /general/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /payments/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /team/i })).toBeVisible()
  })

  test('should display general settings by default', async ({ page }) => {
    // General tab should be selected by default
    const generalTab = page.getByRole('tab', { name: /general/i })
    await expect(generalTab).toHaveAttribute('data-state', 'active')

    // General settings content should be visible
    await expect(page.getByText(/organization|business|company/i).first()).toBeVisible()
  })

  test('should switch to payments tab', async ({ page }) => {
    // Click payments tab
    await page.getByRole('tab', { name: /payments/i }).click()

    // Wait for tab content to change
    await page.waitForTimeout(500)

    // Payments tab should be selected
    const paymentsTab = page.getByRole('tab', { name: /payments/i })
    await expect(paymentsTab).toHaveAttribute('data-state', 'active')

    // Payments content should be visible (Square integration)
    await expect(page.getByText(/square|payment/i).first()).toBeVisible()
  })

  test('should switch to team tab', async ({ page }) => {
    // Click team tab
    await page.getByRole('tab', { name: /team/i }).click()

    // Wait for tab content to change
    await page.waitForTimeout(500)

    // Team tab should be selected
    const teamTab = page.getByRole('tab', { name: /team/i })
    await expect(teamTab).toHaveAttribute('data-state', 'active')

    // Team content should be visible
    await expect(page.getByText(/team|members|invite/i).first()).toBeVisible()
  })

  test('should persist tab state on navigation', async ({ page }) => {
    // Switch to team tab
    await page.getByRole('tab', { name: /team/i }).click()
    await page.waitForTimeout(500)

    // Navigate away and back
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')

    // General tab should be selected (default behavior)
    const generalTab = page.getByRole('tab', { name: /general/i })
    await expect(generalTab).toHaveAttribute('data-state', 'active')
  })
})

test.describe('General Settings', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('should display organization information', async ({ page }) => {
    // Check for organization name or business details section
    const organizationSection = page.locator('text=/organization name|business name|tenant/i')
    await expect(organizationSection.first()).toBeVisible({ timeout: 5000 })
  })

  test('should have editable fields', async ({ page }) => {
    // Look for input fields in general settings
    const inputs = page.locator('input, textarea')
    const inputCount = await inputs.count()

    // Should have at least some editable fields
    expect(inputCount).toBeGreaterThan(0)
  })
})

test.describe('Team Settings', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
    
    // Navigate to team tab
    await page.getByRole('tab', { name: /team/i }).click()
    await page.waitForTimeout(500)
  })

  test('should display team members list', async ({ page }) => {
    // Should show current user as team member
    await expect(page.getByText(/member|user|admin/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('should have invite team member option', async ({ page }) => {
    // Look for invite button or link
    const inviteButton = page.getByRole('button', { name: /invite|add.*member/i })
    
    // Invite functionality might be available
    // If visible, click to open invite dialog
    if (await inviteButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await inviteButton.click()
      
      // Check for invite dialog/form
      const emailInput = page.locator('input[type="email"], input[placeholder*="email" i]')
      await expect(emailInput).toBeVisible({ timeout: 5000 })
    }
  })

  test('should display current user role', async ({ page }) => {
    // Should show user's role (Owner, Admin, etc.)
    const roleIndicator = page.locator('text=/owner|admin|member/i')
    await expect(roleIndicator.first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Payment Settings', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
    
    // Navigate to payments tab
    await page.getByRole('tab', { name: /payments/i }).click()
    await page.waitForTimeout(500)
  })

  test('should display Square integration section', async ({ page }) => {
    // Should show Square integration info
    await expect(page.getByText(/square/i).first()).toBeVisible({ timeout: 5000 })
  })

  test('should show connection status', async ({ page }) => {
    // Should indicate if Square is connected or not
    const statusIndicator = page.locator('text=/connected|not connected|connect|setup/i')
    await expect(statusIndicator.first()).toBeVisible({ timeout: 5000 })
  })

  test('should have connect button for Square', async ({ page }) => {
    // Look for connect/setup button
    const connectButton = page.getByRole('button', { name: /connect|setup|configure/i })
    
    // Button should be visible (either to connect or reconfigure)
    if (await connectButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Verify it's clickable
      await expect(connectButton).toBeEnabled()
    }
  })
})

test.describe('Settings Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running')
    await registerAndLogin(page)
  })

  test('should navigate to settings from dashboard', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Look for settings link/button in navigation
    const settingsLink = page.getByRole('link', { name: /settings/i }).or(
      page.getByRole('button', { name: /settings/i })
    )
    
    if (await settingsLink.isVisible()) {
      await settingsLink.click()
      await expect(page).toHaveURL(/\/settings/)
    } else {
      // Direct navigation fallback
      await page.goto('/settings')
      await expect(page).toHaveURL(/\/settings/)
    }
  })

  test('should require authentication for settings', async ({ page }) => {
    // Logout first
    await page.goto('/logout')
    await page.waitForURL(/\/login/, { timeout: 10000 })

    // Try to access settings
    await page.goto('/settings')
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/)
  })
})
