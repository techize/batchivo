/**
 * ProductionRunList Component
 *
 * Displays a paginated, filterable list of production runs in a data table.
 * Styled to match the Filament Inventory page.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { X, RefreshCcw, Play, CheckCircle, XCircle, AlertTriangle, MoreHorizontal, Ban, Pencil } from 'lucide-react'

import { listProductionRuns, getProductionRun, formatStatus, formatDuration } from '@/lib/api/production-runs'
import type { ProductionRunStatus, ProductionRunDetail } from '@/types/production-run'
import { CancelRunDialog } from './CancelRunDialog'
import { CompleteRunDialog } from './CompleteRunDialog'
import { Button } from '@/components/ui/button'

import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCaption,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

type SortOption = 'newest' | 'oldest' | 'run_number'

export function ProductionRunList() {
  const [statusFilter, setStatusFilter] = useState<ProductionRunStatus | undefined>(undefined)
  const [page, setPage] = useState(0)
  const [limit] = useState(50)
  const [sortBy, setSortBy] = useState<SortOption>('newest')
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [selectedRunForCancel, setSelectedRunForCancel] = useState<ProductionRunDetail | null>(null)
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false)
  const [selectedRunForComplete, setSelectedRunForComplete] = useState<ProductionRunDetail | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['production-runs', { status_filter: statusFilter, skip: page * limit, limit }],
    queryFn: () =>
      listProductionRuns({
        status_filter: statusFilter,
        skip: page * limit,
        limit,
      }),
  })

  const handleStatusChange = (value: string) => {
    setStatusFilter(value === 'all' ? undefined : (value as ProductionRunStatus))
    setPage(0)
  }

  const clearFilters = () => {
    setStatusFilter(undefined)
    setSortBy('newest')
    setPage(0)
  }

  const hasActiveFilters = statusFilter || sortBy !== 'newest'

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  // Sort runs client-side
  const sortedRuns = data?.runs ? [...data.runs].sort((a, b) => {
    switch (sortBy) {
      case 'newest':
        return new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
      case 'oldest':
        return new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
      case 'run_number':
        return a.run_number.localeCompare(b.run_number, undefined, { numeric: true })
      default:
        return 0
    }
  }) : []

  // Get status badge variant
  const getStatusBadgeVariant = (status: ProductionRunStatus) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'in_progress':
        return 'default'
      case 'failed':
        return 'destructive'
      case 'cancelled':
        return 'secondary'
      default:
        return 'secondary'
    }
  }

  // Get status icon
  const getStatusIcon = (status: ProductionRunStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-3 w-3" />
      case 'in_progress':
        return <Play className="h-3 w-3" />
      case 'failed':
        return <XCircle className="h-3 w-3" />
      case 'cancelled':
        return <AlertTriangle className="h-3 w-3" />
      default:
        return null
    }
  }

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading production runs</p>
          <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Search and filter your production runs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Quick Filters */}
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()} className="flex-1 sm:flex-none">
              <RefreshCcw className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden xs:inline">Refresh</span>
            </Button>
            {hasActiveFilters && (
              <Button variant="outline" size="sm" onClick={clearFilters} className="flex-1 sm:flex-none">
                <X className="h-4 w-4 mr-1 sm:mr-2" />
                Clear Filters
              </Button>
            )}
          </div>

          {/* Status Filter and Sort */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="status-filter" className="text-sm">Status</Label>
              <Select
                value={statusFilter || 'all'}
                onValueChange={handleStatusChange}
              >
                <SelectTrigger id="status-filter">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="sort-by" className="text-sm">Sort By</Label>
              <Select
                value={sortBy}
                onValueChange={(value) => setSortBy(value as SortOption)}
              >
                <SelectTrigger id="sort-by">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">Newest First</SelectItem>
                  <SelectItem value="oldest">Oldest First</SelectItem>
                  <SelectItem value="run_number">Run Number</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              Runs
              {data && (
                <span className="ml-2 text-muted-foreground font-normal text-sm">
                  ({data.total} total)
                </span>
              )}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3 text-muted-foreground">Loading production runs...</span>
            </div>
          )}

          {data && sortedRuns.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-lg font-medium">No production runs found</p>
              <p className="text-sm mt-2">
                {statusFilter
                  ? 'Try adjusting your filters'
                  : 'Get started by creating your first production run'}
              </p>
            </div>
          )}

          {data && sortedRuns.length > 0 && (
            <>
              <div className="-mx-6 px-6">
                <Table>
                  <TableCaption>
                    Showing page {page + 1} of {totalPages || 1}
                  </TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[140px]">Run Number</TableHead>
                      <TableHead className="min-w-[150px]">Product/Model</TableHead>
                      <TableHead className="min-w-[100px]">Printer</TableHead>
                      <TableHead className="min-w-[120px]">Status</TableHead>
                      <TableHead className="min-w-[120px]">Started</TableHead>
                      <TableHead className="min-w-[100px]">Duration</TableHead>
                      <TableHead className="text-right min-w-[80px]">Variance</TableHead>
                      <TableHead className="text-right min-w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedRuns.map((run) => (
                      <TableRow
                        key={run.id}
                        className="cursor-pointer hover:bg-muted/50"
                      >
                        <TableCell className="font-mono font-medium">
                          <Link
                            to="/production-runs/$runId"
                            params={{ runId: run.id }}
                            className="hover:underline"
                          >
                            {run.run_number}
                          </Link>
                        </TableCell>
                        <TableCell>
                          {run.items_summary || <span className="text-muted-foreground">—</span>}
                        </TableCell>
                        <TableCell>
                          {run.printer_name || <span className="text-muted-foreground">—</span>}
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusBadgeVariant(run.status)} className="gap-1">
                            {getStatusIcon(run.status)}
                            {formatStatus(run.status)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col text-xs">
                            <span>{new Date(run.started_at).toLocaleDateString()}</span>
                            <span className="text-muted-foreground">
                              {new Date(run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          {run.duration_hours ? (
                            formatDuration(run.duration_hours)
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {run.variance_percentage !== null && run.variance_percentage !== undefined ? (
                            <span
                              className={
                                Math.abs(run.variance_percentage) > 10
                                  ? 'text-destructive font-medium'
                                  : Math.abs(run.variance_percentage) > 5
                                  ? 'text-amber-600 font-medium'
                                  : 'text-muted-foreground'
                              }
                            >
                              {run.variance_percentage > 0 ? '+' : ''}
                              {run.variance_percentage.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="outline" size="sm" asChild>
                              <Link to="/production-runs/$runId" params={{ runId: run.id }}>
                                View
                              </Link>
                            </Button>
                            {run.status === 'in_progress' && (
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    <MoreHorizontal className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem asChild>
                                    <Link to="/production-runs/$runId" params={{ runId: run.id }}>
                                      <Pencil className="h-4 w-4 mr-2" />
                                      Edit Run
                                    </Link>
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onSelect={async () => {
                                      // Fetch full run details for the dialog
                                      const fullRun = await getProductionRun(run.id)
                                      setSelectedRunForComplete(fullRun)
                                      setCompleteDialogOpen(true)
                                    }}
                                  >
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    Complete Run
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onSelect={async () => {
                                      // Fetch full run details for the dialog
                                      const fullRun = await getProductionRun(run.id)
                                      setSelectedRunForCancel(fullRun)
                                      setCancelDialogOpen(true)
                                    }}
                                  >
                                    <Ban className="h-4 w-4 mr-2" />
                                    Cancel / Fail Run
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-muted-foreground">
                    Page {page + 1} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0}
                    >
                      Previous
                    </Button>
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
            </>
          )}
        </CardContent>
      </Card>

      {/* Cancel/Fail Dialog */}
      {selectedRunForCancel && (
        <CancelRunDialog
          run={selectedRunForCancel}
          open={cancelDialogOpen}
          onOpenChange={(open) => {
            setCancelDialogOpen(open)
            if (!open) setSelectedRunForCancel(null)
          }}
          onSuccess={() => refetch()}
        />
      )}

      {/* Complete Run Dialog */}
      {selectedRunForComplete && (
        <CompleteRunDialog
          run={selectedRunForComplete}
          open={completeDialogOpen}
          onOpenChange={(open) => {
            setCompleteDialogOpen(open)
            if (!open) setSelectedRunForComplete(null)
          }}
          onSuccess={() => refetch()}
        />
      )}
    </div>
  )
}
