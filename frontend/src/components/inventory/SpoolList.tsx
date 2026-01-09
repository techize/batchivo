import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { spoolsApi, materialTypesApi } from '@/lib/api/spools'
import type { SpoolListParams, SpoolResponse } from '@/types/spool'
import styles from './SpoolList.module.css'
import {
  isIndexedDBAvailable,
  saveSpools,
  getSpools,
  getSyncQueueCount,
} from '@/lib/db/indexeddb'
import { OfflineBanner } from '@/components/ui/offline-indicator'
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Search, Plus, RefreshCcw, Trash2, X, Copy, QrCode, ScanLine } from 'lucide-react'
import { AddSpoolDialog } from './AddSpoolDialog'
import { EditSpoolDialog } from './EditSpoolDialog'
import { UpdateWeightDialog } from './UpdateWeightDialog'
import { DeleteSpoolDialog } from './DeleteSpoolDialog'
import { ViewSpoolDialog } from './ViewSpoolDialog'
import { SpoolCard } from './SpoolCard'

type SortOption = 'spool_id' | 'material' | 'brand' | 'color' | 'remaining' | 'weight'

export function SpoolList() {
  const queryClient = useQueryClient()
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingSpoolId, setEditingSpoolId] = useState<string | null>(null)
  const [updateWeightDialogOpen, setUpdateWeightDialogOpen] = useState(false)
  const [updatingWeightSpoolId, setUpdatingWeightSpoolId] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingSpoolId, setDeletingSpoolId] = useState<string | null>(null)
  const [duplicatingSpoolId, setDuplicatingSpoolId] = useState<string | null>(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [viewingSpoolId, setViewingSpoolId] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<SortOption>('spool_id')
  const [params, setParams] = useState<SpoolListParams>({
    page: 1,
    page_size: 20,
    search: '',
    low_stock_only: false,
  })

  // Offline support state
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  )
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [pendingSyncCount, setPendingSyncCount] = useState(0)
  const [isSyncing, setIsSyncing] = useState(false)

  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Update pending sync count
  useEffect(() => {
    const updatePendingCount = async () => {
      if (isIndexedDBAvailable()) {
        const count = await getSyncQueueCount()
        setPendingSyncCount(count)
      }
    }

    updatePendingCount()
    const interval = setInterval(updatePendingCount, 5000)
    return () => clearInterval(interval)
  }, [])

  // Fetch spools with react-query and offline fallback
  const {
    data: spoolData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['spools', params],
    queryFn: async () => {
      // Try network first if online
      if (isOnline) {
        try {
          const response = await spoolsApi.list(params)
          // Cache the results to IndexedDB for offline access
          if (isIndexedDBAvailable()) {
            await saveSpools(response.spools)
          }
          return response
        } catch (err) {
          console.warn('Failed to fetch from network, trying cache:', err)
        }
      }

      // Fall back to IndexedDB cache
      if (isIndexedDBAvailable()) {
        const cachedSpools = await getSpools({
          isActive: params.is_active,
          materialTypeId: params.material_type_id,
          search: params.search,
        })

        // Apply low stock filter if needed
        const filteredSpools = params.low_stock_only
          ? cachedSpools.filter((s) => s.remaining_percentage < 20)
          : cachedSpools

        return {
          spools: filteredSpools as SpoolResponse[],
          total: filteredSpools.length,
          page: params.page || 1,
          page_size: params.page_size || 20,
        }
      }

      throw new Error('No network connection and no cached data available')
    },
  })

  // Handle manual sync
  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await refetch()
      const count = await getSyncQueueCount()
      setPendingSyncCount(count)
    } finally {
      setIsSyncing(false)
    }
  }

  // Fetch material types for filtering
  const { data: materialTypes } = useQuery({
    queryKey: ['material-types'],
    queryFn: () => materialTypesApi.list(),
  })

  // Duplicate mutation
  const duplicateMutation = useMutation({
    mutationFn: (id: string) => spoolsApi.duplicate(id),
    onSuccess: (newSpool) => {
      // Invalidate the spools list to refresh
      queryClient.invalidateQueries({ queryKey: ['spools'] })
      // Open edit dialog with the new spool
      setEditingSpoolId(newSpool.id)
      setEditDialogOpen(true)
      setDuplicatingSpoolId(null)
    },
    onError: (error) => {
      console.error('Failed to duplicate spool:', error)
      setDuplicatingSpoolId(null)
    },
  })

  // Handle duplicate
  const handleDuplicate = (id: string) => {
    setDuplicatingSpoolId(id)
    duplicateMutation.mutate(id)
  }

  // Natural sort for spool IDs (FIL-001 before FIL-009 before FIL-010)
  const naturalSort = (a: string, b: string) => {
    return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
  }

  // Client-side sorting (since backend doesn't support it yet)
  const sortedSpools = React.useMemo(() => {
    if (!spoolData?.spools || !Array.isArray(spoolData.spools)) {
      return []
    }

    return [...spoolData.spools].sort((a, b) => {
      switch (sortBy) {
        case 'spool_id':
          return naturalSort(a.spool_id, b.spool_id)
        case 'material':
          return a.material_type_code.localeCompare(b.material_type_code)
        case 'brand':
          return a.brand.localeCompare(b.brand)
        case 'color':
          return a.color.localeCompare(b.color)
        case 'remaining':
          return b.remaining_percentage - a.remaining_percentage  // Descending
        case 'weight':
          return b.current_weight - a.current_weight  // Descending
        default:
          return 0
      }
    })
  }, [spoolData?.spools, sortBy])

  // Handlers
  const handleSearch = (value: string) => {
    setParams((prev) => ({ ...prev, search: value, page: 1 }))
  }

  const handlePageChange = (newPage: number) => {
    setParams((prev) => ({ ...prev, page: newPage }))
  }

  const toggleLowStock = () => {
    setParams((prev) => ({ ...prev, low_stock_only: !prev.low_stock_only, page: 1 }))
  }

  const handleMaterialFilter = (materialId: string) => {
    setParams((prev) => ({ ...prev, material_type_id: materialId || undefined, page: 1 }))
  }

  const clearFilters = () => {
    setParams({
      page: 1,
      page_size: 20,
      search: '',
      low_stock_only: false,
    })
    setSortBy('spool_id')
  }

  // Calculate total pages
  const totalPages = spoolData ? Math.ceil(spoolData.total / params.page_size!) : 0


  return (
    <div className="space-y-4">
      {/* Offline Banner */}
      <OfflineBanner onSync={handleSync} isSyncing={isSyncing} />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Filament Inventory</h1>
          <p className="text-muted-foreground text-sm sm:text-base">
            Manage your 3D printing filament spools
          </p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button variant="outline" asChild className="flex-1 sm:flex-none">
            <Link to="/filaments/scan">
              <ScanLine className="h-4 w-4 mr-2" />
              Scan QR
            </Link>
          </Button>
          <Button onClick={() => setAddDialogOpen(true)} className="flex-1 sm:flex-none">
            <Plus className="h-4 w-4 mr-2" />
            Add Spool
          </Button>
        </div>
      </div>

      {/* Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Search and filter your filament inventory</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search Row */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by spool ID, brand, or colour..."
              className="pl-8"
              value={params.search}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>

          {/* Quick Filters - wrap on mobile */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={params.low_stock_only ? 'default' : 'outline'}
              onClick={toggleLowStock}
              size="sm"
              className="flex-1 sm:flex-none"
            >
              Low Stock Only
            </Button>
            <Button variant="outline" size="sm" onClick={() => refetch()} className="flex-1 sm:flex-none">
              <RefreshCcw className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden xs:inline">Refresh</span>
            </Button>
            {(params.search || params.material_type_id || params.low_stock_only || sortBy !== 'spool_id') && (
              <Button variant="outline" size="sm" onClick={clearFilters} className="flex-1 sm:flex-none">
                <X className="h-4 w-4 mr-1 sm:mr-2" />
                Clear
              </Button>
            )}
          </div>

          {/* Material Filter and Sort - stack on mobile */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="material-filter" className="text-sm">Material Type</Label>
              <Select
                value={params.material_type_id || 'all'}
                onValueChange={handleMaterialFilter}
              >
                <SelectTrigger id="material-filter">
                  <SelectValue placeholder="All materials" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Materials</SelectItem>
                  {Array.isArray(materialTypes) && materialTypes.map((mat) => (
                    <SelectItem key={mat.id} value={mat.id}>
                      {mat.name}
                    </SelectItem>
                  ))}
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
                  <SelectItem value="spool_id">Spool ID</SelectItem>
                  <SelectItem value="material">Material</SelectItem>
                  <SelectItem value="brand">Brand</SelectItem>
                  <SelectItem value="color">Colour</SelectItem>
                  <SelectItem value="remaining">Remaining %</SelectItem>
                  <SelectItem value="weight">Current Weight</SelectItem>
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
              Spools
              {spoolData && (
                <span className="ml-2 text-muted-foreground font-normal text-sm">
                  ({spoolData.total} total)
                </span>
              )}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3 text-muted-foreground">Loading spools...</span>
            </div>
          )}

          {isError && (
            <div className="bg-destructive/10 border border-destructive rounded-md p-4">
              <p className="text-destructive font-medium">❌ Error loading spools</p>
              <p className="text-sm text-muted-foreground mt-2">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          )}

          {spoolData && sortedSpools.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-lg font-medium">No spools found</p>
              <p className="text-sm mt-2">
                {params.search || params.material_type_id || params.low_stock_only
                  ? 'Try adjusting your filters'
                  : 'Get started by adding your first spool'}
              </p>
            </div>
          )}

          {spoolData && Array.isArray(sortedSpools) && sortedSpools.length > 0 && (
            <>
              {/* Mobile/Tablet Card View - show on screens < lg (1024px) */}
              <div className="lg:hidden space-y-4">
                {sortedSpools.map((spool) => (
                  <SpoolCard
                    key={spool.id}
                    spool={spool}
                    onUpdateWeight={(id) => {
                      setUpdatingWeightSpoolId(id)
                      setUpdateWeightDialogOpen(true)
                    }}
                    onEdit={(id) => {
                      setEditingSpoolId(id)
                      setEditDialogOpen(true)
                    }}
                    onDelete={(id) => {
                      setDeletingSpoolId(id)
                      setDeleteDialogOpen(true)
                    }}
                    onDuplicate={handleDuplicate}
                    onView={(id) => {
                      setViewingSpoolId(id)
                      setViewDialogOpen(true)
                    }}
                    isDuplicating={duplicatingSpoolId === spool.id}
                  />
                ))}
              </div>

              {/* Desktop Table View - only show on screens >= lg (1024px) */}
              <div className={`hidden lg:block ${styles.scrollContainer} -mx-6 px-6`}>
                <div className={styles.tableWrapper}>
                <Table>
                  <TableCaption>
                    Showing page {params.page} of {totalPages}
                  </TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[100px]">Spool ID</TableHead>
                      <TableHead className="min-w-[80px]">Material</TableHead>
                      <TableHead className="min-w-[120px]">Brand</TableHead>
                      <TableHead className="min-w-[120px]">Colour</TableHead>
                      <TableHead className="min-w-[130px]">Weight</TableHead>
                      <TableHead className="min-w-[140px]">Remaining</TableHead>
                      <TableHead className="min-w-[120px]">Status</TableHead>
                      <TableHead className="text-right min-w-[280px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                  {sortedSpools.map((spool) => (
                    <TableRow
                      key={spool.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => {
                        setViewingSpoolId(spool.id)
                        setViewDialogOpen(true)
                      }}
                    >
                      <TableCell className="font-medium font-mono">
                        {spool.spool_id}
                      </TableCell>
                      <TableCell>
                        <span className="font-medium">{spool.material_type_name}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {spool.brand}
                          {spool.spools_remaining > 1 && (
                            <Badge variant="secondary" className="text-xs">
                              ×{spool.spools_remaining}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {spool.color}
                          {spool.finish && (
                            <span className="text-xs text-muted-foreground">
                              ({spool.finish})
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {(() => {
                          // Calculate total weight across all spools in this batch
                          // current_weight is for the active spool, remaining spools are full
                          const unusedSpools = Math.max(0, spool.spools_remaining - 1)
                          const totalCurrent = spool.current_weight + (unusedSpools * spool.initial_weight)
                          const totalInitial = spool.spools_remaining * spool.initial_weight

                          return (
                            <div className="flex flex-col text-xs">
                              {spool.spools_remaining > 1 ? (
                                <>
                                  <span className="font-medium">{totalCurrent.toFixed(0)}g</span>
                                  <span className="text-muted-foreground">
                                    / {totalInitial.toFixed(0)}g
                                  </span>
                                  <span className="text-muted-foreground text-[10px]">
                                    ({spool.spools_remaining} spools)
                                  </span>
                                </>
                              ) : (
                                <>
                                  <span>{spool.current_weight.toFixed(0)}g</span>
                                  <span className="text-muted-foreground">
                                    / {spool.initial_weight.toFixed(0)}g
                                  </span>
                                </>
                              )}
                            </div>
                          )
                        })()}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          // Calculate remaining percentage across all spools in batch
                          const unusedSpools = Math.max(0, spool.spools_remaining - 1)
                          const totalCurrent = spool.current_weight + (unusedSpools * spool.initial_weight)
                          const totalInitial = spool.spools_remaining * spool.initial_weight
                          const totalPercentage = totalInitial > 0 ? (totalCurrent / totalInitial) * 100 : 0

                          return (
                            <div className="flex items-center gap-2">
                              {/* Two-colour bar: green for remaining, red for used */}
                              <div className="w-24 h-2 rounded-full overflow-hidden flex">
                                <div
                                  className="h-full bg-green-500 transition-all"
                                  style={{ width: `${totalPercentage}%` }}
                                />
                                <div
                                  className="h-full bg-destructive transition-all"
                                  style={{ width: `${100 - totalPercentage}%` }}
                                />
                              </div>
                              <span className="text-xs font-medium">
                                {totalPercentage.toFixed(0)}%
                              </span>
                            </div>
                          )
                        })()}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          // Calculate total percentage for low stock check
                          const unusedSpools = Math.max(0, spool.spools_remaining - 1)
                          const totalCurrent = spool.current_weight + (unusedSpools * spool.initial_weight)
                          const totalInitial = spool.spools_remaining * spool.initial_weight
                          const totalPercentage = totalInitial > 0 ? (totalCurrent / totalInitial) * 100 : 0

                          return (
                            <>
                              {spool.is_active ? (
                                <Badge variant="success">Active</Badge>
                              ) : (
                                <Badge variant="secondary">Inactive</Badge>
                              )}
                              {totalPercentage < 20 && (
                                <Badge variant="warning" className="ml-1">
                                  Low
                                </Badge>
                              )}
                            </>
                          )
                        })()}
                      </TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex gap-2 justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setUpdatingWeightSpoolId(spool.id)
                              setUpdateWeightDialogOpen(true)
                            }}
                          >
                            Update Weight
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditingSpoolId(spool.id)
                              setEditDialogOpen(true)
                            }}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            asChild
                            title="Print Label"
                          >
                            <Link to="/filaments/$spoolId/label" params={{ spoolId: spool.id }}>
                              <QrCode className="h-4 w-4" />
                            </Link>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDuplicate(spool.id)}
                            disabled={duplicatingSpoolId === spool.id}
                            title="Duplicate spool"
                          >
                            {duplicatingSpoolId === spool.id ? (
                              <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                            ) : (
                              <Copy className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setDeletingSpoolId(spool.id)
                              setDeleteDialogOpen(true)
                            }}
                            className="text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-muted-foreground">
                    Page {params.page} of {totalPages}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(params.page! - 1)}
                      disabled={params.page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(params.page! + 1)}
                      disabled={params.page === totalPages}
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

      {/* Add Spool Dialog */}
      <AddSpoolDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />

      {/* Edit Spool Dialog */}
      <EditSpoolDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        spoolId={editingSpoolId}
      />

      {/* Update Weight Dialog */}
      <UpdateWeightDialog
        open={updateWeightDialogOpen}
        onOpenChange={setUpdateWeightDialogOpen}
        spoolId={updatingWeightSpoolId}
      />

      {/* Delete Spool Dialog */}
      <DeleteSpoolDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        spoolId={deletingSpoolId}
      />

      {/* View Spool Dialog */}
      <ViewSpoolDialog
        open={viewDialogOpen}
        onOpenChange={setViewDialogOpen}
        spoolId={viewingSpoolId}
        onEdit={(id) => {
          setEditingSpoolId(id)
          setEditDialogOpen(true)
        }}
        onDuplicate={handleDuplicate}
      />
    </div>
  )
}
