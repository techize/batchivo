/**
 * E2E Tests: Admin Order Creation
 *
 * Covers staff creating a manual admin order with a recorded payment result.
 */

import { test, expect, type Page, type Route } from '@playwright/test'

const productId = '33333333-3333-4333-8333-333333333333'
const channelId = '55555555-5555-4555-8555-555555555555'
const orderId = '11111111-1111-4111-8111-111111111111'

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function mockAuthenticatedCreateOrderApi(page: Page) {
  await page.route('**/api/v1/users/me', async (route) => {
    await json(route, {
      id: '44444444-4444-4444-8444-444444444444',
      email: 'staff@example.com',
      name: 'E2E Staff',
      tenant_id: '66666666-6666-4666-8666-666666666666',
      tenant_name: 'E2E Print Shop',
      currency_code: 'GBP',
      currency_symbol: '£',
      is_platform_admin: false,
    })
  })

  await page.route('**/api/v1/products**', async (route) => {
    await json(route, {
      products: [
        {
          id: productId,
          tenant_id: '66666666-6666-4666-8666-666666666666',
          sku: 'DRAGON-001',
          name: 'Articulated Dragon',
          description: null,
          packaging_cost: '0.00',
          packaging_quantity: 1,
          assembly_minutes: 0,
          units_in_stock: 10,
          is_active: true,
          created_at: '2026-05-01T10:00:00.000Z',
          updated_at: '2026-05-01T10:00:00.000Z',
          shop_visible: true,
          is_featured: false,
          is_dragon: true,
          print_to_order: false,
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
    })
  })

  await page.route('**/api/v1/sales-channels**', async (route) => {
    await json(route, {
      channels: [
        {
          id: channelId,
          tenant_id: '66666666-6666-4666-8666-666666666666',
          name: 'Craft Fair',
          platform_type: 'fair',
          fee_percentage: '0',
          fee_fixed: '0',
          monthly_cost: '0',
          is_active: true,
          created_at: '2026-05-01T10:00:00.000Z',
          updated_at: '2026-05-01T10:00:00.000Z',
        },
      ],
      total: 1,
    })
  })

  await page.route('**/api/v1/orders**', async (route) => {
    const url = new URL(route.request().url())

    if (route.request().method() === 'GET' && url.pathname === `/api/v1/orders/${orderId}`) {
      await json(route, {
        id: orderId,
        order_number: 'TEST-20260501-001',
        status: 'pending',
        customer_email: 'manual@example.com',
        customer_name: 'Manual Customer',
        customer_phone: null,
        shipping_address_line1: '10 Manual Lane',
        shipping_address_line2: null,
        shipping_city: 'Leeds',
        shipping_county: null,
        shipping_postcode: 'LS1 1AA',
        shipping_country: 'United Kingdom',
        shipping_method: 'Royal Mail Tracked 48',
        shipping_cost: 3.5,
        subtotal: 24.5,
        total: 28,
        currency: 'GBP',
        payment_provider: 'manual',
        payment_id: 'cash-123',
        payment_status: 'completed',
        tracking_number: null,
        tracking_url: null,
        shipped_at: null,
        delivered_at: null,
        fulfilled_at: null,
        customer_notes: null,
        internal_notes: 'Paid at craft fair',
        created_at: '2026-05-01T10:00:00.000Z',
        updated_at: '2026-05-01T10:00:00.000Z',
        items: [
          {
            id: '22222222-2222-4222-8222-222222222222',
            product_id: productId,
            product_sku: 'DRAGON-001',
            product_name: 'Articulated Dragon',
            quantity: 2,
            unit_price: 12.25,
            total_price: 24.5,
          },
        ],
      })
      return
    }

    if (route.request().method() === 'POST' && url.pathname === '/api/v1/orders') {
      const body = route.request().postDataJSON() as {
        customer_email: string
        sales_channel_id: string
        items: { product_id: string; quantity: number; unit_price: number }[]
      }

      expect(body.customer_email).toBe('manual@example.com')
      expect(body.sales_channel_id).toBe(channelId)
      expect(body.items).toEqual([
        {
          product_id: productId,
          quantity: 2,
          unit_price: 12.25,
        },
      ])

      await json(route, {
        id: orderId,
        order_number: 'TEST-20260501-001',
        status: 'pending',
        customer_email: 'manual@example.com',
        customer_name: 'Manual Customer',
        customer_phone: null,
        shipping_address_line1: '10 Manual Lane',
        shipping_address_line2: null,
        shipping_city: 'Leeds',
        shipping_county: null,
        shipping_postcode: 'LS1 1AA',
        shipping_country: 'United Kingdom',
        shipping_method: 'Royal Mail Tracked 48',
        shipping_cost: 3.5,
        subtotal: 24.5,
        total: 28,
        currency: 'GBP',
        payment_provider: 'manual',
        payment_id: 'cash-123',
        payment_status: 'completed',
        tracking_number: null,
        tracking_url: null,
        shipped_at: null,
        delivered_at: null,
        fulfilled_at: null,
        customer_notes: null,
        internal_notes: 'Paid at craft fair',
        created_at: '2026-05-01T10:00:00.000Z',
        updated_at: '2026-05-01T10:00:00.000Z',
        items: [
          {
            id: '22222222-2222-4222-8222-222222222222',
            product_id: productId,
            product_sku: 'DRAGON-001',
            product_name: 'Articulated Dragon',
            quantity: 2,
            unit_price: 12.25,
            total_price: 24.5,
          },
        ],
      })
      return
    }

    await route.fallback()
  })
}

test.describe('Admin Order Creation', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem(
        'batchivo_auth_tokens',
        JSON.stringify({
          accessToken: 'e2e-access-token',
          refreshToken: 'e2e-refresh-token',
          tokenType: 'bearer',
          expiresAt: Date.now() + 60 * 60 * 1000,
        }),
      )
      window.localStorage.setItem('batchivo_remember_me', '1')
    })

    await mockAuthenticatedCreateOrderApi(page)
  })

  test('lets staff create a manual order and lands on the order detail page', async ({ page }) => {
    await page.goto('/orders/new')

    await expect(page.getByRole('heading', { name: 'New Order' })).toBeVisible()

    await page.getByLabel('Customer email').fill('manual@example.com')
    await page.getByLabel('Customer name').fill('Manual Customer')
    await page.getByLabel('Address line 1').fill('10 Manual Lane')
    await page.getByLabel('City').fill('Leeds')
    await page.getByLabel('Postcode').fill('LS1 1AA')
    await page.getByLabel('Shipping method').fill('Royal Mail Tracked 48')
    await page.getByLabel('Shipping cost').fill('3.50')
    await page.getByLabel('Payment reference').fill('cash-123')
    await page.getByLabel('Internal notes').fill('Paid at craft fair')

    await page.getByLabel('Sales channel').click()
    await page.getByRole('option', { name: 'Craft Fair' }).click()

    await page.getByLabel('Product').click()
    await page.getByRole('option', { name: /Articulated Dragon/ }).click()
    await page.getByLabel('Quantity').fill('2')
    await page.getByLabel('Unit price').fill('12.25')

    await expect(page.getByText('£28.00')).toBeVisible()

    await page.getByRole('button', { name: /create order/i }).click()

    await expect(page).toHaveURL(`/orders/${orderId}`)
    await expect(page.getByText('TEST-20260501-001')).toBeVisible()
  })
})
