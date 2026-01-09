/**
 * Patterns Library Page
 *
 * Displays knitting and crochet patterns.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, FileText, Upload } from 'lucide-react'

export function Patterns() {
  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Pattern Library</h1>
            <p className="text-muted-foreground mt-1">
              Store and organize your knitting and crochet patterns
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">
              <Upload className="w-4 h-4 mr-2" />
              Upload PDF
            </Button>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add Pattern
            </Button>
          </div>
        </div>

        {/* Placeholder Content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Patterns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="w-16 h-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No patterns yet</h3>
              <p className="text-muted-foreground mb-4 max-w-sm">
                Build your pattern library by adding patterns.
                Upload PDFs, link to online patterns, or enter details manually.
              </p>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Pattern
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
