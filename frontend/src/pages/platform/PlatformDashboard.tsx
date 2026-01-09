/**
 * Platform Dashboard
 *
 * Overview page for platform administrators showing:
 * - Total tenants and users
 * - Recent activity
 * - Quick links to manage tenants
 */

import { Link } from '@tanstack/react-router'
import { PlatformLayout } from '@/components/platform/PlatformLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTenants, useAuditLogs } from '@/hooks/usePlatformAdmin'
import { Building2, Users, Activity, ArrowRight, Loader2, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export function PlatformDashboard() {
  const { data: tenantsData, isLoading: tenantsLoading } = useTenants({ limit: 5 })
  const { data: auditData, isLoading: auditLoading } = useAuditLogs({ limit: 10 })

  const totalTenants = tenantsData?.total ?? 0
  const activeTenants = tenantsData?.items.filter(t => t.is_active).length ?? 0
  const recentTenants = tenantsData?.items ?? []
  const recentAuditLogs = auditData?.items ?? []

  return (
    <PlatformLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Platform Dashboard</h1>
          <p className="text-muted-foreground">
            Manage tenants, users, and platform settings
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Tenants</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {tenantsLoading ? (
                <Loader2 className="h-8 w-8 animate-spin" />
              ) : (
                <>
                  <div className="text-2xl font-bold">{totalTenants}</div>
                  <p className="text-xs text-muted-foreground">
                    {activeTenants} active
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Now</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{activeTenants}</div>
              <p className="text-xs text-muted-foreground">
                Active tenants
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {auditLoading ? (
                <Loader2 className="h-8 w-8 animate-spin" />
              ) : (
                <>
                  <div className="text-2xl font-bold">{auditData?.total ?? 0}</div>
                  <p className="text-xs text-muted-foreground">
                    Admin actions logged
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Content Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Recent Tenants */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Tenants</CardTitle>
              <CardDescription>
                Newest tenants on the platform
              </CardDescription>
            </CardHeader>
            <CardContent>
              {tenantsLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : recentTenants.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No tenants found
                </p>
              ) : (
                <div className="space-y-4">
                  {recentTenants.map((tenant) => (
                    <div
                      key={tenant.id}
                      className="flex items-center justify-between border-b pb-3 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${tenant.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />
                        <div>
                          <p className="font-medium">{tenant.name}</p>
                          <p className="text-sm text-muted-foreground">{tenant.slug}</p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <Link to={`/platform/tenants/${tenant.id}`}>
                          View
                          <ArrowRight className="ml-1 h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  ))}
                  <Button variant="outline" className="w-full" asChild>
                    <Link to="/platform/tenants">
                      View All Tenants
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                Latest platform admin actions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {auditLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : recentAuditLogs.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">
                  No recent activity
                </p>
              ) : (
                <div className="space-y-4">
                  {recentAuditLogs.slice(0, 5).map((log) => (
                    <div
                      key={log.id}
                      className="flex items-start gap-3 border-b pb-3 last:border-0"
                    >
                      <Clock className="h-4 w-4 text-muted-foreground mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">{log.action}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                  ))}
                  <Button variant="outline" className="w-full" asChild>
                    <Link to="/platform/audit">
                      View All Activity
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </PlatformLayout>
  )
}
