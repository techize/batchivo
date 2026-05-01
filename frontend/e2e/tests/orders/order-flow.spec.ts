/**
 * E2E Tests: Order Processing Workflow
 *
 * Covers the admin-visible order lifecycle after a successful checkout/payment:
 * - paid order appears in the orders list
 * - admin can mark the order shipped with tracking details
 * - admin can mark the shipped order delivered
 */

import { test, expect, type Page, type Route } from '@playwright/test'

type E2EOrder = {
  id: string
  order_number: string
  status: 'pending' | 'shipped' | 'delivered'
  customer_email: string
  customer_name: string
  customer_phone: string | null
  shipping_address_line1: string
  shipping_address_line2: string | null
  shipping_city: string
  shipping_county: string | null
  shipping_postcode: string
  shipping_country: string
  shipping_method: string
  shipping_cost: number
  subtotal: number
  total: number
  currency: string
  payment_provider: string
  payment_id: string
  payment_status: string
  tracking_number: string | null
  tracking_url: string | null
  shipped_at: string | null
  delivered_at: string | null
  fulfilled_at: string | null
  customer_notes: string | null
  internal_notes: string | null
  created_at: string
  updated_at: string
  items: {
    id: string
    product_id: string
    product_sku: string
    product_name: string
    quantity: number
    unit_price: number
    total_price: number
  }[]
}

const orderId = '11111111-1111-4111-8111-111111111111'

function createPaidOrder(): E2EOrder {
  const now = new Date('2026-05-01T10:00:00.000Z').toISOString()

  return {
    id: orderId,
    order_number: 'ORD-E2E-001',
    status: 'pending',
    customer_email: 'customer@example.com',
    customer_name: 'E2E Customer',
    customer_phone: null,
    shipping_address_line1: '1 Test Street',
    shipping_address_line2: null,
    shipping_city: 'London',
    shipping_county: null,
    shipping_postcode: 'E1 1AA',
    shipping_country: 'GB',
    shipping_method: 'standard',
    shipping_cost: 4.99,
    subtotal: 25,
    total: 29.99,
    currency: 'GBP',
    payment_provider: 'square',
    payment_id: 'sq_e2e_payment',
    payment_status: 'COMPLETED',
    tracking_number: null,
    tracking_url: null,
    shipped_at: null,
    delivered_at: null,
    fulfilled_at: null,
    customer_notes: null,
    internal_notes: null,
    created_at: now,
    updated_at: now,
    items: [
      {
        id: '22222222-2222-4222-8222-222222222222',
        product_id: '33333333-3333-4333-8333-333333333333',
        product_sku: 'DRAGON-001',
        product_name: 'Articulated Dragon',
        quantity: 1,
        unit_price: 25,
        total_price: 25,
      },
    ],
  }
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function mockAuthenticatedOrderApi(page: Page, order: E2EOrder) {
  await page.route('**/api/v1/users/me', async (route) => {
    await json(route, {
      id: '44444444-4444-4444-8444-444444444444',
      email: 'staff@example.com',
      name: 'E2E Staff',
      tenant_id: '55555555-5555-4555-8555-555555555555',
      tenant_name: 'E2E Print Shop',
      currency_code: 'GBP',
      currency_symbol: '£',
      is_platform_admin: false,
    })
  })

  await page.route('**/api/v1/orders**', async (route) => {
    const url = new URL(route.request().url())

    if (url.pathname === '/api/v1/orders/counts') {
      await json(route, {
        pending: order.status === 'pending' ? 1 : 0,
        processing: 0,
        shipped: order.status === 'shipped' ? 1 : 0,
        delivered: order.status === 'delivered' ? 1 : 0,
        cancelled: 0,
        refunded: 0,
        total: 1,
      })
      return
    }

    if (url.pathname === '/api/v1/orders') {
      await json(route, {
        data: [order],
        total: 1,
        page: 1,
        limit: 20,
        has_more: false,
      })
      return
    }

    if (url.pathname === `/api/v1/orders/${orderId}/ship`) {
      const body = route.request().postDataJSON() as {
        tracking_number?: string
        tracking_url?: string
      }
      order.status = 'shipped'
      order.tracking_number = body.tracking_number ?? null
      order.tracking_url = body.tracking_url ?? null
      order.shipped_at = new Date('2026-05-01T11:00:00.000Z').toISOString()
      order.updated_at = order.shipped_at

      await json(route, { message: 'Order marked as shipped' })
      return
    }

    if (url.pathname === `/api/v1/orders/${orderId}/deliver`) {
      order.status = 'delivered'
      order.delivered_at = new Date('2026-05-01T12:00:00.000Z').toISOString()
      order.updated_at = order.delivered_at

      await json(route, { message: 'Order marked as delivered' })
      return
    }

    await route.fallback()
  })
}

test.describe('Order Processing Workflow', () => {
  test.beforeEach(async ({ page }) => {
    const order = createPaidOrder()

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

    await mockAuthenticatedOrderApi(page, order)
  })

  test('shows a paid order and lets staff ship then deliver it', async ({ page }) => {
    await page.goto('/orders')

    await expect(page.getByRole('heading', { name: 'Orders' })).toBeVisible()
    const orderRow = page.locator('tbody tr').filter({ hasText: 'ORD-E2E-001' })
    await expect(orderRow).toBeVisible()

    await orderRow.getByRole('button', { name: /ship/i }).click()
    await page.getByLabel(/tracking number/i).fill('RM123456789GB')
    await page.getByRole('button', { name: /mark as shipped/i }).click()

    await expect(page.getByRole('dialog')).toBeHidden()
    await expect(orderRow.getByText('shipped', { exact: true })).toBeVisible()

    await orderRow.getByRole('button', { name: /delivered/i }).click()

    await expect(orderRow.getByText('delivered', { exact: true })).toBeVisible()
  })
})
