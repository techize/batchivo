/**
 * E2E Test: Production Run Edit Flow with Status-Based Restrictions
 *
 * This test verifies the complete user flow for editing production runs
 * with proper status-based restrictions.
 *
 * Flow:
 * 1. Create a production run (in_progress status)
 * 2. Edit the run - verify all fields are editable
 * 3. Save changes and verify they persisted
 * 4. Complete the production run
 * 5. Try to edit completed run - verify only notes field is editable
 * 6. Verify immutable status alert is shown
 * 7. Save notes-only change
 * 8. Verify other fields remain unchanged
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

// Test data
const TEST_RUN = {
  printer: 'Prusa i3 MK3S',
  estimatedTime: '2.5',
  bedTemp: '60',
  nozzleTemp: '210',
  notes: 'Initial test notes',
}

const EDIT_DATA = {
  printer: 'Prusa XL',
  estimatedTime: '3.0',
  bedTemp: '65',
  nozzleTemp: '215',
  notes: 'Updated notes after editing',
}

const COMPLETED_NOTES = 'Added notes after completion'

// Helper functions - registerAndLogin is defined above

async function createProductionRun(page: Page): Promise<string> {
  // Navigate to production runs
  await page.goto('/production-runs')
  await page.waitForLoadState('networkidle')

  // Click "New Production Run" button
  await page.click('button:has-text("New Production Run")')

  // Wait for wizard to load
  await expect(page.locator('text=Step 1 of 4: Basic Info')).toBeVisible()

  // Fill in basic info
  await page.fill('input[name="printer"]', TEST_RUN.printer)
  await page.fill('input[name="estimated_print_time_hours"]', TEST_RUN.estimatedTime)
  await page.fill('input[name="bed_temperature"]', TEST_RUN.bedTemp)
  await page.fill('input[name="nozzle_temperature"]', TEST_RUN.nozzleTemp)
  await page.fill('textarea[name="notes"]', TEST_RUN.notes)

  // Navigate through wizard (skip models and materials for simplicity)
  await page.click('button:has-text("Next")') // To Step 2 (Models)
  await page.click('button:has-text("Next")') // To Step 3 (Materials)
  await page.click('button:has-text("Next")') // To Step 4 (Review)

  // Submit the production run
  await page.click('button:has-text("Create Production Run")')

  // Wait for redirect to production run detail page
  await page.waitForURL(/\/production-runs\/[a-f0-9-]+$/, { timeout: 10000 })

  // Extract run ID from URL
  const url = page.url()
  const runId = url.split('/').pop()!

  return runId
}

async function deleteProductionRun(page: Page, runId: string) {
  await page.goto(`/production-runs/${runId}`)
  // Look for delete button (may require admin/specific permissions)
  const deleteButton = page.locator('button:has-text("Delete")')
  if (await deleteButton.isVisible()) {
    await deleteButton.click()
    await page.click('button:has-text("Confirm")')
    await page.waitForURL('/production-runs')
  }
}

test.describe('Production Run Edit Flow with Status-Based Restrictions', () => {
  let runId: string

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    await registerAndLogin(page)
  })

  test('should allow full editing of in_progress run and restrict editing after completion', async ({ page }) => {
    // ============================================
    // PART 1: Create in_progress production run
    // ============================================
    runId = await createProductionRun(page)

    // Verify we're on the detail page
    await expect(page.locator(`text=${TEST_RUN.printer}`)).toBeVisible()
    await expect(page.locator(`text=${TEST_RUN.notes}`)).toBeVisible()

    // Verify status badge shows "In Progress"
    await expect(page.locator('text=In Progress')).toBeVisible()

    // ============================================
    // PART 2: Edit in_progress run (full access)
    // ============================================

    // Click "Edit Run" button
    await page.click('button:has-text("Edit Run")')

    // Wait for Edit dialog to appear
    await expect(page.locator('text=Edit Production Run')).toBeVisible()

    // Verify NO lock alert (run is editable)
    await expect(page.locator('text=Only notes can be edited')).not.toBeVisible()

    // Verify all tabs are available
    await expect(page.locator('text=Basic Info')).toBeVisible()
    await expect(page.locator('button:has-text("Items")')).toBeVisible()
    await expect(page.locator('button:has-text("Materials")')).toBeVisible()

    // Edit basic info fields
    await page.fill('input[name="printer_name"], input[placeholder*="Prusa"]', EDIT_DATA.printer)
    await page.fill('input[name="estimated_print_time_hours"]', EDIT_DATA.estimatedTime)

    // Click on Basic Info tab to access temperature fields
    await page.click('button:has-text("Basic Info")')
    await page.fill('input[name="bed_temperature"]', EDIT_DATA.bedTemp)
    await page.fill('input[name="nozzle_temperature"]', EDIT_DATA.nozzleTemp)

    // Update notes
    const notesField = page.locator('textarea[name="notes"], label:has-text("Notes") + textarea')
    await notesField.fill(EDIT_DATA.notes)

    // Verify Save button is enabled (changes detected)
    const saveButton = page.locator('button:has-text("Save Changes")')
    await expect(saveButton).toBeEnabled()

    // Click Save
    await saveButton.click()

    // Wait for dialog to close
    await expect(page.locator('text=Edit Production Run')).not.toBeVisible({ timeout: 5000 })

    // ============================================
    // PART 3: Verify changes persisted
    // ============================================

    // Reload the page to ensure changes are saved
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Verify updated values are displayed
    await expect(page.locator(`text=${EDIT_DATA.printer}`)).toBeVisible()
    await expect(page.locator(`text=${EDIT_DATA.notes}`)).toBeVisible()

    // Verify temperature values (may be in a card or table)
    await expect(page.locator(`text=${EDIT_DATA.bedTemp}°C`)).toBeVisible()
    await expect(page.locator(`text=${EDIT_DATA.nozzleTemp}°C`)).toBeVisible()

    // ============================================
    // PART 4: Complete the production run
    // ============================================

    // Click "Complete Run" button
    await page.click('button:has-text("Complete Run")')

    // Wait for Complete dialog to appear
    await expect(page.locator('text=Complete Production Run')).toBeVisible()

    // Fill in completion details (minimal for test)
    // Assuming there's a simple completion form
    await page.click('button:has-text("Complete"), button:has-text("Mark as Complete")')

    // Wait for dialog to close and status to update
    await expect(page.locator('text=Complete Production Run')).not.toBeVisible({ timeout: 5000 })

    // Verify status changed to "Completed"
    await expect(page.locator('text=Completed')).toBeVisible({ timeout: 5000 })

    // ============================================
    // PART 5: Try to edit completed run (restricted)
    // ============================================

    // Click "Edit Run" button again
    await page.click('button:has-text("Edit Run")')

    // Wait for Edit dialog to appear
    await expect(page.locator('text=Edit Production Run')).toBeVisible()

    // Verify LOCK ALERT appears
    await expect(page.locator('text=This run is completed')).toBeVisible()
    await expect(page.locator('text=Only notes can be edited')).toBeVisible()

    // Verify tabs are NOT available (hidden for immutable runs)
    await expect(page.locator('button:has-text("Basic Info")')).not.toBeVisible()
    await expect(page.locator('button:has-text("Items")')).not.toBeVisible()
    await expect(page.locator('button:has-text("Materials")')).not.toBeVisible()

    // Verify only Notes field is editable
    const notesOnlyField = page.locator('textarea[name="notes"], label:has-text("Notes") + textarea')
    await expect(notesOnlyField).toBeVisible()
    await expect(notesOnlyField).toBeEditable()

    // Update notes (only field available)
    await notesOnlyField.fill(COMPLETED_NOTES)

    // Verify Save button is enabled (notes changed)
    const saveButtonRestricted = page.locator('button:has-text("Save Changes")')
    await expect(saveButtonRestricted).toBeEnabled()

    // Click Save
    await saveButtonRestricted.click()

    // Wait for dialog to close
    await expect(page.locator('text=Edit Production Run')).not.toBeVisible({ timeout: 5000 })

    // ============================================
    // PART 6: Verify only notes changed, other fields unchanged
    // ============================================

    // Reload to verify
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Verify notes updated
    await expect(page.locator(`text=${COMPLETED_NOTES}`)).toBeVisible()

    // Verify other fields remain unchanged from EDIT_DATA (not reverted)
    await expect(page.locator(`text=${EDIT_DATA.printer}`)).toBeVisible()
    await expect(page.locator(`text=${EDIT_DATA.bedTemp}°C`)).toBeVisible()
    await expect(page.locator(`text=${EDIT_DATA.nozzleTemp}°C`)).toBeVisible()

    // Verify status is still "Completed"
    await expect(page.locator('text=Completed')).toBeVisible()
  })

  test('should show immutable warning for failed runs', async ({ page }) => {
    // This test verifies that failed runs also have edit restrictions

    // Create a run (would need to fail it via Cancel/Fail dialog)
    runId = await createProductionRun(page)

    // Click "Cancel / Fail" button
    await page.click('button:has-text("Cancel / Fail")')

    // Wait for Cancel dialog
    await expect(page.locator('text=Cancel / Fail Production Run')).toBeVisible()

    // Select "Failed" as failure reason (assuming there's a radio/select)
    // This depends on actual UI implementation
    await page.click('button:has-text("Mark as Failed"), button:has-text("Fail Run")')

    // Wait for status to update
    await expect(page.locator('text=Failed')).toBeVisible({ timeout: 5000 })

    // Click "Edit Run" button
    await page.click('button:has-text("Edit Run")')

    // Wait for Edit dialog
    await expect(page.locator('text=Edit Production Run')).toBeVisible()

    // Verify lock alert for failed status
    await expect(page.locator('text=This run is failed')).toBeVisible()
    await expect(page.locator('text=Only notes can be edited')).toBeVisible()

    // Verify tabs hidden
    await expect(page.locator('button:has-text("Basic Info")')).not.toBeVisible()
  })

  test('should show immutable warning for cancelled runs', async ({ page }) => {
    // This test verifies that cancelled runs also have edit restrictions

    // Create a run
    runId = await createProductionRun(page)

    // Click "Cancel / Fail" button
    await page.click('button:has-text("Cancel / Fail")')

    // Wait for Cancel dialog
    await expect(page.locator('text=Cancel / Fail Production Run')).toBeVisible()

    // Select "Cancelled" option
    await page.click('button:has-text("Cancel Run"), button:has-text("Mark as Cancelled")')

    // Wait for status to update
    await expect(page.locator('text=Cancelled')).toBeVisible({ timeout: 5000 })

    // Click "Edit Run" button
    await page.click('button:has-text("Edit Run")')

    // Wait for Edit dialog
    await expect(page.locator('text=Edit Production Run')).toBeVisible()

    // Verify lock alert for cancelled status
    await expect(page.locator('text=This run is cancelled')).toBeVisible()
    await expect(page.locator('text=Only notes can be edited')).toBeVisible()
  })

  test.afterEach(async ({ page }) => {
    // Cleanup: Delete the test production run if it was created
    if (runId) {
      await deleteProductionRun(page, runId)
    }
  })
})
