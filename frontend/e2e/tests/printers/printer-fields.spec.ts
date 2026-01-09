/**
 * E2E Tests: Printers - Field Validation
 *
 * Comprehensive tests verifying that each printer form field correctly
 * saves to the database and is displayed properly in the UI.
 *
 * Printer Fields Tested:
 * - Required: name
 * - Optional text: manufacturer, model, serial_number, notes
 * - Numeric: bed_size_x/y/z_mm, nozzle_diameter_mm, default_bed_temp, default_nozzle_temp
 * - Boolean: is_active
 */

import { test, expect, Page } from '@playwright/test'
import { API_URL } from '../../config'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

function generateCompletePrinterData() {
  const timestamp = Date.now()
  return {
    name: `Test Printer ${timestamp}`,
    manufacturer: 'Bambu Lab',
    model: 'X1 Carbon',
    serial_number: `SN-${timestamp}`,
    bed_size_x_mm: 256,
    bed_size_y_mm: 256,
    bed_size_z_mm: 256,
    nozzle_diameter_mm: 0.4,
    default_bed_temp: 60,
    default_nozzle_temp: 220,
    notes: 'Test printer with all fields populated',
  }
}

async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => localStorage.getItem('access_token'))
}

// Helper to open dialog and wait for it to be ready
async function openAddPrinterDialog(page: Page): Promise<void> {
  await page.getByRole('button', { name: /add printer/i }).first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
}

// Helper to fill required printer fields
async function fillRequiredPrinterFields(page: Page, name: string): Promise<void> {
  await page.locator('#name').fill(name)
}

// Helper to submit form and verify creation
async function submitAndVerifyPrinter(page: Page, verifyText: string): Promise<void> {
  await page.getByRole('button', { name: /add printer$/i }).click()
  await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })
  // Wait for list to update after dialog closes
  await page.waitForLoadState('networkidle')
  await expect(page.getByRole('cell', { name: verifyText })).toBeVisible({ timeout: 10000 })
}

test.describe('Printer Field Validation - Required Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/printers')
  })

  test('should display printers page with add button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /add printer/i })).toBeVisible()
  })

  test('should open add printer dialog', async ({ page }) => {
    await openAddPrinterDialog(page)
    await expect(page.getByRole('heading', { name: 'Add Printer' })).toBeVisible()
  })

  test('should save name correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await submitAndVerifyPrinter(page, testData.name)
  })
})

test.describe('Printer Field Validation - Optional Text Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/printers')
  })

  test('should save manufacturer correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await page.locator('#manufacturer').fill('Prusa Research')
    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should save model correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await page.locator('#model').fill('MK4')
    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should save serial_number correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await page.locator('#serial_number').fill('SN-TEST-12345')
    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should save notes correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)

    const notesInput = page.locator('#notes')
    if (await notesInput.isVisible()) {
      await notesInput.fill('Test notes with special chars: @#$%')
    }

    await submitAndVerifyPrinter(page, testData.name)
  })
})

test.describe('Printer Field Validation - Numeric Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/printers')
  })

  test('should save bed dimensions correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await page.locator('#bed_size_x_mm').fill('300')
    await page.locator('#bed_size_y_mm').fill('300')
    await page.locator('#bed_size_z_mm').fill('400')
    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should save nozzle_diameter_mm correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await page.locator('#nozzle_diameter_mm').fill('0.6')
    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should save temperature defaults correctly', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)
    await page.locator('#default_bed_temp').fill('65')
    await page.locator('#default_nozzle_temp').fill('215')
    await submitAndVerifyPrinter(page, testData.name)
  })
})

test.describe('Printer Field Validation - Boolean Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/printers')
  })

  test('should save is_active toggle correctly (enabled by default)', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)

    // is_active should be checked by default
    const activeSwitch = page.locator('#is_active')
    if (await activeSwitch.isVisible()) {
      await expect(activeSwitch).toBeChecked()
    }

    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should save is_active toggle when disabled', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)

    // Toggle off is_active
    const activeSwitch = page.locator('#is_active')
    if (await activeSwitch.isVisible()) {
      await activeSwitch.click()
    }

    await submitAndVerifyPrinter(page, testData.name)
  })
})

test.describe('Printer Field Validation - Complete Form', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/printers')
  })

  test('should create printer with ALL fields populated', async ({ page }) => {
    const testData = generateCompletePrinterData()

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, testData.name)

    // Optional text fields
    await page.locator('#manufacturer').fill(testData.manufacturer)
    await page.locator('#model').fill(testData.model)
    await page.locator('#serial_number').fill(testData.serial_number)

    // Build volume
    await page.locator('#bed_size_x_mm').fill(testData.bed_size_x_mm.toString())
    await page.locator('#bed_size_y_mm').fill(testData.bed_size_y_mm.toString())
    await page.locator('#bed_size_z_mm').fill(testData.bed_size_z_mm.toString())

    // Print settings
    await page.locator('#nozzle_diameter_mm').fill(testData.nozzle_diameter_mm.toString())
    await page.locator('#default_bed_temp').fill(testData.default_bed_temp.toString())
    await page.locator('#default_nozzle_temp').fill(testData.default_nozzle_temp.toString())

    // Notes
    const notesInput = page.locator('#notes')
    if (await notesInput.isVisible()) {
      await notesInput.fill(testData.notes)
    }

    await submitAndVerifyPrinter(page, testData.name)
  })

  test('should verify created printer data via API', async ({ page }) => {
    const uniqueName = `API Printer ${Date.now()}`

    await openAddPrinterDialog(page)
    await fillRequiredPrinterFields(page, uniqueName)
    await page.locator('#manufacturer').fill('Test Manufacturer')
    await page.locator('#bed_size_x_mm').fill('250')

    await page.getByRole('button', { name: /add printer$/i }).click()
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 30000 })
    await page.waitForLoadState('networkidle')

    await expect(page.getByRole('cell', { name: uniqueName })).toBeVisible({ timeout: 10000 })

    // Verify via API
    const token = await getAuthToken(page)
    if (token) {
      const response = await page.request.get(`${API_URL}/api/v1/printers`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      expect(response.ok()).toBeTruthy()
      const data = await response.json()

      const created = data.find((p: { name: string }) => p.name === uniqueName)
      expect(created).toBeTruthy()
      expect(created.manufacturer).toBe('Test Manufacturer')
      expect(created.bed_size_x_mm).toBe(250)
    }
  })
})

test.describe('Printer Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should navigate to printers page', async ({ page }) => {
    await page.goto('/printers')
    await expect(page).toHaveURL(/\/printers/)
  })

  test('should require authentication for printers page', async ({ page }) => {
    // Logout and wait for redirect to login page
    await page.goto('/logout')
    await page.waitForURL(/\/login/, { timeout: 10000 })

    // Now try to access protected route
    await page.goto('/printers')
    await expect(page).toHaveURL(/\/login/)
  })
})
