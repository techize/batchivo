/**
 * E2E Test: Production Run Auto-Population from Model BOM
 *
 * This test verifies the complete user flow for creating a production run
 * with auto-populated materials from a Model's Bill of Materials (BOM).
 *
 * Flow:
 * 1. Create a model with BOM materials (2 spools with different weights)
 * 2. Navigate to production runs
 * 3. Create new production run
 * 4. Select the model in Step 2
 * 5. Navigate to Step 3 (Materials)
 * 6. Verify suggested materials appear with correct weights
 * 7. Apply suggestions
 * 8. Verify materials are added to form
 * 9. Complete and submit the production run
 */

import { test, expect, type Page } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from './helpers'

// Test data
const TEST_MODEL = {
  sku: `AUTO-TEST-${Date.now()}`,
  name: 'E2E Test Widget',
  description: 'Auto-population test model',
  category: 'Test',
  laborHours: '1.0',
  overheadPercentage: '25',
  printsPerPlate: 5,
  printTimeMinutes: 120,
  machine: 'Prusa i3 MK3S',
}

const TEST_SPOOLS = {
  spool1: {
    name: 'eSun - PLA - Blue',
    materialType: 'PLA',
    color: 'Blue',
    weight: 50.5, // grams per item
  },
  spool2: {
    name: 'Polymaker - PLA - Red',
    materialType: 'PLA',
    color: 'Red',
    weight: 30.0, // grams per item
  },
}

// Helper functions - registerAndLogin is defined above

async function createTestModel(page: Page): Promise<string> {
  // Navigate to models page
  await page.goto('/models')
  await page.waitForLoadState('networkidle')

  // Click "New Model" button
  await page.click('button:has-text("New Model")')

  // Fill in basic model information
  await page.fill('input[name="sku"]', TEST_MODEL.sku)
  await page.fill('input[name="name"]', TEST_MODEL.name)
  await page.fill('textarea[name="description"]', TEST_MODEL.description)
  await page.fill('input[name="category"]', TEST_MODEL.category)
  await page.fill('input[name="labor_hours"]', TEST_MODEL.laborHours)
  await page.fill('input[name="overhead_percentage"]', TEST_MODEL.overheadPercentage)
  await page.fill('input[name="prints_per_plate"]', TEST_MODEL.printsPerPlate.toString())
  await page.fill('input[name="print_time_minutes"]', TEST_MODEL.printTimeMinutes.toString())
  await page.fill('input[name="machine"]', TEST_MODEL.machine)

  // Submit model creation
  await page.click('button[type="submit"]:has-text("Create Model")')

  // Wait for redirect to model detail page
  await page.waitForURL(/\/models\/[a-f0-9-]+$/, { timeout: 10000 })

  // Extract model ID from URL
  const url = page.url()
  const modelId = url.split('/').pop()!

  // Add BOM materials (assuming there's an "Add Material" section)
  // Note: This section may need adjustment based on actual UI implementation
  await page.click('button:has-text("Add Material")')

  // Add first spool (Blue PLA)
  await page.selectOption('select[name="spool_id"]', { label: TEST_SPOOLS.spool1.name })
  await page.fill('input[name="weight_grams"]', TEST_SPOOLS.spool1.weight.toString())
  await page.click('button:has-text("Add to BOM")')

  // Wait for material to be added
  await expect(page.locator(`text=${TEST_SPOOLS.spool1.name}`)).toBeVisible()

  // Add second spool (Red PLA)
  await page.click('button:has-text("Add Material")')
  await page.selectOption('select[name="spool_id"]', { label: TEST_SPOOLS.spool2.name })
  await page.fill('input[name="weight_grams"]', TEST_SPOOLS.spool2.weight.toString())
  await page.click('button:has-text("Add to BOM")')

  // Wait for second material to be added
  await expect(page.locator(`text=${TEST_SPOOLS.spool2.name}`)).toBeVisible()

  return modelId
}

async function deleteTestModel(page: Page, modelId: string) {
  await page.goto(`/models/${modelId}`)
  await page.click('button:has-text("Delete")')
  await page.click('button:has-text("Confirm")')
  await page.waitForURL('/models')
}

test.describe('Production Run Auto-Population from Model BOM', () => {
  let modelId: string

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    await registerAndLogin(page)
  })

  test('should auto-populate materials from model BOM when creating production run', async ({ page }) => {
    // Step 1: Create a model with BOM materials
    modelId = await createTestModel(page)

    // Step 2: Navigate to production runs
    await page.goto('/production-runs')
    await page.waitForLoadState('networkidle')

    // Step 3: Click "New Production Run" button
    await page.click('button:has-text("New Production Run")')

    // Wait for wizard to load - Step 1 should be visible
    await expect(page.locator('text=Step 1 of 4: Basic Info')).toBeVisible()

    // Fill in basic info (Step 1)
    await page.fill('input[name="printer"]', 'Prusa i3 MK3S')
    await page.fill('input[name="estimated_print_time_hours"]', '2')

    // Navigate to Step 2 (Models)
    await page.click('button:has-text("Next")')
    await expect(page.locator('text=Step 2 of 4: Models')).toBeVisible()

    // Step 4: Select the model
    // Find the model selector (combobox/select)
    const modelSelect = page.locator('select[name="model_id"], [role="combobox"]').first()

    // If it's a custom combobox (Radix UI)
    if (await page.locator('[role="combobox"]').count() > 0) {
      await page.click('[role="combobox"]')
      await page.click(`text=${TEST_MODEL.sku}`)
    } else {
      // Standard select
      await modelSelect.selectOption({ label: TEST_MODEL.sku })
    }

    // Set quantity (default should be 1, but let's be explicit)
    await page.fill('input[name="quantity"]', '10')

    // Click "Add" button to add the model to the production run
    await page.click('button:has-text("Add")')

    // Verify model was added to the list
    await expect(page.locator(`text=${TEST_MODEL.name}`)).toBeVisible()

    // Step 5: Navigate to Step 3 (Materials)
    await page.click('button:has-text("Next")')
    await expect(page.locator('text=Step 3 of 4: Materials')).toBeVisible()

    // Step 6: Verify "Suggested Materials from Model BOM" card appears
    await expect(page.locator('text=Suggested Materials from Model BOM')).toBeVisible()

    // Step 7: Verify suggested materials show correct weights (scaled by quantity)
    // Expected weights: spool1 = 50.5g * 10 = 505g, spool2 = 30.0g * 10 = 300g

    // Verify Blue PLA suggestion
    const blueSuggestion = page.locator(`text=${TEST_SPOOLS.spool1.name}`).locator('..')
    await expect(blueSuggestion).toContainText('505.0g') // 50.5 * 10
    await expect(blueSuggestion).toContainText('Blue')

    // Verify Red PLA suggestion
    const redSuggestion = page.locator(`text=${TEST_SPOOLS.spool2.name}`).locator('..')
    await expect(redSuggestion).toContainText('300.0g') // 30.0 * 10
    await expect(redSuggestion).toContainText('Red')

    // Verify "Apply All Suggestions" button is present
    await expect(page.locator('button:has-text("Apply All Suggestions")')).toBeVisible()

    // Step 8: Click "Apply All Suggestions" button
    await page.click('button:has-text("Apply All Suggestions")')

    // Step 9: Verify materials are added to "Selected Materials" table
    // The materials should now appear in the main materials table
    const materialsTable = page.locator('table, [role="table"]')

    // Verify Blue PLA is in the table with correct weight
    await expect(materialsTable.locator(`text=${TEST_SPOOLS.spool1.name}`)).toBeVisible()
    await expect(materialsTable.locator('text=505')).toBeVisible() // Weight in grams

    // Verify Red PLA is in the table with correct weight
    await expect(materialsTable.locator(`text=${TEST_SPOOLS.spool2.name}`)).toBeVisible()
    await expect(materialsTable.locator('text=300')).toBeVisible() // Weight in grams

    // Step 10: Verify the suggestions are now marked as "Added"
    await expect(page.locator('text=Added').first()).toBeVisible()

    // Navigate to Step 4 (Review)
    await page.click('button:has-text("Next")')
    await expect(page.locator('text=Step 4 of 4: Review')).toBeVisible()

    // Verify the review summary shows correct information
    await expect(page.locator(`text=${TEST_MODEL.name}`)).toBeVisible()
    await expect(page.locator('text=Quantity: 10')).toBeVisible()
    await expect(page.locator(`text=${TEST_SPOOLS.spool1.name}`)).toBeVisible()
    await expect(page.locator(`text=${TEST_SPOOLS.spool2.name}`)).toBeVisible()

    // Step 11: Submit the production run
    await page.click('button:has-text("Create Production Run")')

    // Wait for redirect to production run detail page or list
    await page.waitForURL(/\/production-runs/, { timeout: 10000 })

    // Verify success message or production run appears in list
    await expect(
      page.locator('text=Production run created successfully, text=Production Run #')
    ).toBeVisible({ timeout: 10000 })
  })

  test('should handle low inventory warning when applying suggestions', async ({ page }) => {
    // This test verifies that when a spool has insufficient inventory,
    // a warning badge appears in the suggestions

    // Navigate to production runs
    await page.goto('/production-runs')
    await page.click('button:has-text("New Production Run")')

    // Navigate to Step 2 and add model
    await page.click('button:has-text("Next")')
    // Select model with quantity that exceeds available inventory
    // (This requires a model setup with known low inventory - may need test data setup)

    // Navigate to Step 3
    await page.click('button:has-text("Next")')

    // Verify "Low Inventory" badge appears for affected materials
    await expect(page.locator('text=Low Inventory')).toBeVisible()

    // Verify the warning styling (red background)
    const lowInventoryCard = page.locator('.bg-destructive\\/10').first()
    await expect(lowInventoryCard).toBeVisible()
  })

  test('should handle inactive spool warning when applying suggestions', async ({ page }) => {
    // This test verifies that when a spool is inactive (depleted/archived),
    // a warning badge appears in the suggestions

    // Navigate to production runs
    await page.goto('/production-runs')
    await page.click('button:has-text("New Production Run")')

    // Navigate to Step 2 and add model
    await page.click('button:has-text("Next")')
    // Select model that uses an inactive spool
    // (This requires a model setup with inactive spool - may need test data setup)

    // Navigate to Step 3
    await page.click('button:has-text("Next")')

    // Verify "Inactive" badge appears for affected materials
    await expect(page.locator('text=Inactive')).toBeVisible()

    // Verify the warning styling (red background)
    const inactiveCard = page.locator('.bg-destructive\\/10').first()
    await expect(inactiveCard).toBeVisible()
  })

  test('should show per-model breakdown when multiple models use same spool', async ({ page }) => {
    // This test verifies material grouping across multiple models

    // Create second model that also uses Blue PLA
    // (Requires additional test setup)

    await page.goto('/production-runs')
    await page.click('button:has-text("New Production Run")')

    // Add both models to production run
    await page.click('button:has-text("Next")')
    // Add model 1 and model 2 (both using Blue PLA)

    // Navigate to Step 3
    await page.click('button:has-text("Next")')

    // Verify Blue PLA shows combined weight
    await expect(page.locator('text=Total')).toBeVisible()

    // Expand the details to see per-model breakdown
    const detailsToggle = page.locator('details summary:has-text("Used in 2 models")')
    await detailsToggle.click()

    // Verify both models are listed with individual weights
    await expect(page.locator(`text=${TEST_MODEL.sku}`).first()).toBeVisible()
    // Should show individual model weights
  })

  test.afterEach(async ({ page }) => {
    // Cleanup: Delete the test model if it was created
    if (modelId) {
      await deleteTestModel(page, modelId)
    }
  })
})
