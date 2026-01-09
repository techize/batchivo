/**
 * Audit Logs Page
 *
 * Platform admin page for viewing all admin activity logs.
 */

import { useState } from 'react'
import { PlatformLayout } from '@/components/platform/PlatformLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
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
import { useAuditLogs } from '@/hooks/usePlatformAdmin'
import { ClipboardList, Loader2, ChevronLeft, ChevronRight, Clock } from 'lucide-react'
import { format, formatDistanceToNow } from 'date-fns'

// Action type badges
const ACTION_BADGES: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  impersonate: { label: 'Impersonate', variant: 'default' },
  deactivate_tenant: { label: 'Deactivate', variant: 'destructive' },
  reactivate_tenant: { label: 'Reactivate', variant: 'outline' },
  list_tenants: { label: 'List Tenants', variant: 'secondary' },
  view_tenant: { label: 'View Tenant', variant: 'secondary' },
}

export function AuditLogsPage() {
  const [actionFilter, setActionFilter] = useState<string>('all')
  const [page, setPage] = useState(0)
  const limit = 50

  const { data, isLoading, error } = useAuditLogs({
    skip: page * limit,
    limit,
    action: actionFilter === 'all' ? undefined : actionFilter,
  })

  const logs = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / limit)

  const handleActionChange = (value: string) => {
    setActionFilter(value)
    setPage(0)
  }

  const getActionBadge = (action: string) => {
    const config = ACTION_BADGES[action] || { label: action, variant: 'outline' as const }
    return <Badge variant={config.variant}>{config.label}</Badge>
  }

  return (
    <PlatformLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
          <p className="text-muted-foreground">
            View all platform administration activity
          </p>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <Select value={actionFilter} onValueChange={handleActionChange}>
                <SelectTrigger className="w-full sm:w-[220px]">
                  <SelectValue placeholder="Filter by action" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  <SelectItem value="impersonate">Impersonate</SelectItem>
                  <SelectItem value="deactivate_tenant">Deactivate Tenant</SelectItem>
                  <SelectItem value="reactivate_tenant">Reactivate Tenant</SelectItem>
                  <SelectItem value="list_tenants">List Tenants</SelectItem>
                  <SelectItem value="view_tenant">View Tenant</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Audit Logs Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Activity Log
            </CardTitle>
            <CardDescription>
              {total} log{total !== 1 ? 's' : ''} found
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : error ? (
              <div className="text-center py-12 text-destructive">
                Failed to load audit logs. Please try again.
              </div>
            ) : logs.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                No audit logs found.
              </div>
            ) : (
              <>
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Action</TableHead>
                        <TableHead>Target</TableHead>
                        <TableHead>Admin</TableHead>
                        <TableHead>IP Address</TableHead>
                        <TableHead>Time</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {logs.map((log) => (
                        <TableRow key={log.id}>
                          <TableCell>{getActionBadge(log.action)}</TableCell>
                          <TableCell>
                            {log.target_type && log.target_id ? (
                              <div>
                                <span className="text-muted-foreground text-xs">
                                  {log.target_type}
                                </span>
                                <code className="block text-xs bg-muted px-1 rounded mt-0.5">
                                  {log.target_id.substring(0, 8)}...
                                </code>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <code className="text-xs bg-muted px-1 rounded">
                              {log.admin_user_id.substring(0, 8)}...
                            </code>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {log.ip_address || '—'}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2 text-sm">
                              <Clock className="h-3 w-3 text-muted-foreground" />
                              <span title={format(new Date(log.created_at), 'PPpp')}>
                                {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                              </span>
                            </div>
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
