/**
 * FilamentTypeFilterSheet — filter panel for the Filament Library page.
 * 5 filter dimensions: brand text, colour text, material type select,
 * needs labels toggle, no sample toggle.
 * Uses local draft state — changes only apply on "Apply filters" click.
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { materialTypesApi } from '@/lib/api/spools'
import type { FilamentTypeListParams } from '@/types/filament-type'

interface FilamentTypeFilterSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  params: FilamentTypeListParams
  onParamsChange: (params: FilamentTypeListParams) => void
}

export function FilamentTypeFilterSheet({
  open,
  onOpenChange,
  params,
  onParamsChange,
}: FilamentTypeFilterSheetProps) {
  const [draft, setDraft] = useState<FilamentTypeListParams>(params)

  // Reset draft to current params each time the sheet opens
  useEffect(() => {
    if (open) {
      setDraft(params)
    }
  }, [open, params])

  const { data: materialTypes } = useQuery({
    queryKey: ['material-types'],
    queryFn: () => materialTypesApi.list(),
  })

  const handleClearAll = () => {
    setDraft({})
    onParamsChange({})
  }

  const handleApply = () => {
    onParamsChange(draft)
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-[420px]">
        <SheetHeader>
          <SheetTitle>Filter Filaments</SheetTitle>
          <SheetDescription>
            Narrow the list by any combination of properties.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          {/* Brand filter */}
          <div className="space-y-2">
            <Label htmlFor="filter-brand">Brand</Label>
            <Input
              id="filter-brand"
              value={draft.brand ?? ''}
              onChange={(e) =>
                setDraft((prev) => ({
                  ...prev,
                  brand: e.target.value || undefined,
                }))
              }
              placeholder="e.g. JAYO"
            />
          </div>

          {/* Colour filter */}
          <div className="space-y-2">
            <Label htmlFor="filter-colour">Colour</Label>
            <Input
              id="filter-colour"
              value={draft.color ?? ''}
              onChange={(e) =>
                setDraft((prev) => ({
                  ...prev,
                  color: e.target.value || undefined,
                }))
              }
              placeholder="e.g. Black"
            />
          </div>

          {/* Material type filter */}
          <div className="space-y-2">
            <Label htmlFor="filter-material">Material type</Label>
            <Select
              value={draft.material_type_id ?? ''}
              onValueChange={(value) =>
                setDraft((prev) => ({
                  ...prev,
                  material_type_id: value || undefined,
                }))
              }
            >
              <SelectTrigger id="filter-material">
                <SelectValue placeholder="All materials" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All materials</SelectItem>
                {Array.isArray(materialTypes) &&
                  materialTypes.map((mat) => (
                    <SelectItem key={mat.id} value={mat.id}>
                      {mat.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>

          {/* Toggle filters */}
          <div className="space-y-2">
            <Label>Quick filters</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                variant={draft.needs_labels ? 'default' : 'outline'}
                aria-pressed={!!draft.needs_labels}
                onClick={() =>
                  setDraft((prev) => ({
                    ...prev,
                    needs_labels: prev.needs_labels ? undefined : true,
                  }))
                }
              >
                Needs labels
              </Button>
              <Button
                variant={draft.needs_sample ? 'default' : 'outline'}
                aria-pressed={!!draft.needs_sample}
                onClick={() =>
                  setDraft((prev) => ({
                    ...prev,
                    needs_sample: prev.needs_sample ? undefined : true,
                  }))
                }
              >
                No sample
              </Button>
            </div>
          </div>
        </div>

        <SheetFooter className="mt-8">
          <Button variant="outline" onClick={handleClearAll}>
            Clear all
          </Button>
          <Button variant="default" onClick={handleApply}>
            Apply filters
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
