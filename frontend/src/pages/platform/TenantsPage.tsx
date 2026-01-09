/**
 * Tenants Page
 *
 * Platform admin page for managing all tenants.
 * Provides search, filter, and pagination for tenant list.
 */

import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { PlatformLayout } from '@/components/platform/PlatformLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
import { useTenants } from '@/hooks/usePlatformAdmin'
import { Search, Building2, ArrowRight, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export function TenantsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useTenants({
    skip: page * limit,
    limit,
    search: search || undefined,
    is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
  })

  const tenants = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / limit)

  const handleSearchChange = (value: string) => {
    setSearch(value)
    setPage(0) // Reset to first page on search
  }

  const handleStatusChange = (value: string) => {
    setStatusFilter(value)
    setPage(0) // Reset to first page on filter change
  }

  return (
    <PlatformLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tenants</h1>
          <p className="text-muted-foreground">
            Manage all tenants on the platform
          </p>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tenants..."
                  value={search}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={statusFilter} onValueChange={handleStatusChange}>
                <SelectTrigger className="w-full sm:w-[180px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Tenants Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              All Tenants
            </CardTitle>
            <CardDescription>
              {total} tenant{total !== 1 ? 's' : ''} found
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : error ? (
              <div className="text-center py-12 text-destructive">
                Failed to load tenants. Please try again.
              </div>
            ) : tenants.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No tenants found matching your criteria.
              </div>
            ) : (
              <>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Tenant</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tenants.map((tenant) => (
                        <TableRow key={tenant.id}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{tenant.name}</p>
                              <p className="text-sm text-muted-foreground">{tenant.slug}</p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{tenant.tenant_type}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={tenant.is_active ? 'default' : 'secondary'}>
                              {tenant.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDistanceToNow(new Date(tenant.created_at), { addSuffix: true })}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/platform/tenants/${tenant.id}`}>
                                View
                                <ArrowRight className="ml-1 h-4 w-4" />
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                      Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(page - 1)}
                        disabled={page === 0}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                      </Button>
                      <span className="text-sm text-muted-foreground">
                        Page {page + 1} of {totalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(page + 1)}
                        disabled={page >= totalPages - 1}
                      >
                        Next
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </PlatformLayout>
  )
}
