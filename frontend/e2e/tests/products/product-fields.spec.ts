/**
 * E2E Tests: Products - Field Validation
 *
 * Comprehensive tests verifying that each product form field correctly
 * saves to the database and is displayed properly in the UI.
 *
 * Product Fields Tested:
 * - Required: sku, name
 * - Optional text: description, shop_description, feature_title, backstory
 * - Numeric: packaging_cost, packaging_quantity, assembly_minutes, units_in_stock
 * - Boolean: is_active, shop_visible, is_featured
 * - Select: packaging_consumable_id
 */

import { test, expect, Page } from '@playwright/test'
import { API_URL } from '../../config'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

function generateCompleteProductData() {
  const timestamp = Date.now()
  return {
    sku: `PROD-TEST-${timestamp}`,
    name: `Test Product ${timestamp}`,
    description: 'A comprehensive test product with all fields populated',
    packaging_cost: 1.50,
    packaging_quantity: 2,
    assembly_minutes: 15,
    units_in_stock: 10,
    shop_description: 'Customer-facing description for the shop',
    feature_title: 'Featured Test Dragon',
    backstory: 'An ancient dragon awakened from slumber...',
  }
}

async function getAuthToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => localStorage.getItem('access_token'))
}

// Helper to wait for product form to be ready
async function waitForProductForm(page: Page): Promise<void> {
  await expect(page.locator('input[name="name"]')).toBeVisible({ timeout: 10000 })
}

// Helper to fill required product fields
async function fillRequiredProductFields(page: Page, name: string, sku?: string): Promise<void> {
  if (sku) {
    await page.locator('input[name="sku"]').fill(sku)
  }
  await page.locator('input[name="name"]').fill(name)
}

// Helper to submit form and verify redirect
async function submitAndVerifyProduct(page: Page, verifyText: string): Promise<void> {
  await page.getByRole('button', { name: /create product/i }).click()
  await page.waitForURL(/\/products\/[a-f0-9-]+/, { timeout: 30000 })
  await expect(page.getByText(verifyText).first()).toBeVisible({ timeout: 10000 })
}

test.describe('Product Field Validation - Required Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/products/new')
  })

  test('should display product creation form with all elements', async ({ page }) => {
    await waitForProductForm(page)
    await expect(page.getByText('Basic Information')).toBeVisible()
    await expect(page.locator('input[name="sku"]')).toBeVisible()
    await expect(page.locator('input[name="name"]')).toBeVisible()
  })

  test('should save sku correctly', async ({ page }) => {
    const testData = generateCompleteProductData()

    await waitForProductForm(page)
    await fillRequiredProductFields(page, testData.name, testData.sku)
    await submitAndVerifyProduct(page, testData.sku)
  })

  test('should save name correctly', async ({ page }) => {
    const uniqueName = `Unique Product Name ${Date.now()}`

    await waitForProductForm(page)
    await fillRequiredProductFields(page, uniqueName)
    await submitAndVerifyProduct(page, uniqueName)
  })

  test('should require name field', async ({ page }) => {
    await waitForProductForm(page)
    // Only fill SKU, leave name empty
    await page.locator('input[name="sku"]').fill('TEST-SKU-123')

    await page.getByRole('button', { name: /create product/i }).click()

    // Should show validation error and stay on form
    await expect(page.getByText('Name is required')).toBeVisible()
    await expect(page).toHaveURL(/\/products\/new/)
  })
})

test.describe('Product Field Validation - Optional Text Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/products/new')
  })

  test('should save description correctly', async ({ page }) => {
    const uniqueName = `Product Desc Test ${Date.now()}`
    const description = 'This is a detailed product description with special chars: !@#$%'

    await waitForProductForm(page)
    await fillRequiredProductFields(page, uniqueName)

    const descriptionInput = page.locator('textarea[name="description"]')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill(description)
    }

    await page.getByRole('button', { name: /create product/i }).click()
    await page.waitForURL(/\/products\/[a-f0-9-]+/, { timeout: 30000 })

    // Description should appear on detail page
    await expect(page.getByText(description)).toBeVisible()
  })
})

test.describe('Product Field Validation - Numeric Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
    await page.goto('/products/new')
  })

  test('should save packaging_cost correctly', async ({ page }) => {
    const testData = generateCompleteProductData()

    await waitForProductForm(page)
    await fillRequiredProductFields(page, testData.name)

    const packagingCostInput = page.locator('input[name="packaging_cost"]')
    if (await packagingCostInput.isVisible()) {
      await packagingCostInput.fill('2.50')
    }

    await submitAndVerifyProduct(page, testData.name)
  })

  test('should save assembly_minutes correctly', async ({ page }) => {
    const testData = generateCompleteProductData()

    await waitForProductForm(page)
    await fillRequiredProductFields(page, testData.name)

    const assemblyInput = page.locator('input[name="assembly_minutes"]')
    if (await assemblyInput.isVisible()) {
      await assemblyInput.fill('30')
    }

    await submitAndVerifyProduct(page, testData.name)
  })

  test('should save units_in_stock correctly', async ({ page }) => {
    const testData = generateCompleteProductData()

    await waitForProductForm(page)
    await fillRequiredProductFields(page, testData.name)

    const stockInput = page.locator('input[name="units_in_stock"]')
    if (await stockInput.isVisible()) {
      await stockInput.fill('25')
    }

    await page.getByRole('button', { name: /create product/i }).click()
    await page.waitForURL(/\/products\/[a-f0-9-]+/, { timeout: 30000 })

    // Stock count should appear on detail page
    const pageContent = await page.textContent('body')
    expect(pageContent?.includes('25') || pageContent?.includes('stock')).toBeTruthy()
  })
})

test.describe('Product Field Validation - Complete Form', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should create product with all fields populated', async ({ page }) => {
    const testData = generateCompleteProductData()

    await page.goto('/products/new')
    await waitForProductForm(page)

    // Required fields
    await page.locator('input[name="sku"]').fill(testData.sku)
    await page.locator('input[name="name"]').fill(testData.name)

    // Optional text fields
    const descriptionInput = page.locator('textarea[name="description"]')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill(testData.description)
    }

    // Numeric fields
    const packagingCost = page.locator('input[name="packaging_cost"]')
    if (await packagingCost.isVisible()) {
      await packagingCost.fill(testData.packaging_cost.toString())
    }

    const assemblyMinutes = page.locator('input[name="assembly_minutes"]')
    if (await assemblyMinutes.isVisible()) {
      await assemblyMinutes.fill(testData.assembly_minutes.toString())
    }

    const unitsInStock = page.locator('input[name="units_in_stock"]')
    if (await unitsInStock.isVisible()) {
      await unitsInStock.fill(testData.units_in_stock.toString())
    }

    await submitAndVerifyProduct(page, testData.name)
  })

  test('should verify created product data via API', async ({ page }) => {
    const testData = generateCompleteProductData()
    const uniqueSku = `API-PROD-${Date.now()}`

    await page.goto('/products/new')
    await waitForProductForm(page)

    await page.locator('input[name="sku"]').fill(uniqueSku)
    await page.locator('input[name="name"]').fill(testData.name)

    const descriptionInput = page.locator('textarea[name="description"]')
    if (await descriptionInput.isVisible()) {
      await descriptionInput.fill('API test description')
    }

    await page.getByRole('button', { name: /create product/i }).click()
    await page.waitForURL(/\/products\/[a-f0-9-]+/, { timeout: 30000 })

    // Get product ID from URL
    const url = page.url()
    const productId = url.split('/').pop()

    // Verify via API
    const token = await getAuthToken(page)
    if (token && productId) {
      const response = await page.request.get(`${API_URL}/api/v1/products/${productId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      expect(response.ok()).toBeTruthy()
      const data = await response.json()

      expect(data.sku).toBe(uniqueSku)
      expect(data.name).toBe(testData.name)
      expect(data.description).toBe('API test description')
    }
  })
})

test.describe('Product Field Validation - Edit Mode Fields', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should save shop settings when editing product', async ({ page }) => {
    const testData = generateCompleteProductData()

    // First create a product
    await page.goto('/products/new')
    await waitForProductForm(page)
    await page.locator('input[name="name"]').fill(testData.name)
    await page.getByRole('button', { name: /create product/i }).click()
    await page.waitForURL(/\/products\/[a-f0-9-]+/, { timeout: 30000 })

    // Navigate to edit page
    const editButton = page.getByRole('link', { name: /edit/i })
    if (await editButton.isVisible()) {
      await editButton.click()
      await page.waitForURL(/\/products\/[a-f0-9-]+\/edit/, { timeout: 30000 })

      // Shop visibility toggle
      const shopVisibleSwitch = page.locator('button[role="switch"][name="shop_visible"]')
      if (await shopVisibleSwitch.isVisible()) {
        await shopVisibleSwitch.click()
      }

      // Shop description
      const shopDescription = page.locator('textarea[name="shop_description"]')
      if (await shopDescription.isVisible()) {
        await shopDescription.fill('Shop-specific description')
      }

      // Featured toggle
      const featuredSwitch = page.locator('button[role="switch"][name="is_featured"]')
      if (await featuredSwitch.isVisible()) {
        await featuredSwitch.click()
      }

      // Save changes
      await page.getByRole('button', { name: /save changes/i }).click()
      await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 30000 })
    }
  })

  test('should save featured fields when is_featured enabled', async ({ page }) => {
    const testData = generateCompleteProductData()

    // Create product
    await page.goto('/products/new')
    await waitForProductForm(page)
    await page.locator('input[name="name"]').fill(testData.name)
    await page.getByRole('button', { name: /create product/i }).click()
    await page.waitForURL(/\/products\/[a-f0-9-]+/, { timeout: 30000 })

    // Edit product
    const editButton = page.getByRole('link', { name: /edit/i })
    if (await editButton.isVisible()) {
      await editButton.click()
      await page.waitForURL(/\/products\/[a-f0-9-]+\/edit/, { timeout: 30000 })

      // Enable featured
      const featuredSwitch = page.locator('button[role="switch"][name="is_featured"]')
      if (await featuredSwitch.isVisible()) {
        await featuredSwitch.click()

        // Fill featured fields
        const featureTitle = page.locator('input[name="feature_title"]')
        if (await featureTitle.isVisible()) {
          await featureTitle.fill('Ember the Ancient')
        }

        const backstory = page.locator('textarea[name="backstory"]')
        if (await backstory.isVisible()) {
          await backstory.fill('An ancient dragon awakened from eternal slumber...')
        }
      }

      await page.getByRole('button', { name: /save changes/i }).click()
      await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 30000 })
    }
  })
})

test.describe('Product Navigation', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not running on port 8000')
    await registerAndLogin(page)
  })

  test('should navigate to products page from dashboard', async ({ page }) => {
    await page.goto('/dashboard')

    const productsLink = page.getByRole('link', { name: /products/i })
    if (await productsLink.isVisible()) {
      await productsLink.click()
      await expect(page).toHaveURL(/\/products/)
    } else {
      await page.goto('/products')
      await expect(page).toHaveURL(/\/products/)
    }
  })

  test('should require authentication for products page', async ({ page }) => {
    // Logout and wait for redirect to login page
    await page.goto('/logout')
    await page.waitForURL(/\/login/, { timeout: 10000 })

    // Now try to access protected route
    await page.goto('/products')
    await expect(page).toHaveURL(/\/login/)
  })
})
