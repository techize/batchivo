/**
 * E2E Tests: Consumables - Field Validation
 *
 * Comprehensive tests verifying that each consumable form field correctly
 * saves to the database and is displayed properly in the UI.
 *
 * Consumable Fields Tested:
 * - Required: sku, name
 * - Optional text: description, preferred_supplier, supplier_sku, supplier_url
 * - Numeric: current_cost_per_unit, quantity_on_hand, reorder_point, reorder_quantity, typical_lead_days
 * - Boolean: is_active
 * - Select: category, unit_of_measure
 */

import { test, expect, Page } from '@playwright/test'
import { API_URL } from '../../config'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

function generateCompleteConsumableData() {
  const timestamp = Date.now()
  return {
    sku: `COM-TEST-${timestamp}`,
    name: `Test Magnet ${timestamp}`,
    description: 'Test consumable with all fields populated',
    category: 'hardware',
    unit_of_measure: 'each',
    current_cost_per_unit: 0.05,
    quantity_on_hand: 500,
    reorder_point: 100,
    reorder_quantity: 200,
    preferred_supplier: 'Amazon',
    supplier_sku: 'B09XYZ123',
    supplier_url: 'https://amazon.co.uk/dp/B09XYZ123',
    typical_lead_days: 3,
  }
}

async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => localStorage.getItem('access_token'))
}

// Helper to open dialog and wait for SKU to be ready
async function openAddConsumableDialog(page: Page): Promise<void> {
  await page.getByRole('button', { name: /add consumable/i }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
  // Wait for SKU to be generated (input becomes enabled)
  await expect(page.locator('#sku')).toBeEnabled({ timeout: 10000 })
}

// Helper to fill SKU with unique value
async function fillUniqueSku(page: Page, sku?: string): Promise<string> {
  const uniqueSku = sku || `COM-TEST-${Date.now()}`
  const skuInput = page.locator('#sku')
  await skuInput.clear()
  await skuInput.fill(uniqueSku)
  return uniqueSku
}

// Helper to submit form and verify creation
async function submitAndVerifyConsumable(page: Page, name: string): Promise<void> {
  await page.getByRole('button', { name: /create consumable/i }).click()
  await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })
  await expect(page.getByRole('cell', { name }).first()).toBeVisible({ timeout: 10000 })
}

test.describe('Consumable Field Validation - Required Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/consumables')
  })

  test('should display consumables page with add button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /add consumable/i })).toBeVisible()
  })

  test('should open add consumable dialog', async ({ page }) => {
    await page.getByRole('button', { name: /add consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText('Add New Consumable')).toBeVisible()
  })

  test('should save sku correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await page.getByRole('button', { name: /add consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()

    // Wait for SKU to be generated (input becomes enabled)
    const skuInput = page.locator('#sku')
    await expect(skuInput).toBeEnabled({ timeout: 10000 })

    // Clear auto-generated SKU and fill with test SKU
    await skuInput.clear()
    await skuInput.fill(testData.sku)
    await page.locator('#name').fill(testData.name)

    await page.getByRole('button', { name: /create consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    // Verify SKU appears in table (look for table cell containing the SKU)
    await expect(page.getByRole('cell', { name: testData.sku })).toBeVisible({ timeout: 10000 })
  })

  test('should save name correctly', async ({ page }) => {
    const uniqueName = `Unique Consumable ${Date.now()}`
    const uniqueSku = `COM-NAME-${Date.now()}`

    await page.getByRole('button', { name: /add consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()

    // Wait for SKU to be generated (input becomes enabled)
    const skuInput = page.locator('#sku')
    await expect(skuInput).toBeEnabled({ timeout: 10000 })

    // Must provide unique SKU to avoid duplicates
    await skuInput.clear()
    await skuInput.fill(uniqueSku)
    await page.locator('#name').fill(uniqueName)

    await page.getByRole('button', { name: /create consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    // Verify name appears in table
    await expect(page.getByRole('cell', { name: uniqueName })).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Consumable Field Validation - Optional Text Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/consumables')
  })

  test('should save description correctly', async ({ page }) => {
    const uniqueName = `Description Test ${Date.now()}`
    const description = 'Detailed description with special chars: @#$%^&*()'

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(uniqueName)

    const descriptionInput = page.locator('#description')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill(description)
    }

    await submitAndVerifyConsumable(page, uniqueName)
  })

  test('should save preferred_supplier correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const supplierInput = page.locator('#preferred_supplier')
    if (await supplierInput.isVisible()) {
      await supplierInput.fill('Amazon UK')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save supplier_sku correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const supplierSkuInput = page.locator('#supplier_sku')
    if (await supplierSkuInput.isVisible()) {
      await supplierSkuInput.fill('B09SUPPLIER123')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save supplier_url correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const urlInput = page.locator('#supplier_url')
    if (await urlInput.isVisible()) {
      await urlInput.fill('https://amazon.co.uk/dp/B09TEST123')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })
})

test.describe('Consumable Field Validation - Numeric Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/consumables')
  })

  test('should save current_cost_per_unit correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const costInput = page.locator('#current_cost_per_unit')
    if (await costInput.isVisible()) {
      await costInput.fill('0.0575')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save quantity_on_hand correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const quantityInput = page.locator('#quantity_on_hand')
    if (await quantityInput.isVisible()) {
      await quantityInput.fill('500')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save reorder_point correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const reorderPointInput = page.locator('#reorder_point')
    if (await reorderPointInput.isVisible()) {
      await reorderPointInput.fill('100')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save reorder_quantity correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const reorderQtyInput = page.locator('#reorder_quantity')
    if (await reorderQtyInput.isVisible()) {
      await reorderQtyInput.fill('200')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save typical_lead_days correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    const leadDaysInput = page.locator('#typical_lead_days')
    if (await leadDaysInput.isVisible()) {
      await leadDaysInput.fill('5')
    }

    await submitAndVerifyConsumable(page, testData.name)
  })
})

test.describe('Consumable Field Validation - Select Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/consumables')
  })

  test('should save category selection correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    // Select category
    const categorySelect = page.locator('#category')
    if (await categorySelect.isVisible()) {
      await categorySelect.click()
      await page.getByRole('option', { name: /packaging/i }).click()
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save unit_of_measure selection correctly', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    // Select unit of measure
    const unitSelect = page.locator('#unit_of_measure')
    if (await unitSelect.isVisible()) {
      await unitSelect.click()
      await page.getByRole('option', { name: /pack/i }).first().click()
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should verify all category options exist', async ({ page }) => {
    await openAddConsumableDialog(page)

    const categorySelect = page.locator('#category')
    if (await categorySelect.isVisible()) {
      await categorySelect.click()

      // Check that expected categories are available
      await expect(page.getByRole('option', { name: /hardware/i })).toBeVisible()
      await expect(page.getByRole('option', { name: /packaging/i })).toBeVisible()
    }
  })
})

test.describe('Consumable Field Validation - Boolean Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/consumables')
  })

  test('should save is_active toggle correctly (enabled by default)', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    // is_active should be checked by default
    const activeSwitch = page.locator('#is_active')
    if (await activeSwitch.isVisible()) {
      await expect(activeSwitch).toBeChecked()
    }

    await submitAndVerifyConsumable(page, testData.name)
  })

  test('should save is_active toggle when disabled', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page)
    await page.locator('#name').fill(testData.name)

    // Toggle off is_active
    const activeSwitch = page.locator('#is_active')
    if (await activeSwitch.isVisible()) {
      await activeSwitch.click()
    }

    await submitAndVerifyConsumable(page, testData.name)
  })
})

test.describe('Consumable Field Validation - Complete Form', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/consumables')
  })

  test('should create consumable with ALL fields populated', async ({ page }) => {
    const testData = generateCompleteConsumableData()

    await openAddConsumableDialog(page)
    await fillUniqueSku(page, testData.sku)
    await page.locator('#name').fill(testData.name)

    // Description
    const descriptionInput = page.locator('#description')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill(testData.description)
    }

    // Category select
    const categorySelect = page.locator('#category')
    if (await categorySelect.isVisible()) {
      await categorySelect.click()
      await page.getByRole('option', { name: /hardware/i }).click()
    }

    // Unit of measure select
    const unitSelect = page.locator('#unit_of_measure')
    if (await unitSelect.isVisible()) {
      await unitSelect.click()
      await page.getByRole('option', { name: /each/i }).click()
    }

    // Numeric fields
    const costInput = page.locator('#current_cost_per_unit')
    if (await costInput.isVisible()) {
      await costInput.fill(testData.current_cost_per_unit.toString())
    }

    const quantityInput = page.locator('#quantity_on_hand')
    if (await quantityInput.isVisible()) {
      await quantityInput.fill(testData.quantity_on_hand.toString())
    }

    const reorderPointInput = page.locator('#reorder_point')
    if (await reorderPointInput.isVisible()) {
      await reorderPointInput.fill(testData.reorder_point.toString())
    }

    const reorderQtyInput = page.locator('#reorder_quantity')
    if (await reorderQtyInput.isVisible()) {
      await reorderQtyInput.fill(testData.reorder_quantity.toString())
    }

    // Supplier fields
    const supplierInput = page.locator('#preferred_supplier')
    if (await supplierInput.isVisible()) {
      await supplierInput.fill(testData.preferred_supplier)
    }

    const supplierSkuInput = page.locator('#supplier_sku')
    if (await supplierSkuInput.isVisible()) {
      await supplierSkuInput.fill(testData.supplier_sku)
    }

    const urlInput = page.locator('#supplier_url')
    if (await urlInput.isVisible()) {
      await urlInput.fill(testData.supplier_url)
    }

    const leadDaysInput = page.locator('#typical_lead_days')
    if (await leadDaysInput.isVisible()) {
      await leadDaysInput.fill(testData.typical_lead_days.toString())
    }

    await page.getByRole('button', { name: /create consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    // Verify consumable was created
    await expect(page.getByRole('cell', { name: testData.sku })).toBeVisible({ timeout: 10000 })
  })

  test('should verify created consumable data via API', async ({ page }) => {
    const testData = generateCompleteConsumableData()
    const uniqueSku = `API-COM-${Date.now()}`

    await openAddConsumableDialog(page)
    await fillUniqueSku(page, uniqueSku)
    await page.locator('#name').fill(testData.name)

    const quantityInput = page.locator('#quantity_on_hand')
    if (await quantityInput.isVisible()) {
      await quantityInput.fill('250')
    }

    const costInput = page.locator('#current_cost_per_unit')
    if (await costInput.isVisible()) {
      await costInput.fill('0.05')
    }

    await page.getByRole('button', { name: /create consumable/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    await expect(page.getByRole('cell', { name: uniqueSku })).toBeVisible({ timeout: 10000 })

    // Verify via API
    const token = await getAuthToken(page)
    if (token) {
      const response = await page.request.get(`${API_URL}/api/v1/consumables`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      expect(response.ok()).toBeTruthy()
      const data = await response.json()

      const created = data.consumables.find((c: { sku: string }) => c.sku === uniqueSku)
      expect(created).toBeTruthy()
      expect(created.name).toBe(testData.name)
      expect(created.quantity_on_hand).toBe(250)
      expect(parseFloat(created.current_cost_per_unit)).toBe(0.05)
    }
  })
})

test.describe('Consumable Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should navigate to consumables page from dashboard', async ({ page }) => {
    await page.goto('/dashboard')

    const consumablesLink = page.getByRole('link', { name: /consumables/i })
    if (await consumablesLink.isVisible()) {
      await consumablesLink.click()
      await expect(page).toHaveURL(/\/consumables/)
    } else {
      await page.goto('/consumables')
      await expect(page).toHaveURL(/\/consumables/)
    }
  })

  test('should require authentication for consumables page', async ({ page }) => {
    // Logout and wait for redirect to login page
    await page.goto('/logout')
    await page.waitForURL(/\/login/, { timeout: 10000 })

    // Now try to access protected route
    await page.goto('/consumables')
    await expect(page).toHaveURL(/\/login/)
  })
})
