/**
 * E2E Test: Multi-Model Production Run with Grouped Materials
 *
 * This test verifies the material grouping functionality when creating a
 * production run with multiple models that share common materials.
 *
 * Flow:
 * 1. Create Model A with BOM (PLA-Blue: 50g, PLA-Red: 30g)
 * 2. Create Model B with BOM (PLA-Red: 40g, PLA-Green: 60g)
 * 3. Create production run selecting both models
 * 4. Verify materials are grouped by spool:
 *    - PLA-Blue: 50g total (used in 1 model)
 *    - PLA-Red: 70g total (used in 2 models)
 *    - PLA-Green: 60g total (used in 1 model)
 * 5. Verify expandable per-model breakdown
 * 6. Apply material suggestions
 * 7. Complete production run successfully
 *
 * PREREQUISITES:
 * - Backend server running on http://localhost:8000
 * - Frontend dev server running on http://localhost:5173
 * - Test user must exist in database with credentials:
 *   - Email: test@example.com (or set TEST_USER_EMAIL env var)
 *   - Password: testpassword (or set TEST_USER_PASSWORD env var)
 *
 * To create test user, run:
 *   cd backend && python scripts/create_test_user.py
 */

import { test, expect, type Page } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from './helpers'

// Test data for Model A
const MODEL_A = {
  name: 'Widget A',
  sku: 'WGT-A-001',
  printTime: '2.5',
  printsPerPlate: '1',
  materials: [
    { color: 'Blue', type: 'PLA', weight: '50' },
    { color: 'Red', type: 'PLA', weight: '30' },
  ],
}

// Test data for Model B
const MODEL_B = {
  name: 'Widget B',
  sku: 'WGT-B-001',
  printTime: '3.0',
  printsPerPlate: '1',
  materials: [
    { color: 'Red', type: 'PLA', weight: '40' },
    { color: 'Green', type: 'PLA', weight: '60' },
  ],
}

// Expected grouped materials (kept for test assertions)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const EXPECTED_GROUPS = {
  'PLA-Blue': { total: 50, models: 1 },
  'PLA-Red': { total: 70, models: 2 }, // 30 + 40
  'PLA-Green': { total: 60, models: 1 },
}

// Helper functions - registerAndLogin is defined above

async function createModelWithBOM(
  page: Page,
  modelData: typeof MODEL_A | typeof MODEL_B
): Promise<string> {
  // Navigate to models page
  await page.goto('/models')
  await page.waitForLoadState('networkidle')

  // Click "New Model" button
  await page.click('button:has-text("New Model")')

  // Wait for form to load
  await expect(page.locator('text=Create New Model')).toBeVisible()

  // Fill basic info
  await page.fill('input[name="name"]', modelData.name)
  await page.fill('input[name="sku"]', modelData.sku)
  await page.fill('input[name="print_time_minutes"]', modelData.printTime)
  await page.fill('input[name="prints_per_plate"]', modelData.printsPerPlate)

  // Navigate to BOM tab
  await page.click('button:has-text("Bill of Materials")')
  await page.waitForTimeout(500) // Wait for tab transition

  // Add materials to BOM
  for (const material of modelData.materials) {
    // Click "Add Material" button
    await page.click('button:has-text("Add Material")')

    // Wait for material row to appear
    await page.waitForSelector(`input[placeholder*="color" i], select[name*="spool"]`)

    // Find the last material row (newest)
    const materialRows = page.locator('[data-testid="material-row"], .material-row').last()

    // Select spool (by color/type or create new)
    const spoolSelect = materialRows.locator('select, input[list]').first()
    await spoolSelect.fill(`${material.type}-${material.color}`)
    await page.waitForTimeout(300)

    // If dropdown appears, select or create
    const createOption = page.locator(`text="${material.type}-${material.color}"`)
    if (await createOption.isVisible()) {
      await createOption.click()
    }

    // Fill weight
    const weightInput = materialRows.locator('input[name*="weight" i], input[placeholder*="weight" i]')
    await weightInput.fill(material.weight)
  }

  // Submit the model
  await page.click('button:has-text("Create Model")')

  // Wait for redirect to model detail page
  await page.waitForURL(/\/models\/[a-f0-9-]+$/, { timeout: 10000 })

  // Extract model ID from URL
  const url = page.url()
  const modelId = url.split('/').pop()!

  return modelId
}

async function deleteModel(page: Page, modelId: string) {
  await page.goto(`/models/${modelId}`)
  const deleteButton = page.locator('button:has-text("Delete")')
  if (await deleteButton.isVisible()) {
    await deleteButton.click()
    await page.click('button:has-text("Confirm")')
    await page.waitForURL('/models')
  }
}

test.describe('Multi-Model Production Run with Grouped Materials', () => {
  let modelAId: string
  let modelBId: string
  let runId: string

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    await registerAndLogin(page)
  })

  test('should group materials by spool across multiple models with correct totals', async ({
    page,
  }) => {
    // ============================================
    // PART 1: Create Model A with BOM
    // ============================================
    modelAId = await createModelWithBOM(page, MODEL_A)

    // Verify Model A created
    await expect(page.locator(`text=${MODEL_A.name}`)).toBeVisible()

    // ============================================
    // PART 2: Create Model B with BOM
    // ============================================
    modelBId = await createModelWithBOM(page, MODEL_B)

    // Verify Model B created
    await expect(page.locator(`text=${MODEL_B.name}`)).toBeVisible()

    // ============================================
    // PART 3: Create production run with both models
    // ============================================

    // Navigate to production runs
    await page.goto('/production-runs')
    await page.waitForLoadState('networkidle')

    // Click "New Production Run" button
    await page.click('button:has-text("New Production Run")')

    // Wait for wizard to load
    await expect(page.locator('text=Step 1 of 4: Basic Info')).toBeVisible()

    // Fill basic info
    await page.fill('input[name="printer"]', 'Prusa i3 MK3S')
    await page.fill('input[name="estimated_print_time_hours"]', '6.0')
    await page.fill('input[name="bed_temperature"]', '60')
    await page.fill('input[name="nozzle_temperature"]', '210')

    // Navigate to Step 2 (Models)
    await page.click('button:has-text("Next")')
    await expect(page.locator('text=Step 2 of 4: Select Models')).toBeVisible()

    // Add Model A
    await page.click('button:has-text("Add Model")')
    await page.waitForTimeout(300)

    // Select Model A from dropdown/search
    const modelASearch = page.locator('input[placeholder*="model" i], input[list*="model" i]').first()
    await modelASearch.fill(MODEL_A.name)
    await page.waitForTimeout(300)
    await page.click(`text="${MODEL_A.name}"`)

    // Set quantity for Model A
    const modelAQuantity = page.locator('input[name*="quantity" i]').first()
    await modelAQuantity.fill('1')

    // Add Model B
    await page.click('button:has-text("Add Model")')
    await page.waitForTimeout(300)

    // Select Model B from dropdown/search
    const modelBSearch = page.locator('input[placeholder*="model" i], input[list*="model" i]').last()
    await modelBSearch.fill(MODEL_B.name)
    await page.waitForTimeout(300)
    await page.click(`text="${MODEL_B.name}"`)

    // Set quantity for Model B
    const modelBQuantity = page.locator('input[name*="quantity" i]').last()
    await modelBQuantity.fill('1')

    // Navigate to Step 3 (Materials)
    await page.click('button:has-text("Next")')
    await expect(page.locator('text=Step 3 of 4: Materials')).toBeVisible()

    // ============================================
    // PART 4: Verify material grouping
    // ============================================

    // Wait for suggestions to load
    await page.waitForSelector('text=Suggested Materials from Models', { timeout: 5000 })

    // Verify PLA-Blue (used in 1 model)
    const blueGroup = page.locator('text=/PLA.*Blue/i').first()
    await expect(blueGroup).toBeVisible()
    await expect(page.locator(`text=50`).or(page.locator(`text=50.0g`))).toBeVisible()
    await expect(page.locator('text=/used in 1 model/i')).toBeVisible()

    // Verify PLA-Red (used in 2 models - grouped)
    const redGroup = page.locator('text=/PLA.*Red/i').first()
    await expect(redGroup).toBeVisible()
    await expect(page.locator(`text=70`).or(page.locator(`text=70.0g`))).toBeVisible()
    await expect(page.locator('text=/used in 2 models/i')).toBeVisible()

    // Verify PLA-Green (used in 1 model)
    const greenGroup = page.locator('text=/PLA.*Green/i').first()
    await expect(greenGroup).toBeVisible()
    await expect(page.locator(`text=60`).or(page.locator(`text=60.0g`))).toBeVisible()

    // ============================================
    // PART 5: Verify expandable per-model breakdown
    // ============================================

    // Expand PLA-Red group to see per-model breakdown
    const redExpandButton = page.locator('button:near(:text("PLA-Red")):has-text("Expand"), button[aria-expanded="false"]:near(:text("PLA-Red"))')
    if (await redExpandButton.isVisible()) {
      await redExpandButton.click()
      await page.waitForTimeout(300)

      // Verify Model A contribution: 30g
      await expect(page.locator(`text=${MODEL_A.name}`).and(page.locator('text=/30.*g/i'))).toBeVisible()

      // Verify Model B contribution: 40g
      await expect(page.locator(`text=${MODEL_B.name}`).and(page.locator('text=/40.*g/i'))).toBeVisible()
    }

    // ============================================
    // PART 6: Apply material suggestions
    // ============================================

    // Click "Apply Suggestions" button
    await page.click('button:has-text("Apply Suggestions")')
    await page.waitForTimeout(500)

    // Verify materials were added to the production run
    await expect(page.locator('text=3 materials added')).toBeVisible()

    // Navigate to Step 4 (Review)
    await page.click('button:has-text("Next")')
    await expect(page.locator('text=Step 4 of 4: Review')).toBeVisible()

    // Verify review shows both models
    await expect(page.locator(`text=${MODEL_A.name}`)).toBeVisible()
    await expect(page.locator(`text=${MODEL_B.name}`)).toBeVisible()

    // Verify review shows grouped materials
    await expect(page.locator('text=/PLA.*Blue/i')).toBeVisible()
    await expect(page.locator('text=/PLA.*Red/i')).toBeVisible()
    await expect(page.locator('text=/PLA.*Green/i')).toBeVisible()

    // ============================================
    // PART 7: Complete production run creation
    // ============================================

    // Submit the production run
    await page.click('button:has-text("Create Production Run")')

    // Wait for redirect to production run detail page
    await page.waitForURL(/\/production-runs\/[a-f0-9-]+$/, { timeout: 10000 })

    // Extract run ID from URL
    const url = page.url()
    runId = url.split('/').pop()!

    // Verify production run created successfully
    await expect(page.locator('text=In Progress')).toBeVisible()
    await expect(page.locator(`text=${MODEL_A.name}`)).toBeVisible()
    await expect(page.locator(`text=${MODEL_B.name}`)).toBeVisible()

    // Verify materials section shows all 3 materials
    await expect(page.locator('text=Filament Materials')).toBeVisible()
    const materialsTable = page.locator('table').filter({ hasText: 'Spool' })
    await expect(materialsTable.locator('tbody tr')).toHaveCount(3)

    // Verify material weights in detail view
    const blueRow = materialsTable.locator('tr:has-text("Blue")')
    await expect(blueRow.locator('text=/50.*g/i')).toBeVisible()

    const redRow = materialsTable.locator('tr:has-text("Red")')
    await expect(redRow.locator('text=/70.*g/i')).toBeVisible()

    const greenRow = materialsTable.locator('tr:has-text("Green")')
    await expect(greenRow.locator('text=/60.*g/i')).toBeVisible()
  })

  test.afterEach(async ({ page }) => {
    // Cleanup: Delete test models and production run
    if (runId) {
      await page.goto(`/production-runs/${runId}`)
      const deleteButton = page.locator('button:has-text("Delete")')
      if (await deleteButton.isVisible()) {
        await deleteButton.click()
        await page.click('button:has-text("Confirm")')
      }
    }

    if (modelAId) {
      await deleteModel(page, modelAId)
    }

    if (modelBId) {
      await deleteModel(page, modelBId)
    }
  })
})
