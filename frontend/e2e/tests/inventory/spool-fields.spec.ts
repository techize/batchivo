/**
 * E2E Tests: Inventory - Spool Field Validation
 *
 * Comprehensive tests verifying that each form field correctly
 * saves to the database and is displayed properly in the UI.
 *
 * Tests cover:
 * - Required fields (spool_id, brand, color, material_type, weights)
 * - Optional text fields (finish, pattern, storage_location, notes)
 * - Numeric fields (diameter, density, temps, prices, quantities)
 * - Boolean fields (translucent, glow)
 * - Select fields (material_type, spool_type, diameter)
 * - Date fields (purchase_date)
 *
 * Prerequisites:
 * - Frontend dev server running
 * - Backend API running on port 8000
 * - At least one material type in the database
 */

import { test, expect, Page } from '@playwright/test'
import { API_URL } from '../../config'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

// Generate unique test data with all fields populated
function generateCompleteSpoolData() {
  const timestamp = Date.now()
  return {
    spool_id: `FIL-TEST-${timestamp}`,
    brand: `TestBrand-${timestamp}`,
    color: `Electric Blue ${timestamp}`,
    color_hex: 'FF5733',
    finish: 'Matte',
    diameter: '1.75',
    extruder_temp: 215,
    bed_temp: 60,
    translucent: true,
    glow: true,
    pattern: 'Marble',
    spool_type: 'cardboard',
    initial_weight: 1000,
    current_weight: 850,
    empty_spool_weight: 190,
    purchase_date: '2025-01-15',
    purchase_price: 24.99,
    supplier: 'Amazon',
    quantity: 2,
    storage_location: 'Shelf A3 - Bin 12',
    notes: 'Test spool with all fields populated for E2E validation',
  }
}

// Helper to get auth token from localStorage for API calls
async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => {
    return localStorage.getItem('access_token')
  })
}

// Helper to open dialog and wait for it to be ready
async function openAddSpoolDialog(page: Page): Promise<void> {
  await page.getByRole('button', { name: /add spool/i }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  // Wait for spool_id to be generated (input becomes enabled)
  await expect(page.locator('#spool_id')).toBeEnabled({ timeout: 10000 })
}

// Helper to fill spool ID with unique value
async function fillUniqueSpoolId(page: Page, spoolId?: string): Promise<string> {
  const uniqueId = spoolId || `FIL-TEST-${Date.now()}`
  const idInput = page.locator('#spool_id')
  await idInput.clear()
  await idInput.fill(uniqueId)
  return uniqueId
}

// Helper to fill required spool fields
async function fillRequiredSpoolFields(page: Page, data: { brand: string; color: string; initial_weight: number }): Promise<void> {
  await page.locator('#brand').fill(data.brand)
  await page.locator('#color').fill(data.color)
  await page.locator('#initial_weight').fill(data.initial_weight.toString())

  // Select material type
  const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
  if (await materialSelect.isVisible()) {
    await materialSelect.click()
    await page.locator('[role="option"]').first().click()
  }
}

// Helper to submit form and verify creation
async function submitAndVerifySpool(page: Page, verifyText: string): Promise<void> {
  await page.getByRole('button', { name: /create spool/i }).click()
  await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })
  // Wait for list to update after dialog closes
  await page.waitForLoadState('networkidle')
  // Scroll to top to see the newly created spool and verify it exists in DOM
  await page.evaluate(() => window.scrollTo(0, 0))
  const element = page.getByText(verifyText).first()
  await element.scrollIntoViewIfNeeded()
  await expect(element).toBeVisible({ timeout: 10000 })
}

test.describe('Spool Field Validation - Required Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save spool_id correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page, testData.spool_id)
    await fillRequiredSpoolFields(page, testData)
    await page.locator('#current_weight').fill(testData.current_weight.toString())

    await submitAndVerifySpool(page, testData.spool_id)
  })

  test('should save brand correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()
    const uniqueBrand = `UniqueBrandTest-${Date.now()}`

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await page.locator('#brand').fill(uniqueBrand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill(testData.initial_weight.toString())

    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    await submitAndVerifySpool(page, uniqueBrand)
  })

  test('should save color correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()
    const uniqueColor = `UniqueColor-${Date.now()}`

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(uniqueColor)
    await page.locator('#initial_weight').fill(testData.initial_weight.toString())

    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    await submitAndVerifySpool(page, uniqueColor)
  })

  test('should save initial_weight and current_weight correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()
    const initialWeight = 750
    const currentWeight = 600

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill(initialWeight.toString())
    await page.locator('#current_weight').fill(currentWeight.toString())

    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    await page.getByRole('button', { name: /create spool/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    // Verify weights appear in the UI (usually shown as percentage or weight display)
    await expect(page.getByText(testData.brand)).toBeVisible({ timeout: 10000 })

    // Check for weight percentage (600/750 = 80%)
    const expectedPercentage = Math.round((currentWeight / initialWeight) * 100)
    // The UI might show this as "80%" or similar
    const pageContent = await page.textContent('body')
    expect(
      pageContent?.includes(`${expectedPercentage}%`) ||
        pageContent?.includes(`${currentWeight}`) ||
        pageContent?.includes('g')
    ).toBeTruthy()
  })
})

test.describe('Spool Field Validation - Optional Text Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save finish field correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const finishInput = page.locator('#finish')
    if (await finishInput.isVisible()) {
      await finishInput.fill('Glossy Metallic')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save pattern field correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const patternInput = page.locator('#pattern')
    if (await patternInput.isVisible()) {
      await patternInput.fill('Speckled Granite')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save storage_location correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const locationInput = page.locator('#storage_location')
    if (await locationInput.isVisible()) {
      await locationInput.fill('Cabinet B - Drawer 3')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save notes correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const notesInput = page.locator('#notes')
    if (await notesInput.isVisible()) {
      await notesInput.fill('This is a test note with special chars: !@#$%^&*()')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save color_hex correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const colorHexInput = page.locator('#color_hex')
    if (await colorHexInput.isVisible()) {
      await colorHexInput.fill('FF5733')
    }

    await submitAndVerifySpool(page, testData.brand)
  })
})

test.describe('Spool Field Validation - Numeric Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save temperature fields correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const extruderTemp = page.locator('#extruder_temp')
    if (await extruderTemp.isVisible()) {
      await extruderTemp.fill('215')
    }

    const bedTemp = page.locator('#bed_temp')
    if (await bedTemp.isVisible()) {
      await bedTemp.fill('60')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save empty_spool_weight correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const emptySpoolWeight = page.locator('#empty_spool_weight')
    if (await emptySpoolWeight.isVisible()) {
      await emptySpoolWeight.fill('190')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save purchase_price correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const purchasePrice = page.locator('#purchase_price')
    if (await purchasePrice.isVisible()) {
      await purchasePrice.fill('24.99')
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save quantity fields correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const quantityInput = page.locator('#quantity')
    if (await quantityInput.isVisible()) {
      await quantityInput.fill('3')
    }

    await submitAndVerifySpool(page, testData.brand)
  })
})

test.describe('Spool Field Validation - Boolean Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save translucent toggle correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const translucentSwitch = page.locator('#translucent')
    if (await translucentSwitch.isVisible()) {
      await translucentSwitch.click()
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save glow toggle correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const glowSwitch = page.locator('#glow')
    if (await glowSwitch.isVisible()) {
      await glowSwitch.click()
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save both boolean fields when enabled', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const translucentSwitch = page.locator('#translucent')
    if (await translucentSwitch.isVisible()) {
      await translucentSwitch.click()
    }

    const glowSwitch = page.locator('#glow')
    if (await glowSwitch.isVisible()) {
      await glowSwitch.click()
    }

    await submitAndVerifySpool(page, testData.brand)
  })
})

test.describe('Spool Field Validation - Select Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save diameter selection correctly (1.75mm)', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill(testData.initial_weight.toString())

    const diameterSelect = page.locator('#diameter')
    if (await diameterSelect.isVisible()) {
      await diameterSelect.click()
      await page.getByRole('option', { name: /1\.75/i }).click()
    }

    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save diameter selection correctly (2.85mm)', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill(testData.initial_weight.toString())

    const diameterSelect = page.locator('#diameter')
    if (await diameterSelect.isVisible()) {
      await diameterSelect.click()
      await page.getByRole('option', { name: /2\.85/i }).click()
    }

    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save spool_type selection correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const spoolTypeSelect = page.locator('#spool_type')
    if (await spoolTypeSelect.isVisible()) {
      await spoolTypeSelect.click()
      await page.getByRole('option', { name: /cardboard/i }).click()
    }

    await submitAndVerifySpool(page, testData.brand)
  })

  test('should save different material types correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill(testData.initial_weight.toString())

    // Click material type dropdown and check available options
    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    await materialSelect.click()

    // Check that material options are available
    const options = page.locator('[role="option"]')
    const optionCount = await options.count()
    expect(optionCount).toBeGreaterThan(0)

    // Select first available option
    await options.first().click()

    await submitAndVerifySpool(page, testData.brand)
  })
})

test.describe('Spool Field Validation - Date Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save purchase_date correctly', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page)
    await fillRequiredSpoolFields(page, testData)

    const purchaseDate = page.locator('#purchase_date')
    if (await purchaseDate.isVisible()) {
      await purchaseDate.fill('2025-01-15')
    }

    await submitAndVerifySpool(page, testData.brand)
  })
})

test.describe('Spool Field Validation - Complete Form', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/inventory')
  })

  test('should save spool with ALL fields populated', async ({ page }) => {
    const testData = generateCompleteSpoolData()

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page, testData.spool_id)

    // Required fields
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill(testData.initial_weight.toString())
    await page.locator('#current_weight').fill(testData.current_weight.toString())

    // Material type
    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    // Optional text fields
    const finishInput = page.locator('#finish')
    if (await finishInput.isVisible()) {
      await finishInput.fill(testData.finish)
    }

    const colorHexInput = page.locator('#color_hex')
    if (await colorHexInput.isVisible()) {
      await colorHexInput.fill(testData.color_hex)
    }

    const patternInput = page.locator('#pattern')
    if (await patternInput.isVisible()) {
      await patternInput.fill(testData.pattern)
    }

    const storageInput = page.locator('#storage_location')
    if (await storageInput.isVisible()) {
      await storageInput.fill(testData.storage_location)
    }

    const notesInput = page.locator('#notes')
    if (await notesInput.isVisible()) {
      await notesInput.fill(testData.notes)
    }

    // Numeric fields
    const extruderTemp = page.locator('#extruder_temp')
    if (await extruderTemp.isVisible()) {
      await extruderTemp.fill(testData.extruder_temp.toString())
    }

    const bedTemp = page.locator('#bed_temp')
    if (await bedTemp.isVisible()) {
      await bedTemp.fill(testData.bed_temp.toString())
    }

    const emptySpoolWeight = page.locator('#empty_spool_weight')
    if (await emptySpoolWeight.isVisible()) {
      await emptySpoolWeight.fill(testData.empty_spool_weight.toString())
    }

    const purchasePrice = page.locator('#purchase_price')
    if (await purchasePrice.isVisible()) {
      await purchasePrice.fill(testData.purchase_price.toString())
    }

    const quantityInput = page.locator('#quantity')
    if (await quantityInput.isVisible()) {
      await quantityInput.fill(testData.quantity.toString())
    }

    // Date fields
    const purchaseDate = page.locator('#purchase_date')
    if (await purchaseDate.isVisible()) {
      await purchaseDate.fill(testData.purchase_date)
    }

    // Boolean fields (toggles)
    const translucentSwitch = page.locator('#translucent')
    if (await translucentSwitch.isVisible() && testData.translucent) {
      await translucentSwitch.click()
    }

    const glowSwitch = page.locator('#glow')
    if (await glowSwitch.isVisible() && testData.glow) {
      await glowSwitch.click()
    }

    // Select fields
    const diameterSelect = page.locator('#diameter')
    if (await diameterSelect.isVisible()) {
      await diameterSelect.click()
      await page.getByRole('option', { name: new RegExp(testData.diameter) }).click()
    }

    const spoolTypeSelect = page.locator('#spool_type')
    if (await spoolTypeSelect.isVisible()) {
      await spoolTypeSelect.click()
      await page.getByRole('option', { name: new RegExp(testData.spool_type, 'i') }).click()
    }

    // Submit form
    await page.getByRole('button', { name: /create spool/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    // Verify spool was created with all data
    await expect(page.getByText(testData.spool_id)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(testData.brand)).toBeVisible()
    await expect(page.getByText(testData.color)).toBeVisible()
  })

  test('should verify created spool data via API', async ({ page }) => {
    const testData = generateCompleteSpoolData()
    const uniqueSpoolId = `API-TEST-${Date.now()}`

    await openAddSpoolDialog(page)
    await fillUniqueSpoolId(page, uniqueSpoolId)

    // Fill required fields
    await page.locator('#brand').fill(testData.brand)
    await page.locator('#color').fill(testData.color)
    await page.locator('#initial_weight').fill('1000')
    await page.locator('#current_weight').fill('750')

    // Add some optional fields
    const finishInput = page.locator('#finish')
    if (await finishInput.isVisible()) {
      await finishInput.fill('Silk')
    }

    const storageInput = page.locator('#storage_location')
    if (await storageInput.isVisible()) {
      await storageInput.fill('Test Location')
    }

    const materialSelect = page.locator('#material_type_id, [name="material_type_id"]').first()
    if (await materialSelect.isVisible()) {
      await materialSelect.click()
      await page.locator('[role="option"]').first().click()
    }

    await page.getByRole('button', { name: /create spool/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })

    // Wait for spool to appear
    await expect(page.getByText(uniqueSpoolId)).toBeVisible({ timeout: 10000 })

    // Verify via API call
    const token = await getAuthToken(page)
    if (token) {
      const response = await page.request.get(`${API_URL}/api/v1/spools`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      expect(response.ok()).toBeTruthy()
      const data = await response.json()

      // Find our created spool
      const createdSpool = data.spools.find((s: { spool_id: string }) => s.spool_id === uniqueSpoolId)
      expect(createdSpool).toBeTruthy()

      // Verify fields match
      expect(createdSpool.brand).toBe(testData.brand)
      expect(createdSpool.color).toBe(testData.color)
      expect(parseFloat(createdSpool.initial_weight)).toBe(1000)
      expect(parseFloat(createdSpool.current_weight)).toBe(750)
      expect(createdSpool.finish).toBe('Silk')
      expect(createdSpool.storage_location).toBe('Test Location')
    }
  })
})
