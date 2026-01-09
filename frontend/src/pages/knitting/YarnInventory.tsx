/**
 * Yarn Inventory Page
 *
 * Displays yarn inventory for knitting tenants.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Palette } from 'lucide-react'

export function YarnInventory() {
  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Yarn Inventory</h1>
            <p className="text-muted-foreground mt-1">
              Manage your yarn stash and track usage
            </p>
          </div>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Add Yarn
          </Button>
        </div>

        {/* Placeholder Content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="w-5 h-5" />
              Yarn Stash
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Palette className="w-16 h-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No yarn yet</h3>
              <p className="text-muted-foreground mb-4 max-w-sm">
                Start building your yarn inventory by adding your first skein.
                Track brands, colors, yardage, and more.
              </p>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Yarn
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
