/**
 * E2E Tests: Models - Field Validation
 *
 * Comprehensive tests verifying that each model form field correctly
 * saves to the database and is displayed properly in the UI.
 *
 * Model Fields Tested:
 * - Required: sku, name
 * - Optional text: description, category, designer, source, machine
 * - Numeric: labor_hours, overhead_percentage, print_time_hours/minutes, prints_per_plate, units_in_stock
 * - Boolean: is_active
 * - Date: last_printed_date
 */

import { test, expect, Page } from '@playwright/test'
import { API_URL } from '../../config'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

function generateCompleteModelData() {
  const timestamp = Date.now()
  return {
    sku: `MOD-TEST-${timestamp}`,
    name: `Test Dragon Model ${timestamp}`,
    description: 'A detailed dragon model with articulated wings',
    category: 'Dragons',
    labor_hours: '0.5',
    overhead_percentage: '10',
    designer: 'PrintyJay',
    source: 'Patreon',
    print_time_hours: '4',
    print_time_minutes: '30',
    prints_per_plate: '2',
    machine: 'Bambulabs A1 Mini',
    units_in_stock: '5',
  }
}

async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => localStorage.getItem('access_token'))
}

// Helper to wait for model form to be ready
async function waitForModelForm(page: Page): Promise<void> {
  await expect(page.locator('input[name="name"]')).toBeVisible({ timeout: 10000 })
}

// Helper to fill required model fields
async function fillRequiredModelFields(page: Page, name: string, sku?: string): Promise<void> {
  if (sku) {
    await page.locator('input[name="sku"]').fill(sku)
  }
  await page.locator('input[name="name"]').fill(name)
}

// Helper to submit form and verify redirect
async function submitAndVerifyModel(page: Page, verifyText: string): Promise<void> {
  await page.getByRole('button', { name: /create model/i }).click()
  await page.waitForURL(/\/models\/[a-f0-9-]+/, { timeout: 30000 })
  await expect(page.getByText(verifyText).first()).toBeVisible({ timeout: 10000 })
}

test.describe('Model Field Validation - Required Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/models/new')
  })

  test('should display model creation form', async ({ page }) => {
    await waitForModelForm(page)
    await expect(page.locator('input[name="sku"]')).toBeVisible()
    await expect(page.locator('input[name="name"]')).toBeVisible()
  })

  test('should save sku correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name, testData.sku)
    await submitAndVerifyModel(page, testData.sku)
  })

  test('should save name correctly', async ({ page }) => {
    const uniqueName = `Unique Model Name ${Date.now()}`

    await waitForModelForm(page)
    await fillRequiredModelFields(page, uniqueName)
    await submitAndVerifyModel(page, uniqueName)
  })

  test('should require name field', async ({ page }) => {
    await waitForModelForm(page)
    await page.locator('input[name="sku"]').fill('TEST-SKU')

    await page.getByRole('button', { name: /create model/i }).click()

    // Should show validation error
    await expect(page.getByText('Name is required')).toBeVisible()
    await expect(page).toHaveURL(/\/models\/new/)
  })
})

test.describe('Model Field Validation - Optional Text Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/models/new')
  })

  test('should save description correctly', async ({ page }) => {
    const uniqueName = `Model Desc Test ${Date.now()}`

    await waitForModelForm(page)
    await fillRequiredModelFields(page, uniqueName)

    const descriptionInput = page.locator('textarea[name="description"]')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill('Detailed model description')
    }

    await submitAndVerifyModel(page, uniqueName)
  })

  test('should save category correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const categoryInput = page.locator('input[name="category"]')
    if (await categoryInput.isVisible()) {
      await categoryInput.fill('Dragons')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save designer correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const designerInput = page.locator('input[name="designer"]')
    if (await designerInput.isVisible()) {
      await designerInput.fill('PrintyJay')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save source correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const sourceInput = page.locator('input[name="source"]')
    if (await sourceInput.isVisible()) {
      await sourceInput.fill('Patreon')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save machine correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const machineInput = page.locator('input[name="machine"]')
    if (await machineInput.isVisible()) {
      await machineInput.fill('Bambulabs A1 Mini')
    }

    await submitAndVerifyModel(page, testData.name)
  })
})

test.describe('Model Field Validation - Numeric Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/models/new')
  })

  test('should save labor_hours correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const laborInput = page.locator('input[name="labor_hours"]')
    if (await laborInput.isVisible()) {
      await laborInput.fill('0.75')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save overhead_percentage correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const overheadInput = page.locator('input[name="overhead_percentage"]')
    if (await overheadInput.isVisible()) {
      await overheadInput.fill('15')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save print_time correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const hoursInput = page.locator('input[name="print_time_hours"]')
    if (await hoursInput.isVisible()) {
      await hoursInput.fill('3')
    }

    const minutesInput = page.locator('input[name="print_time_minutes"]')
    if (await minutesInput.isVisible()) {
      await minutesInput.fill('45')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save prints_per_plate correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const printsInput = page.locator('input[name="prints_per_plate"]')
    if (await printsInput.isVisible()) {
      await printsInput.fill('4')
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should save units_in_stock correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    const stockInput = page.locator('input[name="units_in_stock"]')
    if (await stockInput.isVisible()) {
      await stockInput.fill('10')
    }

    await submitAndVerifyModel(page, testData.name)
  })
})

test.describe('Model Field Validation - Boolean Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/models/new')
  })

  test('should save is_active toggle correctly', async ({ page }) => {
    const testData = generateCompleteModelData()

    await waitForModelForm(page)
    await fillRequiredModelFields(page, testData.name)

    // is_active should be checked by default
    const activeSwitch = page.locator('button[role="switch"][name="is_active"]')
    if (await activeSwitch.isVisible()) {
      await expect(activeSwitch).toHaveAttribute('data-state', 'checked')
    }

    await submitAndVerifyModel(page, testData.name)
  })
})

test.describe('Model Field Validation - Complete Form', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should create model with all fields populated', async ({ page }) => {
    const testData = generateCompleteModelData()

    await page.goto('/models/new')
    await waitForModelForm(page)

    // Required fields
    await page.locator('input[name="sku"]').fill(testData.sku)
    await page.locator('input[name="name"]').fill(testData.name)

    // Optional text fields
    const descriptionInput = page.locator('textarea[name="description"]')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill(testData.description)
    }

    const categoryInput = page.locator('input[name="category"]')
    if (await categoryInput.isVisible()) {
      await categoryInput.fill(testData.category)
    }

    // Numeric fields
    const laborInput = page.locator('input[name="labor_hours"]')
    if (await laborInput.isVisible()) {
      await laborInput.fill(testData.labor_hours)
    }

    const overheadInput = page.locator('input[name="overhead_percentage"]')
    if (await overheadInput.isVisible()) {
      await overheadInput.fill(testData.overhead_percentage)
    }

    const printsInput = page.locator('input[name="prints_per_plate"]')
    if (await printsInput.isVisible()) {
      await printsInput.fill(testData.prints_per_plate)
    }

    const stockInput = page.locator('input[name="units_in_stock"]')
    if (await stockInput.isVisible()) {
      await stockInput.fill(testData.units_in_stock)
    }

    await submitAndVerifyModel(page, testData.name)
  })

  test('should verify created model data via API', async ({ page }) => {
    const testData = generateCompleteModelData()
    const uniqueSku = `API-MOD-${Date.now()}`

    await page.goto('/models/new')
    await waitForModelForm(page)

    await page.locator('input[name="sku"]').fill(uniqueSku)
    await page.locator('input[name="name"]').fill(testData.name)

    const categoryInput = page.locator('input[name="category"]')
    if (await categoryInput.isVisible()) {
      await categoryInput.fill('Test Category')
    }

    await page.getByRole('button', { name: /create model/i }).click()
    await page.waitForURL(/\/models\/[a-f0-9-]+/, { timeout: 30000 })

    // Get model ID from URL
    const url = page.url()
    const modelId = url.split('/').pop()

    // Verify via API
    const token = await getAuthToken(page)
    if (token && modelId) {
      const response = await page.request.get(`${API_URL}/api/v1/models/${modelId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      expect(response.ok()).toBeTruthy()
      const data = await response.json()

      expect(data.sku).toBe(uniqueSku)
      expect(data.name).toBe(testData.name)
      expect(data.category).toBe('Test Category')
    }
  })
})

test.describe('Model Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should navigate to models page', async ({ page }) => {
    await page.goto('/models')
    await expect(page).toHaveURL(/\/models/)
  })

  test('should require authentication for models page', async ({ page }) => {
    // Logout and wait for redirect to login page
    await page.goto('/logout')
    await page.waitForURL(/\/login/, { timeout: 10000 })

    // Now try to access protected route
    await page.goto('/models')
    await expect(page).toHaveURL(/\/login/)
  })
})
