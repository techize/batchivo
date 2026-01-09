/**
 * E2E Tests: Shop Visibility & Featured Products
 *
 * Tests the shop display functionality for products:
 * - Toggle shop visibility on/off
 * - Set shop description
 * - Toggle featured status
 * - Set feature title and backstory
 */

import { test, expect, type Page } from '@playwright/test'
import { isBackendAvailable, registerAndLogin } from '../../helpers'

// Generate unique test data
const generateTestProduct = () => ({
  sku: `SHOP-TEST-${Date.now()}`,
  name: `Shop Visibility Test ${Date.now()}`,
  description: 'Product for shop visibility E2E testing',
  shopDescription: 'Beautiful handcrafted item perfect for collectors',
  featureTitle: 'Featured Dragon of the Month',
  backstory: 'This rare dragon was discovered in the mystical forests...',
})

// Helper: Create a test product and return its ID
async function createTestProduct(page: Page, product: ReturnType<typeof generateTestProduct>): Promise<string> {
  await page.goto('/products/new')
  await page.waitForLoadState('networkidle')

  // Fill basic fields
  await page.fill('input[name="sku"]', product.sku)
  await page.fill('input[name="name"]', product.name)
  await page.fill('textarea[name="description"]', product.description)

  // Submit
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

  // Extract product ID from URL
  const url = page.url()
  return url.split('/').pop()!
}

// Helper: Navigate to product edit page
async function navigateToProductEdit(page: Page, productId: string) {
  await page.goto(`/products/${productId}/edit`)
  await page.waitForLoadState('networkidle')
}

// Helper: Delete product
async function deleteProduct(page: Page, productId: string) {
  await page.goto(`/products/${productId}`)
  const deleteButton = page.locator('button:has-text("Delete")')
  if (await deleteButton.isVisible()) {
    await deleteButton.click()
    await page.click('button:has-text("Delete"):not(:has-text("Cancel"))')
    await page.waitForLoadState('networkidle')
  }
}

test.describe('Shop Visibility Toggle', () => {
  let testProduct: ReturnType<typeof generateTestProduct>
  let productId: string

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    testProduct = generateTestProduct()
    await registerAndLogin(page)
    productId = await createTestProduct(page, testProduct)
  })

  test.afterEach(async ({ page }) => {
    try {
      await deleteProduct(page, productId)
    } catch {
      // Ignore cleanup errors
    }
  })

  test('should toggle shop visibility ON', async ({ page }) => {
    await navigateToProductEdit(page, productId)

    // Find and toggle shop_visible switch
    const shopVisibleSwitch = page.locator('button[role="switch"][name="shop_visible"]')

    // Get initial state
    const initialState = await shopVisibleSwitch.getAttribute('data-state')

    // If not checked, click to enable
    if (initialState !== 'checked') {
      await shopVisibleSwitch.click()
    }

    // Save changes
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Go back to edit and verify
    await navigateToProductEdit(page, productId)
    const savedState = await shopVisibleSwitch.getAttribute('data-state')
    expect(savedState).toBe('checked')
  })

  test('should toggle shop visibility OFF', async ({ page }) => {
    // First enable shop visibility
    await navigateToProductEdit(page, productId)
    const shopVisibleSwitch = page.locator('button[role="switch"][name="shop_visible"]')

    // Enable if not already
    const initialState = await shopVisibleSwitch.getAttribute('data-state')
    if (initialState !== 'checked') {
      await shopVisibleSwitch.click()
    }
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Now disable it
    await navigateToProductEdit(page, productId)
    await shopVisibleSwitch.click() // Toggle off
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify it's off
    await navigateToProductEdit(page, productId)
    const savedState = await shopVisibleSwitch.getAttribute('data-state')
    expect(savedState).toBe('unchecked')
  })

  test('should set shop description when visible', async ({ page }) => {
    await navigateToProductEdit(page, productId)

    // Enable shop visibility
    const shopVisibleSwitch = page.locator('button[role="switch"][name="shop_visible"]')
    const initialState = await shopVisibleSwitch.getAttribute('data-state')
    if (initialState !== 'checked') {
      await shopVisibleSwitch.click()
    }

    // Fill shop description
    const shopDescriptionInput = page.locator('textarea[name="shop_description"]')
    await shopDescriptionInput.fill(testProduct.shopDescription)

    // Save
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify
    await navigateToProductEdit(page, productId)
    await expect(shopDescriptionInput).toHaveValue(testProduct.shopDescription)
  })
})

test.describe('Featured Product Toggle', () => {
  let testProduct: ReturnType<typeof generateTestProduct>
  let productId: string

  test.beforeEach(async ({ page }) => {
    test.skip(!(await isBackendAvailable()), 'Backend API not available')
    testProduct = generateTestProduct()
    await registerAndLogin(page)
    productId = await createTestProduct(page, testProduct)
  })

  test.afterEach(async ({ page }) => {
    try {
      await deleteProduct(page, productId)
    } catch {
      // Ignore cleanup errors
    }
  })

  test('should toggle featured status ON', async ({ page }) => {
    await navigateToProductEdit(page, productId)

    // Enable featured
    const featuredSwitch = page.locator('button[role="switch"][name="is_featured"]')
    const initialState = await featuredSwitch.getAttribute('data-state')

    if (initialState !== 'checked') {
      await featuredSwitch.click()
    }

    // Save
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify
    await navigateToProductEdit(page, productId)
    const savedState = await featuredSwitch.getAttribute('data-state')
    expect(savedState).toBe('checked')
  })

  test('should set feature title when featured', async ({ page }) => {
    await navigateToProductEdit(page, productId)

    // Enable featured
    const featuredSwitch = page.locator('button[role="switch"][name="is_featured"]')
    const initialState = await featuredSwitch.getAttribute('data-state')
    if (initialState !== 'checked') {
      await featuredSwitch.click()
    }

    // Fill feature title
    const featureTitleInput = page.locator('input[name="feature_title"]')
    await featureTitleInput.fill(testProduct.featureTitle)

    // Save
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify
    await navigateToProductEdit(page, productId)
    await expect(featureTitleInput).toHaveValue(testProduct.featureTitle)
  })

  test('should set backstory when featured', async ({ page }) => {
    await navigateToProductEdit(page, productId)

    // Enable featured
    const featuredSwitch = page.locator('button[role="switch"][name="is_featured"]')
    const initialState = await featuredSwitch.getAttribute('data-state')
    if (initialState !== 'checked') {
      await featuredSwitch.click()
    }

    // Fill backstory
    const backstoryInput = page.locator('textarea[name="backstory"]')
    await backstoryInput.fill(testProduct.backstory)

    // Save
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify
    await navigateToProductEdit(page, productId)
    await expect(backstoryInput).toHaveValue(testProduct.backstory)
  })

  test('should enable both shop visibility and featured status', async ({ page }) => {
    await navigateToProductEdit(page, productId)

    // Enable shop visibility
    const shopVisibleSwitch = page.locator('button[role="switch"][name="shop_visible"]')
    if ((await shopVisibleSwitch.getAttribute('data-state')) !== 'checked') {
      await shopVisibleSwitch.click()
    }

    // Enable featured
    const featuredSwitch = page.locator('button[role="switch"][name="is_featured"]')
    if ((await featuredSwitch.getAttribute('data-state')) !== 'checked') {
      await featuredSwitch.click()
    }

    // Fill all fields
    await page.locator('textarea[name="shop_description"]').fill(testProduct.shopDescription)
    await page.locator('input[name="feature_title"]').fill(testProduct.featureTitle)
    await page.locator('textarea[name="backstory"]').fill(testProduct.backstory)

    // Save
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/products\/[a-f0-9-]+$/, { timeout: 15000 })

    // Verify all fields saved
    await navigateToProductEdit(page, productId)

    expect(await shopVisibleSwitch.getAttribute('data-state')).toBe('checked')
    expect(await featuredSwitch.getAttribute('data-state')).toBe('checked')
    await expect(page.locator('textarea[name="shop_description"]')).toHaveValue(testProduct.shopDescription)
    await expect(page.locator('input[name="feature_title"]')).toHaveValue(testProduct.featureTitle)
    await expect(page.locator('textarea[name="backstory"]')).toHaveValue(testProduct.backstory)
  })
})
