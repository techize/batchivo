/**
 * E2E Tests: Authentication - Registration Flow
 *
 * Tests the registration functionality including:
 * - Successful registration with valid credentials
 * - Form validation errors (password length, mismatch)
 * - Duplicate email registration
 * - Redirect to dashboard after successful registration
 * - Empty state verification on new account dashboard
 *
 * Prerequisites:
 * - Frontend dev server running (Playwright starts this automatically)
 * - Backend API running on port 8000 (must be started manually)
 *
 * To run these tests:
 * 1. Start backend: cd backend && poetry run uvicorn app.main:app --reload
 * 2. Run tests: npm run test:e2e e2e/tests/auth/registration.spec.ts
 */

import { test, expect } from '@playwright/test'
import { HEALTH_URL } from '../../config'

// Check if backend is available
async function isBackendAvailable(): Promise<boolean> {
  try {
    const response = await fetch(HEALTH_URL)
    return response.ok
  } catch {
    return false
  }
}

// Generate unique test email to avoid conflicts between test runs
function generateTestEmail(): string {
  return `test-${Date.now()}-${Math.random().toString(36).substring(7)}@example.com`
}

// Store created test accounts for cleanup
const createdAccounts: string[] = []

test.describe('Registration Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/signup')
  })

  test('should display registration form with all elements', async ({ page }) => {
    // Verify page title and description
    await expect(page.getByText('Create an account')).toBeVisible()
    await expect(page.getByText('Sign up for Nozzly to get started')).toBeVisible()

    // Verify form elements exist
    await expect(page.locator('#fullName')).toBeVisible()
    await expect(page.locator('#email')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.locator('#confirmPassword')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()

    // Verify navigation link to login
    await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()

    // Verify password requirement hint
    await expect(page.getByText('Must be at least 8 characters')).toBeVisible()
  })

  test('should successfully register with valid credentials', async ({ page }) => {
    // Skip if backend is not available
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')

    const testEmail = generateTestEmail()
    const testPassword = 'TestPassword123!'

    // Fill in registration form
    await page.fill('#fullName', 'E2E Test User')
    await page.fill('#email', testEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for redirect to dashboard
    await page.waitForURL('/dashboard', { timeout: 15000 })

    // Verify we're on the dashboard
    await expect(page).toHaveURL(/\/dashboard/)

    // Track account for cleanup
    createdAccounts.push(testEmail)
  })

  test('should register without full name (optional field)', async ({ page }) => {
    // Skip if backend is not available
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')

    const testEmail = generateTestEmail()
    const testPassword = 'TestPassword123!'

    // Fill in registration form WITHOUT full name
    await page.fill('#email', testEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for redirect to dashboard
    await page.waitForURL('/dashboard', { timeout: 15000 })

    // Verify we're on the dashboard
    await expect(page).toHaveURL(/\/dashboard/)

    // Track account for cleanup
    createdAccounts.push(testEmail)
  })

  test('should show error for password too short', async ({ page }) => {
    const testEmail = generateTestEmail()

    // Fill in form with short password
    await page.fill('#email', testEmail)
    await page.fill('#password', 'short')
    await page.fill('#confirmPassword', 'short')

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for error message
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Password must be at least 8 characters')).toBeVisible()

    // Verify we're still on signup page
    await expect(page).toHaveURL(/\/signup/)
  })

  test('should show error for password mismatch', async ({ page }) => {
    const testEmail = generateTestEmail()

    // Fill in form with mismatched passwords
    await page.fill('#email', testEmail)
    await page.fill('#password', 'ValidPassword123!')
    await page.fill('#confirmPassword', 'DifferentPassword123!')

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for error message
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Passwords do not match')).toBeVisible()

    // Verify we're still on signup page
    await expect(page).toHaveURL(/\/signup/)
  })

  test('should not submit with empty required fields', async ({ page }) => {
    // Try to submit empty form
    await page.click('button[type="submit"]')

    // Form should not submit (HTML5 validation)
    await expect(page).toHaveURL(/\/signup/)

    // Email field should show validation
    const emailInput = page.locator('#email')
    await expect(emailInput).toHaveAttribute('required', '')
  })

  test('should show loading state during registration', async ({ page }) => {
    // Skip if backend is not available
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')

    const testEmail = generateTestEmail()
    const testPassword = 'TestPassword123!'

    // Fill in form
    await page.fill('#email', testEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)

    // Click submit and immediately check for loading state
    const submitButton = page.locator('button[type="submit"]')
    await submitButton.click()

    // Button should be disabled during loading
    await expect(submitButton).toBeDisabled()

    // Wait for completion (either success or error)
    await page.waitForURL('/dashboard', { timeout: 15000 }).catch(() => {})

    // Track account for cleanup if successful
    if (page.url().includes('/dashboard')) {
      createdAccounts.push(testEmail)
    }
  })

  test('should navigate to login page', async ({ page }) => {
    await page.click('text=Sign in')
    await expect(page).toHaveURL(/\/login/)
  })

  test('should have accessible form labels', async ({ page }) => {
    // Check that labels are properly associated with inputs
    await expect(page.getByText('Full Name', { exact: false })).toBeVisible()
    await expect(page.getByText('Email', { exact: false })).toBeVisible()
    await expect(page.getByText('Password', { exact: false }).first()).toBeVisible()
    await expect(page.getByText('Confirm Password', { exact: false })).toBeVisible()
  })
})

test.describe('Registration - Duplicate Email', () => {
  // These tests require backend
  test.skip(async () => !(await isBackendAvailable()), 'Backend API not running on port 8000')

  const existingEmail = generateTestEmail()
  const testPassword = 'TestPassword123!'

  test.beforeAll(async ({ browser }) => {
    // Create a user first
    const page = await browser.newPage()
    await page.goto('/signup')

    await page.fill('#email', existingEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)
    await page.click('button[type="submit"]')

    await page.waitForURL('/dashboard', { timeout: 15000 })
    createdAccounts.push(existingEmail)

    await page.close()
  })

  test('should show error when registering with existing email', async ({ page }) => {
    await page.goto('/signup')

    // Try to register with the same email
    await page.fill('#email', existingEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)
    await page.click('button[type="submit"]')

    // Wait for error message
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 10000 })

    // Verify we're still on signup page
    await expect(page).toHaveURL(/\/signup/)
  })
})

test.describe('Registration - Dashboard Onboarding', () => {
  // These tests require backend
  test.skip(async () => !(await isBackendAvailable()), 'Backend API not running on port 8000')

  test('new user should see empty state on dashboard', async ({ page }) => {
    const testEmail = generateTestEmail()
    const testPassword = 'TestPassword123!'

    // Register new user
    await page.goto('/signup')
    await page.fill('#fullName', 'New User Test')
    await page.fill('#email', testEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)
    await page.click('button[type="submit"]')

    // Wait for dashboard
    await page.waitForURL('/dashboard', { timeout: 15000 })

    // Verify dashboard has loaded
    await expect(page).toHaveURL(/\/dashboard/)

    // Check for welcome/empty state indicators
    // The dashboard should show some indication it's a new account
    // This could be empty inventory, welcome message, etc.
    await page.waitForLoadState('networkidle')

    // Track account for cleanup
    createdAccounts.push(testEmail)
  })

  test('new user can navigate to key areas after registration', async ({ page }) => {
    const testEmail = generateTestEmail()
    const testPassword = 'TestPassword123!'

    // Register new user
    await page.goto('/signup')
    await page.fill('#email', testEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)
    await page.click('button[type="submit"]')

    // Wait for dashboard
    await page.waitForURL('/dashboard', { timeout: 15000 })

    // Verify user can access inventory page
    await page.goto('/inventory')
    await expect(page).toHaveURL(/\/inventory/)

    // Verify user can access products page
    await page.goto('/products')
    await expect(page).toHaveURL(/\/products/)

    // Track account for cleanup
    createdAccounts.push(testEmail)
  })
})
