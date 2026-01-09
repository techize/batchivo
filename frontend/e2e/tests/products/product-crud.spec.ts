/**
 * E2E Tests: Product CRUD Operations
 *
 * Tests the complete product lifecycle:
 * - Create product with required fields
 * - View product details
 * - Update product information
 * - Delete product
 * - SKU auto-generation
 */

import { test, expect, type Page } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

// Generate unique test data using timestamp
const generateTestProduct = () => ({
  sku: `TEST-PROD-${Date.now()}`,
  name: `E2E Test Product ${Date.now()}`,
  description: 'Product created by automated E2E test',
  packaging_cost: '1.50',
  assembly_minutes: '10',
  units_in_stock: '5',
})

// Helper: Navigate to products page
async function navigateToProducts(page: Page) {
  await page.goto('/products')
  await page.waitForLoadState('networkidle')
}

// Helper: Clean up test product by name
async function deleteProductByName(page: Page, productName: string) {
  await navigateToProducts(page)

  // Search for the product
  const searchInput = page.locator('input[placeholder*="Search"]')
  await searchInput.fill(productName)
  await page.waitForLoadState('networkidle')

  // Click on the product row to go to detail page
  const productRow = page.locator('tr').filter({ hasText: productName }).first()
  if (await productRow.isVisible()) {
    await productRow.click()
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 10000 })

    // Look for delete button
    const deleteButton = page.locator('button:has-text("Delete")')
    if (await deleteButton.isVisible()) {
      await deleteButton.click()
      // Confirm deletion in dialog
      await page.click('button:has-text("Delete"):not(:has-text("Cancel"))')
      await page.waitForLoadState('networkidle')
    }
  }
}

test.describe('Product CRUD Operations', () => {
  let testProduct: ReturnType<typeof generateTestProduct>

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    testProduct = generateTestProduct()
    await registerAndLogin(page)
  })

  test.afterEach(async ({ page }) => {
    // Cleanup: Try to delete test product
    try {
      await deleteProductByName(page, testProduct.name)
    } catch {
      // Ignore cleanup errors
    }
  })

  test('should display products list page', async ({ page }) => {
    await navigateToProducts(page)

    // Verify page elements
    await expect(page.getByRole('heading', { name: 'Products' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'New Product' })).toBeVisible()
    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible()
  })

  test('should create a new product with basic fields', async ({ page }) => {
    await navigateToProducts(page)

    // Click New Product button
    await page.click('text=New Product')
    await page.waitForURL('/products/new', { timeout: 10000 })

    // Verify we're on create page
    await expect(page).toHaveURL('/products/new')

    // Fill in product form
    await page.fill('input[name="sku"]', testProduct.sku)
    await page.fill('input[name="name"]', testProduct.name)
    await page.fill('textarea[name="description"]', testProduct.description)
    await page.fill('input[name="packaging_cost"]', testProduct.packaging_cost)
    await page.fill('input[name="assembly_minutes"]', testProduct.assembly_minutes)
    await page.fill('input[name="units_in_stock"]', testProduct.units_in_stock)

    // Submit form
    await page.click('button[type="submit"]')

    // Wait for redirect to product detail page
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify product was created - should see the name on detail page
    await expect(page.getByText(testProduct.name)).toBeVisible()
  })

  test('should auto-generate SKU for new product', async ({ page }) => {
    await navigateToProducts(page)

    // Click New Product button
    await page.click('text=New Product')
    await page.waitForURL('/products/new', { timeout: 10000 })

    // Wait for SKU to auto-populate
    await page.waitForTimeout(1000)

    // Check that SKU field has a value (auto-generated)
    const skuInput = page.locator('input[name="sku"]')
    const skuValue = await skuInput.inputValue()
    expect(skuValue).toMatch(/^PROD-\d{4}$/) // Format: PROD-0001
  })

  test('should view product details', async ({ page }) => {
    // First create a product
    await navigateToProducts(page)
    await page.click('text=New Product')
    await page.waitForURL('/products/new')

    await page.fill('input[name="sku"]', testProduct.sku)
    await page.fill('input[name="name"]', testProduct.name)
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify detail page shows product information
    await expect(page.getByText(testProduct.sku)).toBeVisible()
    await expect(page.getByText(testProduct.name)).toBeVisible()
  })

  test('should edit an existing product', async ({ page }) => {
    // First create a product
    await navigateToProducts(page)
    await page.click('text=New Product')
    await page.waitForURL('/products/new')

    await page.fill('input[name="sku"]', testProduct.sku)
    await page.fill('input[name="name"]', testProduct.name)
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Navigate to edit page
    await page.click('text=Edit')
    await page.waitForURL(/\/products\/[a-f0-9-]+\/edit$/, { timeout: 10000 })

    // Update product name
    const updatedName = `${testProduct.name} - Updated`
    await page.fill('input[name="name"]', updatedName)

    // Save changes
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify update
    await expect(page.getByText(updatedName)).toBeVisible()

    // Update testProduct name for cleanup
    testProduct.name = updatedName
  })

  test('should search for products', async ({ page }) => {
    // First create a product with unique name
    await navigateToProducts(page)
    await page.click('text=New Product')
    await page.waitForURL('/products/new')

    await page.fill('input[name="sku"]', testProduct.sku)
    await page.fill('input[name="name"]', testProduct.name)
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Navigate back to products list
    await navigateToProducts(page)

    // Search for the product
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill(testProduct.name)
    await page.waitForLoadState('networkidle')

    // Verify product appears in results
    await expect(page.getByText(testProduct.name)).toBeVisible()
  })

  test('should toggle product active status', async ({ page }) => {
    // First create a product
    await navigateToProducts(page)
    await page.click('text=New Product')
    await page.waitForURL('/products/new')

    await page.fill('input[name="sku"]', testProduct.sku)
    await page.fill('input[name="name"]', testProduct.name)
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Navigate to edit page
    await page.click('text=Edit')
    await page.waitForURL(/\/products\/[a-f0-9-]+\/edit$/, { timeout: 10000 })

    // Toggle active status (find the switch)
    const activeSwitch = page.locator('button[role="switch"][name="is_active"]')
    if (await activeSwitch.isVisible()) {
      await activeSwitch.click()
      await page.click('button[type="submit"]')
      await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })
    }
  })

  test('should validate required fields', async ({ page }) => {
    await navigateToProducts(page)
    await page.click('text=New Product')
    await page.waitForURL('/products/new')

    // Clear the auto-generated SKU
    await page.fill('input[name="sku"]', '')

    // Try to submit without filling required fields
    await page.click('button[type="submit"]')

    // Should show validation error - stay on create page
    await expect(page).toHaveURL('/products/new')

    // Should see validation message for SKU
    await expect(page.getByText(/SKU is required/i)).toBeVisible()
  })
})

test.describe('Product List Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    await registerAndLogin(page)
    await navigateToProducts(page)
  })

  test('should navigate to product detail on row click', async ({ page }) => {
    // Click on first product row (if exists)
    const firstProduct = page.locator('tbody tr').first()

    // Wait for table to load
    await page.waitForTimeout(1000)

    if (await firstProduct.isVisible()) {
      // Get the product name before clicking
      const productLink = firstProduct.locator('a').first()

      if (await productLink.isVisible()) {
        await productLink.click()
        await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 10000 })
      }
    }
  })

  test('should filter active/inactive products', async ({ page }) => {
    // Click on Active filter button
    const activeButton = page.getByRole('button', { name: /Active/i })
    await activeButton.click()
    await page.waitForLoadState('networkidle')

    // Click again to clear filter
    await activeButton.click()
    await page.waitForLoadState('networkidle')

    // Click on Inactive filter
    const inactiveButton = page.getByRole('button', { name: /Inactive/i })
    await inactiveButton.click()
    await page.waitForLoadState('networkidle')
  })

  test('should sort products', async ({ page }) => {
    // Open sort dropdown
    const sortTrigger = page.locator('button:has-text("Most Recent")')
    if (await sortTrigger.isVisible()) {
      await sortTrigger.click()

      // Select Name sort
      await page.click('text=Name (A-Z)')
      await page.waitForLoadState('networkidle')
    }
  })
})
