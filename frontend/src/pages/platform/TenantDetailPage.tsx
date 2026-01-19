/**
 * Tenant Detail Page
 *
 * Platform admin page for viewing and managing a specific tenant.
 * Shows tenant details, statistics, and administrative actions.
 */

import { useParams, Link } from '@tanstack/react-router'
import { PlatformLayout } from '@/components/platform/PlatformLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  useTenantDetail,
  useDeactivateTenant,
  useReactivateTenant,
} from '@/hooks/usePlatformAdmin'
import { useImpersonation } from '@/hooks/useImpersonation'
import {
  Building2,
  Users,
  Package,
  ShoppingCart,
  DollarSign,
  ArrowLeft,
  Loader2,
  UserCog,
  Power,
  PowerOff,
  Calendar,
  Globe,
} from 'lucide-react'
import { format } from 'date-fns'

export function TenantDetailPage() {
  const { tenantId } = useParams({ strict: false }) as { tenantId: string }
  const { data: tenant, isLoading, error, refetch } = useTenantDetail(tenantId)
  const deactivateMutation = useDeactivateTenant()
  const reactivateMutation = useReactivateTenant()
  const { startImpersonation, isLoading: isImpersonating } = useImpersonation()

  const handleImpersonate = async () => {
    if (!tenant) return
    try {
      await startImpersonation(tenant.id, tenant.name)
      // Redirect to dashboard after impersonation
      window.location.href = '/dashboard'
    } catch (error) {
      console.error('Failed to impersonate tenant:', error)
    }
  }

  const handleDeactivate = async () => {
    if (!tenant) return
    try {
      await deactivateMutation.mutateAsync(tenant.id)
      refetch()
    } catch (error) {
      console.error('Failed to deactivate tenant:', error)
    }
  }

  const handleReactivate = async () => {
    if (!tenant) return
    try {
      await reactivateMutation.mutateAsync(tenant.id)
      refetch()
    } catch (error) {
      console.error('Failed to reactivate tenant:', error)
    }
  }

  if (isLoading) {
    return (
      <PlatformLayout>
        <div className="flex justify-center py-24">
          <Loader2 className="h-12 w-12 animate-spin" />
        </div>
      </PlatformLayout>
    )
  }

  if (error || !tenant) {
    return (
      <PlatformLayout>
        <div className="space-y-6">
          <Button variant="ghost" asChild>
            <Link to="/platform/tenants">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Tenants
            </Link>
          </Button>
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-destructive">
                {error ? 'Failed to load tenant details.' : 'Tenant not found.'}
              </div>
            </CardContent>
          </Card>
        </div>
      </PlatformLayout>
    )
  }

  const shopSettings = tenant.settings?.shop as Record<string, unknown> | undefined

  return (
    <PlatformLayout>
      <div className="space-y-6">
        {/* Back Button */}
        <Button variant="ghost" asChild>
          <Link to="/platform/tenants">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Tenants
          </Link>
        </Button>

        {/* Tenant Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="bg-primary/10 p-3 rounded-lg">
              <Building2 className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{tenant.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={tenant.is_active ? 'default' : 'secondary'}>
                  {tenant.is_active ? 'Active' : 'Inactive'}
                </Badge>
                <Badge variant="outline">{tenant.tenant_type}</Badge>
                <span className="text-sm text-muted-foreground">{tenant.slug}</span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="default"
              onClick={handleImpersonate}
              disabled={!tenant.is_active || isImpersonating}
            >
              <UserCog className="mr-2 h-4 w-4" />
              {isImpersonating ? 'Impersonating...' : 'Impersonate'}
            </Button>

            <Button variant="outline" asChild>
              <Link to={`/platform/tenants/${tenant.id}/modules`}>
                <Package className="mr-2 h-4 w-4" />
                Manage Modules
              </Link>
            </Button>

            {tenant.is_active ? (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" disabled={deactivateMutation.isPending}>
                    <PowerOff className="mr-2 h-4 w-4" />
                    Deactivate
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Deactivate Tenant?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will prevent all users from accessing {tenant.name}. The tenant
                      can be reactivated later. No data will be deleted.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleDeactivate}>
                      Deactivate
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : (
              <Button
                variant="outline"
                onClick={handleReactivate}
                disabled={reactivateMutation.isPending}
              >
                <Power className="mr-2 h-4 w-4" />
                Reactivate
              </Button>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Users</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{tenant.user_count}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Products</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{tenant.product_count}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Orders</CardTitle>
              <ShoppingCart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{tenant.order_count}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Revenue</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                £{tenant.total_revenue.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Details Grid */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Tenant Information */}
          <Card>
            <CardHeader>
              <CardTitle>Tenant Information</CardTitle>
              <CardDescription>Basic tenant details and configuration</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4">
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-muted-foreground">Tenant ID</span>
                  <code className="text-sm bg-muted px-2 py-1 rounded">{tenant.id}</code>
                </div>
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-muted-foreground">Slug</span>
                  <span className="font-medium">{tenant.slug}</span>
                </div>
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-muted-foreground">Type</span>
                  <Badge variant="outline">{tenant.tenant_type}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Created
                  </span>
                  <span>{format(new Date(tenant.created_at), 'PPP')}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Shop Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Shop Configuration</CardTitle>
              <CardDescription>Online shop settings and status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {shopSettings ? (
                <div className="grid gap-4">
                  <div className="flex items-center justify-between border-b pb-2">
                    <span className="text-muted-foreground">Shop Enabled</span>
                    <Badge variant={shopSettings.enabled ? 'default' : 'secondary'}>
                      {shopSettings.enabled ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                  {shopSettings.shop_name && (
                    <div className="flex items-center justify-between border-b pb-2">
                      <span className="text-muted-foreground">Shop Name</span>
                      <span className="font-medium">{shopSettings.shop_name as string}</span>
                    </div>
                  )}
                  {shopSettings.custom_domain && (
                    <div className="flex items-center justify-between border-b pb-2">
                      <span className="text-muted-foreground flex items-center gap-2">
                        <Globe className="h-4 w-4" />
                        Custom Domain
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{shopSettings.custom_domain as string}</span>
                        {shopSettings.custom_domain_verified && (
                          <Badge variant="default" className="text-xs">Verified</Badge>
                        )}
                      </div>
                    </div>
                  )}
                  {shopSettings.order_prefix && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Order Prefix</span>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {shopSettings.order_prefix as string}
                      </code>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-4">
                  No shop configuration found
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </PlatformLayout>
  )
}
