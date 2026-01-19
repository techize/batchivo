/**
 * ProductList Component
 *
 * Displays a paginated, searchable list of sellable products.
 * Products are composite items made of models with per-channel pricing.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Loader2, Plus, Search, Package, ArrowUpDown, Wand2 } from 'lucide-react'

import { listProducts } from '@/lib/api/products'
import { useCurrency } from '@/hooks/useCurrency'
import { ProductWizard } from '@/components/products/ProductWizard'
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

type SortOption = 'name' | 'sku' | 'recent'

export function ProductList() {
  const [search, setSearch] = useState('')
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)
  const [sortBy, setSortBy] = useState<SortOption>('recent')
  const [page, setPage] = useState(0)
  const [limit] = useState(50)
  const [wizardOpen, setWizardOpen] = useState(false)
  const { formatCurrency } = useCurrency()

  const { data, isLoading, error } = useQuery({
    queryKey: ['products', { search, isActive, skip: page * limit, limit }],
    queryFn: () =>
      listProducts({
        search: search || undefined,
        is_active: isActive,
        skip: page * limit,
        limit,
      }),
  })

  const handleSearchChange = (value: string) => {
    setSearch(value)
    setPage(0)
  }

  // handleStatusChange reserved for future dropdown filter
  // const handleStatusChange = (value: string) => {
  //   setIsActive(value === 'all' ? undefined : value === 'active')
  //   setPage(0)
  // }

  // Sort products client-side (backend returns by recent first)
  const sortedProducts = data?.products ? [...data.products].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name)
      case 'sku':
        return a.sku.localeCompare(b.sku)
      case 'recent':
      default:
        return 0
    }
  }) : []

  const totalPages = data ? Math.ceil(data.total / limit) : 0
  const activeCount = data?.products.filter(p => p.is_active).length || 0
  const inactiveCount = data?.products.filter(p => !p.is_active).length || 0

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading products</p>
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
          <h2 className="text-2xl font-bold tracking-tight">Products</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} products • {activeCount} active • Sellable items composed of models
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setWizardOpen(true)}>
            <Wand2 className="mr-2 h-4 w-4" />
            Create with Wizard
          </Button>
          <Button asChild>
            <Link to="/products/new">
              <Plus className="mr-2 h-4 w-4" />
              Quick Create
            </Link>
          </Button>
        </div>
      </div>

      {/* Product Creation Wizard */}
      <ProductWizard open={wizardOpen} onOpenChange={setWizardOpen} />

      {/* Filters Card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
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

            <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
              <SelectTrigger className="w-[140px] h-8">
                <ArrowUpDown className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">Most Recent</SelectItem>
                <SelectItem value="name">Name (A-Z)</SelectItem>
                <SelectItem value="sku">SKU (A-Z)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Package className="h-4 w-4" />
            Products
            {data && (
              <Badge variant="secondary" className="ml-2">
                {data.total}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Click on a product to view models, pricing, and cost breakdown
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Loading State */}
          {isLoading && (
            <div className="flex h-[200px] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-3">Loading products...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && sortedProducts.length === 0 && (
            <div className="flex h-[200px] items-center justify-center">
              <div className="text-center">
                <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">
                  {search
                    ? 'No products match your search'
                    : 'No products yet. Create your first product to get started.'}
                </p>
                {!search && (
                  <Button asChild className="mt-4">
                    <Link to="/products/new">
                      <Plus className="mr-2 h-4 w-4" />
                      Create Product
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Card View - Mobile/Tablet */}
          {!isLoading && sortedProducts.length > 0 && (
            <div className="lg:hidden space-y-3">
              {sortedProducts.map((product) => (
                <Link
                  key={product.id}
                  to="/products/$productId"
                  params={{ productId: product.id }}
                  className="block rounded-lg border p-4 space-y-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-medium">{product.name}</div>
                      <div className="text-sm font-mono text-muted-foreground">
                        {product.sku}
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={product.is_active ? 'bg-green-500/10 text-green-600 border-green-200' : 'bg-gray-500/10 text-gray-500 border-gray-200'}
                    >
                      {product.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <span className="font-medium">
                      Cost: {formatCurrency(product.total_make_cost || '0')}
                    </span>
                    <span className="text-green-600 font-medium">
                      SRP: {formatCurrency(product.suggested_price || '0')}
                    </span>
                    <span className="text-muted-foreground">Stock: {product.units_in_stock}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {/* Table View - Desktop */}
          {!isLoading && sortedProducts.length > 0 && (
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[120px]">SKU</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[100px] text-right">Make Cost</TableHead>
                    <TableHead className="w-[100px] text-right">SRP (2.5×)</TableHead>
                    <TableHead className="w-[80px] text-right">Stock</TableHead>
                    <TableHead className="w-[80px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedProducts.map((product) => (
                    <TableRow key={product.id} className="group">
                      <TableCell className="font-mono text-sm">{product.sku}</TableCell>
                      <TableCell>
                        <Link
                          to="/products/$productId"
                          params={{ productId: product.id }}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {product.name}
                        </Link>
                        {product.description && (
                          <p className="text-xs text-muted-foreground truncate max-w-[300px]">
                            {product.description}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={product.is_active ? 'bg-green-500/10 text-green-600 border-green-200' : 'bg-gray-500/10 text-gray-500 border-gray-200'}
                        >
                          {product.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">
                        {formatCurrency(product.total_make_cost || '0')}
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium text-green-600">
                        {formatCurrency(product.suggested_price || '0')}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {product.units_in_stock}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Link to="/products/$productId" params={{ productId: product.id }}>
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
