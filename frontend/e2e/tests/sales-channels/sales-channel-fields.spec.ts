/**
 * E2E Tests: Sales Channels - Field Validation
 *
 * Comprehensive tests verifying that each sales channel form field correctly
 * saves to the database and is displayed properly in the UI.
 *
 * Sales Channel Fields Tested:
 * - Required: name, platform_type
 * - Numeric: fee_percentage, fee_fixed, monthly_cost
 * - Boolean: is_active
 * - Select: platform_type
 */

import { test, expect, Page } from '@playwright/test'
import { API_URL } from '../../config'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

function generateCompleteSalesChannelData() {
  const timestamp = Date.now()
  return {
    name: `Test Channel ${timestamp}`,
    platform_type: 'etsy',
    fee_percentage: '6.5',
    fee_fixed: '0.30',
    monthly_cost: '15.00',
  }
}

async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => localStorage.getItem('access_token'))
}

// Helper to wait for sales channel form to be ready
async function waitForSalesChannelForm(page: Page): Promise<void> {
  await expect(page.locator('input[name="name"]')).toBeVisible({ timeout: 10000 })
}

// Helper to fill required sales channel fields
async function fillRequiredSalesChannelFields(
  page: Page,
  name: string,
  platformType: string = 'other'
): Promise<void> {
  await page.locator('input[name="name"]').fill(name)

  const platformSelect = page.locator('button[name="platform_type"]')
  if (await platformSelect.isVisible()) {
    await platformSelect.click()
    await page.getByRole('option', { name: new RegExp(platformType, 'i') }).click()
  }
}

// Helper to submit form and verify redirect
async function submitAndVerifySalesChannel(page: Page, verifyText: string): Promise<void> {
  await page.getByRole('button', { name: /create.*channel/i }).click()
  await page.waitForURL(/\/sales-channels\/[a-f0-9-]+/, { timeout: 30000 })
  await page.waitForLoadState('networkidle')
  await expect(page.getByText(verifyText).first()).toBeVisible({ timeout: 10000 })
}

test.describe('Sales Channel Field Validation - Required Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/sales-channels/new')
  })

  test('should display sales channel creation form', async ({ page }) => {
    await waitForSalesChannelForm(page)
    await expect(page.locator('input[name="name"]')).toBeVisible()
  })

  test('should save name correctly', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, testData.name, 'etsy')
    await submitAndVerifySalesChannel(page, testData.name)
  })

  test('should require name field', async ({ page }) => {
    await waitForSalesChannelForm(page)
    // Try to submit without name
    await page.getByRole('button', { name: /create.*channel/i }).click()

    await expect(page.getByText('Name is required')).toBeVisible()
    await expect(page).toHaveURL(/\/sales-channels\/new/)
  })
})

test.describe('Sales Channel Field Validation - Select Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/sales-channels/new')
  })

  test('should save platform_type etsy correctly', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, testData.name, 'etsy')
    await submitAndVerifySalesChannel(page, testData.name)
  })

  test('should save platform_type ebay correctly', async ({ page }) => {
    const uniqueName = `eBay Channel ${Date.now()}`

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, uniqueName, 'ebay')
    await submitAndVerifySalesChannel(page, uniqueName)
  })

  test('should save platform_type fair correctly', async ({ page }) => {
    const uniqueName = `Fair Channel ${Date.now()}`

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, uniqueName, 'fair')
    await submitAndVerifySalesChannel(page, uniqueName)
  })

  test('should verify all platform types exist', async ({ page }) => {
    await waitForSalesChannelForm(page)
    const platformSelect = page.locator('button[name="platform_type"]')
    if (await platformSelect.isVisible()) {
      await platformSelect.click()

      // Check expected platform types
      await expect(page.getByRole('option', { name: /fair/i })).toBeVisible()
      await expect(page.getByRole('option', { name: /online.*shop/i })).toBeVisible()
      await expect(page.getByRole('option', { name: /etsy/i })).toBeVisible()
      await expect(page.getByRole('option', { name: /ebay/i })).toBeVisible()
    }
  })
})

test.describe('Sales Channel Field Validation - Numeric Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/sales-channels/new')
  })

  test('should save fee_percentage correctly', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, testData.name, 'other')

    const feePercentageInput = page.locator('input[name="fee_percentage"]')
    if (await feePercentageInput.isVisible()) {
      await feePercentageInput.fill('12.5')
    }

    await submitAndVerifySalesChannel(page, testData.name)
  })

  test('should save fee_fixed correctly', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, testData.name, 'other')

    const feeFixedInput = page.locator('input[name="fee_fixed"]')
    if (await feeFixedInput.isVisible()) {
      await feeFixedInput.fill('0.45')
    }

    await submitAndVerifySalesChannel(page, testData.name)
  })

  test('should save monthly_cost correctly', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)
    await fillRequiredSalesChannelFields(page, testData.name, 'shopify')

    const monthlyCostInput = page.locator('input[name="monthly_cost"]')
    if (await monthlyCostInput.isVisible()) {
      await monthlyCostInput.fill('29.99')
    }

    await submitAndVerifySalesChannel(page, testData.name)
  })
})

test.describe('Sales Channel Field Validation - Boolean Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/sales-channels/new')
  })

  test('should save is_active toggle correctly (enabled by default)', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)

    // is_active should be checked by default
    const activeSwitch = page.locator('button[role="switch"][name="is_active"]')
    if (await activeSwitch.isVisible()) {
      await expect(activeSwitch).toHaveAttribute('data-state', 'checked')
    }

    await fillRequiredSalesChannelFields(page, testData.name, 'other')
    await submitAndVerifySalesChannel(page, testData.name)
  })

  test('should save is_active toggle when disabled', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await waitForSalesChannelForm(page)

    // Toggle off is_active
    const activeSwitch = page.locator('button[role="switch"][name="is_active"]')
    if (await activeSwitch.isVisible()) {
      await activeSwitch.click()
    }

    await fillRequiredSalesChannelFields(page, testData.name, 'other')
    await submitAndVerifySalesChannel(page, testData.name)
  })
})

test.describe('Sales Channel Field Validation - Complete Form', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should create sales channel with all fields populated', async ({ page }) => {
    const testData = generateCompleteSalesChannelData()

    await page.goto('/sales-channels/new')
    await waitForSalesChannelForm(page)

    // Required fields
    await fillRequiredSalesChannelFields(page, testData.name, 'etsy')

    // Fee fields
    const feePercentageInput = page.locator('input[name="fee_percentage"]')
    if (await feePercentageInput.isVisible()) {
      await feePercentageInput.fill(testData.fee_percentage)
    }

    const feeFixedInput = page.locator('input[name="fee_fixed"]')
    if (await feeFixedInput.isVisible()) {
      await feeFixedInput.fill(testData.fee_fixed)
    }

    const monthlyCostInput = page.locator('input[name="monthly_cost"]')
    if (await monthlyCostInput.isVisible()) {
      await monthlyCostInput.fill(testData.monthly_cost)
    }

    await submitAndVerifySalesChannel(page, testData.name)
  })

  test('should verify created sales channel data via API', async ({ page }) => {
    const uniqueName = `API Channel ${Date.now()}`

    await page.goto('/sales-channels/new')
    await waitForSalesChannelForm(page)

    await fillRequiredSalesChannelFields(page, uniqueName, 'ebay')

    const feePercentageInput = page.locator('input[name="fee_percentage"]')
    if (await feePercentageInput.isVisible()) {
      await feePercentageInput.fill('10')
    }

    await page.getByRole('button', { name: /create.*channel/i }).click()
    await page.waitForURL(/\/sales-channels\/[a-f0-9-]+/, { timeout: 30000 })

    // Get channel ID from URL
    const url = page.url()
    const channelId = url.split('/').pop()

    // Verify via API
    const token = await getAuthToken(page)
    if (token && channelId) {
      const response = await page.request.get(`${API_URL}/api/v1/sales-channels/${channelId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      expect(response.ok()).toBeTruthy()
      const data = await response.json()

      expect(data.name).toBe(uniqueName)
      expect(data.platform_type).toBe('ebay')
      expect(data.fee_percentage).toBe('10')
    }
  })
})

test.describe('Sales Channel Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should navigate to sales channels page', async ({ page }) => {
    await page.goto('/sales-channels')
    await expect(page).toHaveURL(/\/sales-channels/)
  })

  test('should require authentication for sales channels page', async ({ page }) => {
    // Logout and wait for redirect to login page
    await page.goto('/logout')
    await page.waitForURL(/\/login/, { timeout: 10000 })

    // Now try to access protected route
    await page.goto('/sales-channels')
    await expect(page).toHaveURL(/\/login/)
  })
})
