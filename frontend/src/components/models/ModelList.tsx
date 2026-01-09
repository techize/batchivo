/**
 * ModelList Component
 *
 * Displays a paginated, searchable, filterable list of models in a data table.
 * Models are printed items with BOM (Bill of Materials).
 */

import { useState, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Loader2, Plus, Search, X, Upload, Download, Boxes, Filter, ArrowUpDown, Printer, PoundSterling } from 'lucide-react'

import { listModels, importModels, exportModels } from '@/lib/api/models'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

type SortOption = 'name' | 'sku' | 'category' | 'recent'

export function ModelList() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string | undefined>(undefined)
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)
  const [sortBy, setSortBy] = useState<SortOption>('recent')
  const [page, setPage] = useState(0)
  const [limit] = useState(50)
  const [isImporting, setIsImporting] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['models', { search, category, isActive, skip: page * limit, limit }],
    queryFn: () =>
      listModels({
        search: search || undefined,
        category,
        is_active: isActive,
        skip: page * limit,
        limit,
      }),
  })

  const handleSearchChange = (value: string) => {
    setSearch(value)
    setPage(0) // Reset to first page on search
  }

  const handleCategoryChange = (value: string) => {
    setCategory(value === 'all' ? undefined : value)
    setPage(0)
  }

  const handleStatusChange = (value: string) => {
    setIsActive(value === 'all' ? undefined : value === 'active')
    setPage(0)
  }

  const clearFilters = () => {
    setSearch('')
    setCategory(undefined)
    setIsActive(undefined)
    setSortBy('recent')
    setPage(0)
  }

  const hasActiveFilters = search || category || isActive !== undefined || sortBy !== 'recent'

  // Sort models client-side (backend returns by recent first)
  const sortedModels = data?.models ? [...data.models].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name)
      case 'sku':
        return a.sku.localeCompare(b.sku)
      case 'category':
        return (a.category || '').localeCompare(b.category || '')
      case 'recent':
      default:
        return 0 // Keep original order (most recent)
    }
  }) : []

  // Get category color for visual consistency
  const getCategoryColor = (cat: string | null) => {
    switch (cat?.toLowerCase()) {
      case 'figurines':
        return 'bg-purple-500/10 text-purple-600 border-purple-200'
      case 'functional':
        return 'bg-blue-500/10 text-blue-600 border-blue-200'
      case 'toys':
        return 'bg-orange-500/10 text-orange-600 border-orange-200'
      case 'art':
        return 'bg-pink-500/10 text-pink-600 border-pink-200'
      case 'parts':
        return 'bg-green-500/10 text-green-600 border-green-200'
      default:
        return 'bg-gray-500/10 text-gray-600 border-gray-200'
    }
  }

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const blob = await exportModels()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `models_export_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      console.log('Export successful: Models have been exported to CSV')
    } catch (error) {
      console.error('Export failed:', error)
      alert(`Export failed: ${(error as Error).message}`)
    } finally {
      setIsExporting(false)
    }
  }

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsImporting(true)
    try {
      const result = await importModels(file)

      console.log('Import successful:', result)
      alert(`Import successful!\nCreated: ${result.created}\nUpdated: ${result.updated}\nSkipped: ${result.skipped}`)

      // Refresh model list
      queryClient.invalidateQueries({ queryKey: ['models'] })

      // Show errors if any
      if (result.errors && result.errors.length > 0) {
        console.error('Import errors:', result.errors)
        alert(`Import completed with ${result.errors.length} errors. Check console for details.`)
      }
    } catch (error) {
      console.error('Import failed:', error)
      alert(`Import failed: ${(error as Error).message}`)
    } finally {
      setIsImporting(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const totalPages = data ? Math.ceil(data.total / limit) : 0
  const activeCount = data?.models.filter(m => m.is_active).length || 0
  const inactiveCount = data?.models.filter(m => !m.is_active).length || 0
  const totalStock = data?.models.reduce((sum, m) => sum + (m.units_in_stock || 0), 0) || 0

  // Format print time from minutes
  const formatPrintTime = (minutes: number | undefined) => {
    if (!minutes) return '—'
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (hours === 0) return `${mins}m`
    return `${hours}h${mins > 0 ? ` ${mins}m` : ''}`
  }

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading models</p>
          <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Model Catalog</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} models | {totalStock} units in stock | {activeCount} active
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Hidden file input for import */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleImport}
            style={{ display: 'none' }}
          />

          {/* Import button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isImporting}
          >
            {isImporting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Upload className="mr-2 h-4 w-4" />
            )}
            <span className="hidden sm:inline">Import</span>
          </Button>

          {/* Export button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={isExporting}
          >
            {isExporting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            <span className="hidden sm:inline">Export</span>
          </Button>

          {/* New Model button */}
          <Button asChild>
            <Link to="/models/new">
              <Plus className="mr-2 h-4 w-4" />
              New Model
            </Link>
          </Button>
        </div>
      </div>

      {/* Filters Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by SKU or name..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Quick Filters */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={isActive === true ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setIsActive(isActive === true ? undefined : true)
                setPage(0)
              }}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-green-500" />
              Active ({activeCount})
            </Button>
            <Button
              variant={isActive === false ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setIsActive(isActive === false ? undefined : false)
                setPage(0)
              }}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-gray-400" />
              Inactive ({inactiveCount})
            </Button>
          </div>

          {/* Dropdowns Row */}
          <div className="flex flex-wrap gap-3">
            <Select value={category || 'all'} onValueChange={handleCategoryChange}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="figurines">Figurines</SelectItem>
                <SelectItem value="functional">Functional</SelectItem>
                <SelectItem value="toys">Toys</SelectItem>
                <SelectItem value="art">Art</SelectItem>
                <SelectItem value="parts">Parts</SelectItem>
              </SelectContent>
            </Select>

            <Select value={isActive === undefined ? 'all' : isActive ? 'active' : 'inactive'} onValueChange={handleStatusChange}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
              <SelectTrigger className="w-[140px]">
                <ArrowUpDown className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">Most Recent</SelectItem>
                <SelectItem value="name">Name (A-Z)</SelectItem>
                <SelectItem value="sku">SKU (A-Z)</SelectItem>
                <SelectItem value="category">Category</SelectItem>
              </SelectContent>
            </Select>

            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="h-10">
                <X className="mr-2 h-4 w-4" />
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Boxes className="h-4 w-4" />
            Models
            {data && (
              <Badge variant="secondary" className="ml-2">
                {data.total}
              </Badge>
            )}
          </CardTitle>
          {hasActiveFilters && (
            <CardDescription>
              Showing filtered results
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {/* Loading State */}
          {isLoading && (
            <div className="flex h-[200px] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-3">Loading models...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && sortedModels.length === 0 && (
            <div className="flex h-[200px] items-center justify-center">
              <div className="text-center">
                <Boxes className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">
                  {hasActiveFilters
                    ? 'No models match your filters'
                    : 'No models yet. Create your first model to get started.'}
                </p>
                {!hasActiveFilters && (
                  <Button asChild className="mt-4">
                    <Link to="/models/new">
                      <Plus className="mr-2 h-4 w-4" />
                      Create Model
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Card View - Mobile/Tablet */}
          {!isLoading && sortedModels.length > 0 && (
            <div className="lg:hidden space-y-3">
              {sortedModels.map((model) => (
                <Link
                  key={model.id}
                  to="/models/$modelId"
                  params={{ modelId: model.id }}
                  className="block rounded-lg border p-4 space-y-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-medium">{model.name}</div>
                      <div className="text-sm font-mono text-muted-foreground">
                        {model.sku}
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={model.is_active ? 'bg-green-500/10 text-green-600 border-green-200' : 'bg-gray-500/10 text-gray-500 border-gray-200'}
                    >
                      {model.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {model.category && (
                      <Badge variant="outline" className={getCategoryColor(model.category)}>
                        {model.category}
                      </Badge>
                    )}
                    {model.designer && (
                      <span className="text-sm text-muted-foreground">
                        by {model.designer}
                      </span>
                    )}
                    {model.total_cost && (
                      <span className="text-sm font-medium text-green-600">
                        £{parseFloat(model.total_cost).toFixed(3)}
                      </span>
                    )}
                    <span className="text-sm text-muted-foreground">
                      Stock: {model.units_in_stock || 0}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* Table View - Desktop */}
          {!isLoading && sortedModels.length > 0 && (
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[120px]">SKU</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-[120px]">Category</TableHead>
                    <TableHead className="w-[120px]">Designer</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[100px] text-right">
                      <PoundSterling className="inline h-4 w-4 mr-1" />
                      Cost
                    </TableHead>
                    <TableHead className="w-[100px] text-right">
                      <Printer className="inline h-4 w-4 mr-1" />
                      Time
                    </TableHead>
                    <TableHead className="w-[80px] text-right">Stock</TableHead>
                    <TableHead className="w-[80px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedModels.map((model) => (
                    <TableRow key={model.id} className="group">
                      <TableCell className="font-mono text-sm">{model.sku}</TableCell>
                      <TableCell>
                        <Link
                          to="/models/$modelId"
                          params={{ modelId: model.id }}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {model.name}
                        </Link>
                        {model.description && (
                          <p className="text-xs text-muted-foreground truncate max-w-[300px]">
                            {model.description}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        {model.category ? (
                          <Badge variant="outline" className={getCategoryColor(model.category)}>
                            {model.category}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {model.designer || <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={model.is_active ? 'bg-green-500/10 text-green-600 border-green-200' : 'bg-gray-500/10 text-gray-500 border-gray-200'}
                        >
                          {model.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {model.total_cost ? `£${parseFloat(model.total_cost).toFixed(3)}` : '—'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPrintTime(model.print_time_minutes)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {model.units_in_stock || 0}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Link to="/models/$modelId" params={{ modelId: model.id }}>
                            View
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {data && data.total > limit && (
            <div className="flex items-center justify-between pt-4 border-t mt-4">
              <div className="text-sm text-muted-foreground">
                Showing {page * limit + 1} to {Math.min((page + 1) * limit, data.total)} of {data.total}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  Previous
                </Button>
                <div className="text-sm tabular-nums">
                  {page + 1} / {totalPages}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= totalPages - 1}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
