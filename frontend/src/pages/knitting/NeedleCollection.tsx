/**
 * Needle Collection Page
 *
 * Displays knitting needles and crochet hooks inventory.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Pen } from 'lucide-react'

export function NeedleCollection() {
  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Needles & Hooks</h1>
            <p className="text-muted-foreground mt-1">
              Track your knitting needles and crochet hooks
            </p>
          </div>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Add Needle/Hook
          </Button>
        </div>

        {/* Placeholder Content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Pen className="w-5 h-5" />
              Needle Collection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Pen className="w-16 h-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No needles yet</h3>
              <p className="text-muted-foreground mb-4 max-w-sm">
                Add your knitting needles and crochet hooks to track your collection.
                Record sizes, types, and materials.
              </p>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Needle
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
