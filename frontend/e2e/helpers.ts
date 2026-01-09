/**
 * E2E Test Helpers
 *
 * Shared helper functions for E2E tests including authentication
 * with retry logic for rate limiting.
 */

import { Page } from '@playwright/test'
import { HEALTH_URL } from './config'

/**
 * Check if the backend API is available
 */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    const response = await fetch(HEALTH_URL)
    return response.ok
  } catch {
    return false
  }
}

/**
 * Register a new user and login
 *
 * Creates a unique user for test isolation.
 * Includes retry logic with exponential backoff to handle rate limiting.
 *
 * Rate limit is 5/minute for auth endpoints, so we retry with delays.
 *
 * @param page - Playwright page object
 * @param maxRetries - Maximum number of retry attempts (default: 3)
 * @returns The email of the created user
 */
export async function registerAndLogin(page: Page, maxRetries: number = 3): Promise<string> {
  const testPassword = 'TestPassword123!'

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const testEmail = `test-${Date.now()}-${Math.random().toString(36).substring(7)}@example.com`

    await page.goto('/signup')
    await page.fill('#email', testEmail)
    await page.fill('#password', testPassword)
    await page.fill('#confirmPassword', testPassword)
    await page.click('button[type="submit"]')

    // Wait for either dashboard (success) or error message (rate limited)
    const result = await Promise.race([
      page.waitForURL('/dashboard', { timeout: 15000 }).then(() => 'success'),
      page.locator('text=Registration failed').waitFor({ timeout: 5000 }).then(() => 'rate_limited'),
    ]).catch(() => 'timeout')

    if (result === 'success') {
      return testEmail
    }

    if (result === 'rate_limited' && attempt < maxRetries) {
      // Wait with exponential backoff before retrying
      // Rate limit is 5/minute, so we need to wait a bit
      const waitTime = Math.min(5000 * Math.pow(2, attempt), 30000) // 5s, 10s, 20s (max 30s)
      console.log(`Rate limited. Waiting ${waitTime / 1000}s before retry ${attempt + 1}/${maxRetries}`)
      await page.waitForTimeout(waitTime)
      continue
    }

    // If timeout or all retries exhausted, throw
    if (attempt === maxRetries) {
      throw new Error(`Registration failed after ${maxRetries} retries. Rate limit may be exceeded.`)
    }
  }

  throw new Error('Registration failed unexpectedly')
}

/**
 * Create a test user and return credentials (for login tests)
 *
 * Registers a user, then logs out so the login flow can be tested.
 *
 * @param page - Playwright page object
 * @returns Object with email and password
 */
export async function createTestUser(page: Page): Promise<{ email: string; password: string }> {
  const email = await registerAndLogin(page)
  const password = 'TestPassword123!'

  // Logout to test login flow
  await page.goto('/logout')
  await page.waitForURL('/login', { timeout: 10000 })

  return { email, password }
}

/**
 * Wait for page to be fully loaded and stable
 */
export async function waitForPageStable(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle')
}

/**
 * Click element and verify navigation
 */
export async function clickAndNavigate(
  page: Page,
  selector: string,
  expectedUrl: RegExp,
  timeout: number = 10000
): Promise<void> {
  await page.click(selector)
  await page.waitForURL(expectedUrl, { timeout })
  await waitForPageStable(page)
}
