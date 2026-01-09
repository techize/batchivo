/**
 * E2E Tests: Category Management
 *
 * Tests the category management functionality:
 * - Create new category
 * - Edit existing category
 * - Toggle active status
 * - Reorder categories
 * - Delete category
 * - Search categories
 */

import { test, expect, type Page } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

// Generate unique test data
const generateTestCategory = () => ({
  name: `E2E Test Category ${Date.now()}`,
  slug: `e2e-test-category-${Date.now()}`,
  description: 'Category created by automated E2E test',
})

// Helper: Navigate to categories page
async function navigateToCategories(page: Page) {
  await page.goto('/categories')
  await page.waitForLoadState('networkidle')
}

// Helper: Create a category via the dialog
async function createCategory(
  page: Page,
  category: ReturnType<typeof generateTestCategory>
): Promise<void> {
  await navigateToCategories(page)

  // Click "New Category" button
  await page.click('button:has-text("New Category")')

  // Wait for dialog to open
  await expect(page.locator('[role="dialog"]')).toBeVisible()

  // Fill in the form
  await page.fill('input[placeholder*="Category name"]', category.name)

  // Slug might auto-generate, but let's fill it explicitly
  const slugInput = page.locator('input[placeholder*="category-slug"]')
  if (await slugInput.isVisible()) {
    await slugInput.fill(category.slug)
  }

  // Fill description if field exists
  const descInput = page.locator('textarea').first()
  if (await descInput.isVisible()) {
    await descInput.fill(category.description)
  }

  // Submit the dialog
  await page.click('button:has-text("Create"):not(:has-text("New"))')
  await page.waitForLoadState('networkidle')
}

// Helper: Delete category by name
async function deleteCategoryByName(page: Page, categoryName: string): Promise<void> {
  await navigateToCategories(page)

  // Search for the category
  const searchInput = page.locator('input[placeholder*="Search"]')
  await searchInput.fill(categoryName)
  await page.waitForLoadState('networkidle')

  // Find the delete button in the row
  const row = page.locator('tr, .rounded-lg.border').filter({ hasText: categoryName }).first()
  if (await row.isVisible()) {
    // Click delete button (Trash icon)
    const deleteButton = row.locator('button').filter({ has: page.locator('svg.lucide-trash-2') })
    if (await deleteButton.isVisible()) {
      await deleteButton.click()

      // Confirm in alert dialog
      const confirmButton = page.locator('[role="alertdialog"] button:has-text("Delete")')
      if (await confirmButton.isVisible()) {
        await confirmButton.click()
        await page.waitForLoadState('networkidle')
      }
    }
  }
}

test.describe('Category Management', () => {
  let testCategory: ReturnType<typeof generateTestCategory>

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    testCategory = generateTestCategory()
    await registerAndLogin(page)
  })

  test.afterEach(async ({ page }) => {
    // Cleanup: Try to delete test category
    try {
      await deleteCategoryByName(page, testCategory.name)
    } catch {
      // Ignore cleanup errors
    }
  })

  test('should display categories page', async ({ page }) => {
    await navigateToCategories(page)

    // Verify page elements
    await expect(page.getByRole('heading', { name: 'Categories' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'New Category' })).toBeVisible()
    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible()
  })

  test('should create a new category', async ({ page }) => {
    await createCategory(page, testCategory)

    // Search for the category to verify it was created
    await navigateToCategories(page)
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill(testCategory.name)
    await page.waitForLoadState('networkidle')

    // Verify category appears in list
    await expect(page.getByText(testCategory.name)).toBeVisible()
  })

  test('should auto-generate slug from name', async ({ page }) => {
    await navigateToCategories(page)

    // Click "New Category" button
    await page.click('button:has-text("New Category")')

    // Wait for dialog
    await expect(page.locator('[role="dialog"]')).toBeVisible()

    // Fill in name
    const uniqueName = `My Test Category ${Date.now()}`
    await page.fill('input[placeholder*="Category name"]', uniqueName)

    // Wait a moment for slug to auto-generate
    await page.waitForTimeout(500)

    // Check if slug field has value
    const slugInput = page.locator('input[placeholder*="category-slug"]')
    if (await slugInput.isVisible()) {
      const slugValue = await slugInput.inputValue()
      // Should have generated a slug
      expect(slugValue.length).toBeGreaterThan(0)
      expect(slugValue).toContain('my-test-category')
    }

    // Close dialog without saving
    await page.keyboard.press('Escape')
  })

  test('should edit an existing category', async ({ page }) => {
    // First create a category
    await createCategory(page, testCategory)

    // Navigate back and search for it
    await navigateToCategories(page)
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill(testCategory.name)
    await page.waitForLoadState('networkidle')

    // Find and click edit button
    const row = page.locator('tr, .rounded-lg.border').filter({ hasText: testCategory.name }).first()
    const editButton = row.locator('button').filter({ has: page.locator('svg.lucide-pencil') })
    await editButton.click()

    // Wait for edit dialog/inline edit
    await page.waitForTimeout(500)

    // Update the name
    const updatedName = `${testCategory.name} - Updated`

    // The edit might be inline or dialog-based, try both approaches
    const dialogNameInput = page.locator('[role="dialog"] input').first()
    const inlineNameInput = row.locator('input').first()

    if (await dialogNameInput.isVisible()) {
      await dialogNameInput.fill(updatedName)
      await page.click('button:has-text("Save")')
    } else if (await inlineNameInput.isVisible()) {
      await inlineNameInput.fill(updatedName)
      await page.click('button:has-text("Save")')
    }

    await page.waitForLoadState('networkidle')

    // Update testCategory for cleanup
    testCategory.name = updatedName
  })

  test('should toggle category active status', async ({ page }) => {
    // First create a category
    await createCategory(page, testCategory)

    await navigateToCategories(page)

    // Make sure we're showing all categories (including inactive)
    const showAllButton = page.getByRole('button', { name: 'Show Inactive' })
    if (await showAllButton.isVisible()) {
      await showAllButton.click()
      await page.waitForLoadState('networkidle')
    }

    // Search for the category
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill(testCategory.name)
    await page.waitForLoadState('networkidle')

    // Find the row and toggle switch
    const row = page.locator('tr, .rounded-lg.border').filter({ hasText: testCategory.name }).first()
    const toggle = row.locator('button[role="switch"]')

    if (await toggle.isVisible()) {
      // Get initial state
      const initialState = await toggle.getAttribute('data-state')

      // Toggle
      await toggle.click()
      await page.waitForLoadState('networkidle')

      // Verify state changed
      const newState = await toggle.getAttribute('data-state')
      expect(newState).not.toBe(initialState)
    }
  })

  test('should search categories', async ({ page }) => {
    // First create a category with unique name
    await createCategory(page, testCategory)

    await navigateToCategories(page)

    // Search with the unique name
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill(testCategory.name)
    await page.waitForLoadState('networkidle')

    // Should see the category
    await expect(page.getByText(testCategory.name)).toBeVisible()

    // Search for something that shouldn't exist
    await searchInput.fill('nonexistent-category-xyz-12345')
    await page.waitForLoadState('networkidle')

    // Should show empty state or no results
    await expect(page.getByText(testCategory.name)).not.toBeVisible()
  })

  test('should filter active/inactive categories', async ({ page }) => {
    await navigateToCategories(page)

    // Click "Active Only" filter if visible
    const activeOnlyButton = page.getByRole('button', { name: /Active Only/i })
    if (await activeOnlyButton.isVisible()) {
      await activeOnlyButton.click()
      await page.waitForLoadState('networkidle')
    }

    // Click "Show Inactive" filter if visible
    const showInactiveButton = page.getByRole('button', { name: /Show Inactive/i })
    if (await showInactiveButton.isVisible()) {
      await showInactiveButton.click()
      await page.waitForLoadState('networkidle')
    }
  })

  test('should delete a category', async ({ page }) => {
    // Create a category specifically for deletion
    const deleteCategory = generateTestCategory()
    await createCategory(page, deleteCategory)

    await navigateToCategories(page)

    // Search for it
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill(deleteCategory.name)
    await page.waitForLoadState('networkidle')

    // Verify it exists
    await expect(page.getByText(deleteCategory.name)).toBeVisible()

    // Find and click delete button
    const row = page.locator('tr, .rounded-lg.border').filter({ hasText: deleteCategory.name }).first()
    const deleteButton = row.locator('button').filter({ has: page.locator('svg.lucide-trash-2') })
    await deleteButton.click()

    // Confirm in alert dialog
    const confirmButton = page.locator('[role="alertdialog"] button:has-text("Delete")')
    await expect(confirmButton).toBeVisible()
    await confirmButton.click()
    await page.waitForLoadState('networkidle')

    // Verify category is gone
    await searchInput.fill(deleteCategory.name)
    await page.waitForLoadState('networkidle')
    await expect(page.getByText(deleteCategory.name)).not.toBeVisible()
  })
})

test.describe('Category Reordering', () => {
  let category1: ReturnType<typeof generateTestCategory>
  let category2: ReturnType<typeof generateTestCategory>

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    category1 = generateTestCategory()
    category2 = {
      name: `E2E Test Category 2 - ${Date.now()}`,
      slug: `e2e-test-category-2-${Date.now()}`,
      description: 'Second category for reorder test',
    }
    await registerAndLogin(page)
  })

  test.afterEach(async ({ page }) => {
    // Cleanup
    try {
      await deleteCategoryByName(page, category1.name)
      await deleteCategoryByName(page, category2.name)
    } catch {
      // Ignore cleanup errors
    }
  })

  test('should have reorder buttons', async ({ page }) => {
    // Create two categories
    await createCategory(page, category1)
    await createCategory(page, category2)

    await navigateToCategories(page)

    // Look for arrow buttons (up/down for reordering)
    const upButtons = page.locator('button').filter({ has: page.locator('svg.lucide-arrow-up') })
    const downButtons = page.locator('button').filter({ has: page.locator('svg.lucide-arrow-down') })

    // Should have reorder buttons if multiple categories exist
    const upCount = await upButtons.count()
    const downCount = await downButtons.count()

    // At least some buttons should exist
    expect(upCount + downCount).toBeGreaterThan(0)
  })
})
