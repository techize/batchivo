/**
 * Tenant Modules Page
 *
 * Platform admin page for managing tenant module access.
 * Shows all available modules with toggle switches for enable/disable.
 */

import { useParams, Link } from '@tanstack/react-router'
import { PlatformLayout } from '@/components/platform/PlatformLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
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
  useTenantModules,
  useUpdateTenantModule,
  useResetTenantModules,
} from '@/hooks/usePlatformAdmin'
import {
  ArrowLeft,
  Loader2,
  RotateCcw,
  Package,
  Layers,
  Printer,
  Factory,
  ShoppingBag,
  FolderOpen,
  Box,
} from 'lucide-react'
import { useState } from 'react'

// Module display metadata
const MODULE_DISPLAY: Record<
  string,
  { displayName: string; description: string; icon: React.ComponentType<{ className?: string }> }
> = {
  spools: {
    displayName: 'Spools / Inventory',
    description: 'Track filament spools, inventory levels, and material usage',
    icon: Box,
  },
  models: {
    displayName: '3D Models',
    description: 'Manage 3D model files, STL uploads, and model library',
    icon: Layers,
  },
  printers: {
    displayName: 'Printers',
    description: 'Manage printer fleet, assignments, and maintenance',
    icon: Printer,
  },
  production: {
    displayName: 'Production',
    description: 'Production runs, batch tracking, and manufacturing workflow',
    icon: Factory,
  },
  products: {
    displayName: 'Products',
    description: 'Product catalog, variants, and pricing management',
    icon: Package,
  },
  orders: {
    displayName: 'Orders',
    description: 'Customer orders, fulfillment, and order tracking',
    icon: ShoppingBag,
  },
  categories: {
    displayName: 'Categories',
    description: 'Product categories and organizational structure',
    icon: FolderOpen,
  },
}

export function TenantModulesPage() {
  const { tenantId } = useParams({ strict: false }) as { tenantId: string }
  const { data: tenant, isLoading: tenantLoading } = useTenantDetail(tenantId)
  const { data: modulesData, isLoading: modulesLoading } = useTenantModules(tenantId)
  const updateModuleMutation = useUpdateTenantModule()
  const resetModulesMutation = useResetTenantModules()
  const [pendingChanges, setPendingChanges] = useState<Record<string, boolean>>({})

  const isLoading = tenantLoading || modulesLoading

  const handleToggleModule = async (moduleName: string, currentEnabled: boolean) => {
    const newEnabled = !currentEnabled
    setPendingChanges((prev) => ({ ...prev, [moduleName]: true }))

    try {
      await updateModuleMutation.mutateAsync({
        tenantId,
        moduleName,
        enabled: newEnabled,
      })
    } catch (error) {
      console.error(`Failed to update module ${moduleName}:`, error)
    } finally {
      setPendingChanges((prev) => {
        const next = { ...prev }
        delete next[moduleName]
        return next
      })
    }
  }

  const handleResetToDefaults = async () => {
    try {
      await resetModulesMutation.mutateAsync(tenantId)
    } catch (error) {
      console.error('Failed to reset modules:', error)
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

  if (!tenant || !modulesData) {
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
              <p className="text-center text-muted-foreground">Tenant not found</p>
            </CardContent>
          </Card>
        </div>
      </PlatformLayout>
    )
  }

  // Check if any module differs from default
  const hasCustomConfig = modulesData.modules.some((m) => !m.is_default)

  return (
    <PlatformLayout>
      <div className="space-y-6">
        {/* Back Navigation */}
        <Button variant="ghost" asChild>
          <Link to={`/platform/tenants/${tenantId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to {tenant.name}
          </Link>
        </Button>

        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Module Management</h1>
            <p className="text-muted-foreground">
              Configure which modules are enabled for {tenant.name}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="outline">{modulesData.tenant_type.replace('_', ' ')}</Badge>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" disabled={!hasCustomConfig || resetModulesMutation.isPending}>
                  {resetModulesMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RotateCcw className="mr-2 h-4 w-4" />
                  )}
                  Reset to Defaults
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Reset to Default Configuration?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will reset all module settings to the defaults for{' '}
                    <strong>{modulesData.tenant_type.replace('_', ' ')}</strong> tenant type. Any
                    custom configuration will be lost.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleResetToDefaults}>
                    Reset to Defaults
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        {/* Modules Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modulesData.modules.map((module) => {
            const display = MODULE_DISPLAY[module.module_name] || {
              displayName: module.module_name,
              description: 'Module description not available',
              icon: Package,
            }
            const Icon = display.icon
            const isPending = pendingChanges[module.module_name]

            return (
              <Card
                key={module.module_name}
                className={module.enabled ? '' : 'opacity-60'}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`rounded-lg p-2 ${
                          module.enabled
                            ? 'bg-primary/10 text-primary'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{display.displayName}</CardTitle>
                        <div className="flex items-center gap-2 mt-1">
                          {!module.is_default && (
                            <Badge variant="secondary" className="text-xs">
                              Custom
                            </Badge>
                          )}
                          {module.configured && module.is_default && (
                            <Badge variant="outline" className="text-xs">
                              Default
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                      <Switch
                        checked={module.enabled}
                        onCheckedChange={() =>
                          handleToggleModule(module.module_name, module.enabled)
                        }
                        disabled={isPending}
                      />
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>{display.description}</CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">About Module Configuration</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              Modules control which features are available to this tenant. Disabled modules will not
              appear in the tenant's navigation or be accessible via API.
            </p>
            <p>
              <strong>Custom</strong> indicates the module status differs from the default for this
              tenant type. Use "Reset to Defaults" to restore the standard configuration.
            </p>
          </CardContent>
        </Card>
      </div>
    </PlatformLayout>
  )
}
