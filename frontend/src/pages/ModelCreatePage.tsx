/**
 * Model Create Page
 *
 * Page for creating new models (printed items with BOM).
 */

import { ModelForm } from '@/components/models/ModelForm'
import { AppLayout } from '@/components/layout/AppLayout'

export function ModelCreatePage() {
  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Create Model</h1>
          <p className="text-muted-foreground">Add a new printed item to your catalog</p>
        </div>
        <ModelForm mode="create" />
      </div>
    </AppLayout>
  )
}
