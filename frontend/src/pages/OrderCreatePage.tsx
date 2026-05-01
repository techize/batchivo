/**
 * Order Create Page
 *
 * Page for creating manual admin orders.
 */

import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { AppLayout } from '@/components/layout/AppLayout'
import { OrderCreateForm } from '@/components/orders/OrderCreateForm'
import { Button } from '@/components/ui/button'

export function OrderCreatePage() {
  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <div className="mb-2 flex items-center gap-2 text-muted-foreground">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/orders">
                <ArrowLeft className="mr-1 h-4 w-4" />
                Orders
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">New Order</h1>
          <p className="text-muted-foreground">
            Create a manual order and record its payment status
          </p>
        </div>

        <OrderCreateForm />
      </div>
    </AppLayout>
  )
}
