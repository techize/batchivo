/**
 * Model Edit Page
 *
 * Page for editing existing models (printed items with BOM).
 */

import { useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { Loader2 } from 'lucide-react'

import { getModel } from '@/lib/api/models'
import { ModelForm } from '@/components/models/ModelForm'
import { BOMEditor } from '@/components/models/BOMEditor'
import { ComponentsEditor } from '@/components/models/ComponentsEditor'
import { ModelFilesEditor } from '@/components/models/ModelFilesEditor'
import { Separator } from '@/components/ui/separator'
import { AppLayout } from '@/components/layout/AppLayout'

export function ModelEditPage() {
  const { modelId } = useParams({ from: '/models/$modelId/edit' })

  const { data: model, isLoading, error } = useQuery({
    queryKey: ['model', modelId],
    queryFn: () => getModel(modelId),
  })

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      </AppLayout>
    )
  }

  if (error || !model) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-[400px]">
          <div className="text-center">
            <p className="text-lg font-semibold text-destructive">Error loading model</p>
            <p className="text-sm text-muted-foreground">{error ? (error as Error).message : 'Model not found'}</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Edit Model</h1>
          <p className="text-muted-foreground">Update model information, BOM (materials), and components</p>
        </div>

        {/* Model Information Form */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Model Information</h2>
          <ModelForm mode="edit" model={model} />
        </div>

        <Separator />

        {/* Bill of Materials Editor */}
        <BOMEditor modelId={modelId} materials={model.materials} />

        <Separator />

        {/* 3D Model Files */}
        <ModelFilesEditor modelId={modelId} />

        <Separator />

        {/* Components Editor */}
        <ComponentsEditor modelId={modelId} components={model.components} />
      </div>
    </AppLayout>
  )
}
