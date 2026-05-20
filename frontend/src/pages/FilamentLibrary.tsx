/**
 * FilamentLibrary — consolidated filament type list page.
 * Shows all filament types aggregated by brand + colour + material with spool counts.
 * Replaces the stub component from Plan 01.
 */

import { useState } from 'react'
import { Search, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useFilamentTypes, useToggleHasSample } from '@/hooks/useFilamentTypes'
import type { FilamentTypeListParams } from '@/types/filament-type'
import { FilamentTypeCard } from '@/components/filaments/FilamentTypeCard'
import { FilamentTypeRow } from '@/components/filaments/FilamentTypeRow'

// TODO: replace with real components from Plan 06
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const FilamentTypeSpoolSheet = (_props: any) => null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const FilamentTypeFilterSheet = (_props: any) => null

export function FilamentLibrary() {
  const [spoolSheetFilamentTypeId, setSpoolSheetFilamentTypeId] = useState<string | null>(null)
  const [spoolSheetFilamentTypeName, setSpoolSheetFilamentTypeName] = useState<
    string | undefined
  >(undefined)
  const [filterSheetOpen, setFilterSheetOpen] = useState(false)
  const [params, setParams] = useState<FilamentTypeListParams>({ page: 1, page_size: 20 })

  const { data, isLoading, isError, error, refetch } = useFilamentTypes(params)
  const toggleSampleMutation = useToggleHasSample(params)

  const filamentTypes = data?.filament_types ?? []
  const hasActiveFilters = !!(
    params.brand ||
    params.color ||
    params.material_type_id ||
    params.needs_labels ||
    params.needs_sample
  )
  const activeFilterCount = [
    params.brand,
    params.color,
    params.material_type_id,
    params.needs_labels,
    params.needs_sample,
  ].filter(Boolean).length

  // Handlers
  const handleSearch = (value: string) => {
    setParams((prev) => ({ ...prev, brand: value || undefined, page: 1 }))
  }

  const handleRowClick = (id: string, name: string) => {
    setSpoolSheetFilamentTypeId(id)
    setSpoolSheetFilamentTypeName(name)
  }

  const handleToggleSample = (id: string, hasSample: boolean) => {
    toggleSampleMutation.mutate({ id, hasSample })
  }

  const handleClearFilters = () => {
    setParams({ page: 1, page_size: 20 })
  }

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Filament Library</h1>
        <p className="text-muted-foreground text-sm sm:text-base mt-1">
          Browse filament types and track spool inventory
        </p>
      </div>

      {/* Controls row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by brand, colour, or material..."
            className="pl-8"
            value={params.brand ?? ''}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
        <Button
          variant="outline"
          className="flex items-center gap-2"
          onClick={() => setFilterSheetOpen(true)}
        >
          <Filter className="h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="default" className="ml-1">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </div>

      {/* Quick filter toggles */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={params.needs_labels ? 'default' : 'outline'}
          size="sm"
          aria-pressed={!!params.needs_labels}
          onClick={() =>
            setParams((prev) => ({
              ...prev,
              needs_labels: prev.needs_labels ? undefined : true,
              page: 1,
            }))
          }
        >
          Needs labels
        </Button>
        <Button
          variant={params.needs_sample ? 'default' : 'outline'}
          size="sm"
          aria-pressed={!!params.needs_sample}
          onClick={() =>
            setParams((prev) => ({
              ...prev,
              needs_sample: prev.needs_sample ? undefined : true,
              page: 1,
            }))
          }
        >
          No sample
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <span className="ml-3 text-muted-foreground">Loading filaments...</span>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="bg-destructive/10 border border-destructive rounded-md p-4">
          <p className="text-destructive font-medium">Could not load filaments</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => refetch()}
          >
            Try again
          </Button>
        </div>
      )}

      {/* Empty states */}
      {!isLoading && !isError && data && filamentTypes.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          {hasActiveFilters ? (
            <>
              <p className="text-lg font-medium">No matching filament types</p>
              <p className="text-sm mt-2">Try adjusting your search or clearing filters.</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={handleClearFilters}
              >
                Clear filters
              </Button>
            </>
          ) : (
            <>
              <p className="text-lg font-medium">No filament types yet</p>
              <p className="text-sm mt-2">Add your first filament type to get started.</p>
            </>
          )}
        </div>
      )}

      {/* Mobile card list */}
      {!isLoading && !isError && filamentTypes.length > 0 && (
        <div className="lg:hidden space-y-4">
          {filamentTypes.map((ft) => (
            <FilamentTypeCard
              key={ft.id}
              filamentType={ft}
              onRowClick={(id) => handleRowClick(id, `${ft.brand} ${ft.color}`)}
              onToggleSample={handleToggleSample}
              isTogglingId={toggleSampleMutation.isPending ? toggleSampleMutation.variables?.id : null}
            />
          ))}
        </div>
      )}

      {/* Desktop table */}
      {!isLoading && !isError && filamentTypes.length > 0 && (
        <div className="hidden lg:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Brand</TableHead>
                <TableHead>Colour</TableHead>
                <TableHead>Material</TableHead>
                <TableHead>Spools</TableHead>
                <TableHead>Labels</TableHead>
                <TableHead>Sample</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filamentTypes.map((ft) => (
                <FilamentTypeRow
                  key={ft.id}
                  filamentType={ft}
                  onRowClick={(id) => handleRowClick(id, `${ft.brand} ${ft.color}`)}
                  onToggleSample={handleToggleSample}
                  isTogglingId={
                    toggleSampleMutation.isPending ? toggleSampleMutation.variables?.id : null
                  }
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Sheet siblings — rendered outside the list containers */}
      <FilamentTypeSpoolSheet
        filamentTypeId={spoolSheetFilamentTypeId}
        filamentTypeName={spoolSheetFilamentTypeName}
        onClose={() => {
          setSpoolSheetFilamentTypeId(null)
          setSpoolSheetFilamentTypeName(undefined)
        }}
      />
      <FilamentTypeFilterSheet
        open={filterSheetOpen}
        onOpenChange={setFilterSheetOpen}
        params={params}
        onParamsChange={(newParams: FilamentTypeListParams) => setParams(newParams)}
      />
    </div>
  )
}
