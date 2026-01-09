import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { consumablesApi } from '@/lib/api/consumables'
import type { ConsumableTypeListParams } from '@/types/consumable'
import { CONSUMABLE_CATEGORIES } from '@/types/consumable'
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
import {
  Search,
  Plus,
  RefreshCcw,
  Trash2,
  X,
  Edit,
  ShoppingCart,
  AlertTriangle,
  Package,
} from 'lucide-react'
import { AddConsumableDialog } from './AddConsumableDialog'
import { AddPurchaseDialog } from './AddPurchaseDialog'
import { EditConsumableDialog } from './EditConsumableDialog'
import { DeleteConsumableDialog } from './DeleteConsumableDialog'

export function ConsumableList() {
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [purchaseDialogOpen, setPurchaseDialogOpen] = useState(false)
  const [purchaseConsumableId, setPurchaseConsumableId] = useState<string | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingConsumableId, setEditingConsumableId] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingConsumableId, setDeletingConsumableId] = useState<string | null>(null)
  const [params, setParams] = useState<ConsumableTypeListParams>({
    page: 1,
    page_size: 20,
    search: '',
    low_stock_only: false,
  })

  // Fetch consumables with react-query
  const {
    data: consumableData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['consumables', params],
    queryFn: () => consumablesApi.list(params),
  })

  // Fetch low stock alerts
  const { data: lowStockAlerts } = useQuery({
    queryKey: ['consumables', 'low-stock'],
    queryFn: () => consumablesApi.getLowStockAlerts(),
  })

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

  const handleCategoryFilter = (category: string) => {
    setParams((prev) => ({
      ...prev,
      category: category === 'all' ? undefined : category,
      page: 1,
    }))
  }

  const clearFilters = () => {
    setParams({
      page: 1,
      page_size: 20,
      search: '',
      low_stock_only: false,
    })
  }

  const handleAddPurchase = (consumableId: string) => {
    setPurchaseConsumableId(consumableId)
    setPurchaseDialogOpen(true)
  }

  // Calculate total pages
  const totalPages = consumableData ? Math.ceil(consumableData.total / params.page_size!) : 0

  // Format currency
  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return `£${value.toFixed(2)}`
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Consumables Inventory</h1>
          <p className="text-muted-foreground">
            Manage magnets, inserts, hardware, and other consumables
          </p>
        </div>
        <Button onClick={() => setAddDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Consumable
        </Button>
      </div>

      {/* Low Stock Alert Banner */}
      {lowStockAlerts && lowStockAlerts.length > 0 && (
        <Card className="border-warning bg-warning/10">
          <CardContent className="flex items-center gap-3 py-3">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <div className="flex-1">
              <p className="font-medium text-warning">
                {lowStockAlerts.length} item{lowStockAlerts.length !== 1 ? 's' : ''} low on stock
              </p>
              <p className="text-sm text-muted-foreground">
                {lowStockAlerts.slice(0, 3).map((a) => a.name).join(', ')}
                {lowStockAlerts.length > 3 && ` and ${lowStockAlerts.length - 3} more...`}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={toggleLowStock}
              className={params.low_stock_only ? 'bg-warning/20' : ''}
            >
              {params.low_stock_only ? 'Show All' : 'View Low Stock'}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Filters Card */}
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Search and filter your consumable inventory</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search and Quick Filters */}
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by SKU or name..."
                  className="pl-8"
                  value={params.search}
                  onChange={(e) => handleSearch(e.target.value)}
                />
              </div>
            </div>
            <Button
              variant={params.low_stock_only ? 'default' : 'outline'}
              onClick={toggleLowStock}
            >
              Low Stock Only
            </Button>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
          </div>

          {/* Category Filter */}
          <div className="flex gap-4 items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="category-filter" className="text-sm">
                Category
              </Label>
              <Select
                value={params.category || 'all'}
                onValueChange={handleCategoryFilter}
              >
                <SelectTrigger id="category-filter">
                  <SelectValue placeholder="All categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {CONSUMABLE_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat.charAt(0).toUpperCase() + cat.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {(params.search || params.category || params.low_stock_only) && (
              <Button variant="outline" onClick={clearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              Consumables
              {consumableData && (
                <span className="ml-2 text-muted-foreground font-normal text-sm">
                  ({consumableData.total} total)
                </span>
              )}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3 text-muted-foreground">Loading consumables...</span>
            </div>
          )}

          {isError && (
            <div className="bg-destructive/10 border border-destructive rounded-md p-4">
              <p className="text-destructive font-medium">Error loading consumables</p>
              <p className="text-sm text-muted-foreground mt-2">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          )}

          {consumableData && consumableData.consumables.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No consumables found</p>
              <p className="text-sm mt-2">
                {params.search || params.category || params.low_stock_only
                  ? 'Try adjusting your filters'
                  : 'Get started by adding your first consumable'}
              </p>
              {!params.search && !params.category && !params.low_stock_only && (
                <Button className="mt-4" onClick={() => setAddDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Consumable
                </Button>
              )}
            </div>
          )}

          {consumableData && consumableData.consumables.length > 0 && (
            <>
              {/* Card View - Mobile/Tablet */}
              <div className="lg:hidden space-y-3">
                {consumableData.consumables.map((consumable) => (
                  <div
                    key={consumable.id}
                    className="border rounded-lg p-4 space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium">{consumable.name}</div>
                        <div className="text-sm font-mono text-muted-foreground">
                          {consumable.sku}
                        </div>
                        {consumable.preferred_supplier && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {consumable.preferred_supplier}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-1">
                        {consumable.is_active ? (
                          <Badge variant="success">Active</Badge>
                        ) : (
                          <Badge variant="secondary">Inactive</Badge>
                        )}
                        {consumable.is_low_stock && (
                          <Badge variant="warning">Low</Badge>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Category:</span>
                        <Badge variant="outline" className="ml-2">
                          {consumable.category || 'Uncategorized'}
                        </Badge>
                      </div>
                      <div>
                        <span className="text-muted-foreground">On Hand:</span>
                        <span className="ml-2 font-mono">
                          {consumable.quantity_on_hand} {consumable.unit_of_measure}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Cost/Unit:</span>
                        <span className="ml-2 font-mono">
                          {formatCurrency(consumable.current_cost_per_unit)}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Value:</span>
                        <span className="ml-2 font-mono">
                          {formatCurrency(consumable.stock_value)}
                        </span>
                      </div>
                    </div>

                    <div className="flex gap-2 pt-2 border-t">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => handleAddPurchase(consumable.id)}
                      >
                        <ShoppingCart className="h-4 w-4 mr-2" />
                        Purchase
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditingConsumableId(consumable.id)
                          setEditDialogOpen(true)
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setDeletingConsumableId(consumable.id)
                          setDeleteDialogOpen(true)
                        }}
                        className="text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Table View - Desktop */}
              <div className="hidden lg:block -mx-6 px-6 overflow-x-auto">
                <Table>
                  <TableCaption>
                    Showing page {params.page} of {totalPages}
                  </TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[100px]">SKU</TableHead>
                      <TableHead className="min-w-[180px]">Name</TableHead>
                      <TableHead className="min-w-[100px]">Category</TableHead>
                      <TableHead className="min-w-[80px] text-right">On Hand</TableHead>
                      <TableHead className="min-w-[100px] text-right">Cost/Unit</TableHead>
                      <TableHead className="min-w-[100px] text-right">Stock Value</TableHead>
                      <TableHead className="min-w-[100px]">Status</TableHead>
                      <TableHead className="text-right min-w-[180px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {consumableData.consumables.map((consumable) => (
                      <TableRow key={consumable.id}>
                        <TableCell className="font-medium font-mono">
                          {consumable.sku}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span>{consumable.name}</span>
                            {consumable.preferred_supplier && (
                              <span className="text-xs text-muted-foreground">
                                {consumable.preferred_supplier}
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {consumable.category || 'Uncategorized'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {consumable.quantity_on_hand} {consumable.unit_of_measure}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(consumable.current_cost_per_unit)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrency(consumable.stock_value)}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {consumable.is_active ? (
                              <Badge variant="success">Active</Badge>
                            ) : (
                              <Badge variant="secondary">Inactive</Badge>
                            )}
                            {consumable.is_low_stock && (
                              <Badge variant="warning">Low</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex gap-2 justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAddPurchase(consumable.id)}
                              title="Add purchase"
                            >
                              <ShoppingCart className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setEditingConsumableId(consumable.id)
                                setEditDialogOpen(true)
                              }}
                              title="Edit"
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setDeletingConsumableId(consumable.id)
                                setDeleteDialogOpen(true)
                              }}
                              className="text-destructive hover:bg-destructive/10"
                              title="Delete"
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

      {/* Dialogs */}
      <AddConsumableDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />

      <AddPurchaseDialog
        open={purchaseDialogOpen}
        onOpenChange={setPurchaseDialogOpen}
        consumableId={purchaseConsumableId}
      />

      <EditConsumableDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        consumableId={editingConsumableId}
      />

      <DeleteConsumableDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        consumableId={deletingConsumableId}
      />
    </div>
  )
}
