/**
 * Sales Channel Create Page
 *
 * Page for creating a new sales channel.
 */

import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

import { AppLayout } from '@/components/layout/AppLayout'
import { SalesChannelForm } from '@/components/sales-channels/SalesChannelForm'
import { Button } from '@/components/ui/button'

export function SalesChannelCreatePage() {
  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Button variant="ghost" size="sm" asChild className="h-auto p-0 hover:bg-transparent">
              <Link to="/sales-channels">
                <ArrowLeft className="mr-1 h-4 w-4" />
                Sales Channels
              </Link>
            </Button>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">New Sales Channel</h1>
          <p className="text-muted-foreground">
            Add a new sales channel where you sell products
          </p>
        </div>

        {/* Form */}
        <SalesChannelForm mode="create" />
      </div>
    </AppLayout>
  )
}
