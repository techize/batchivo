/**
 * Settings Page
 *
 * Main settings page with tabs for different configuration sections.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { EtsySettings } from '@/components/settings/EtsySettings'
import { GeneralSettings } from '@/components/settings/GeneralSettings'
import { SquareSettings } from '@/components/settings/SquareSettings'
import { TeamSettings } from '@/components/settings/TeamSettings'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Building2, CreditCard, Store, Users } from 'lucide-react'

export function Settings() {
  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Manage your organization settings and integrations
          </p>
        </div>

        <Tabs defaultValue="general" className="space-y-6">
          <TabsList>
            <TabsTrigger value="general" className="gap-2">
              <Building2 className="h-4 w-4" />
              General
            </TabsTrigger>
            <TabsTrigger value="payments" className="gap-2">
              <CreditCard className="h-4 w-4" />
              Payments
            </TabsTrigger>
            <TabsTrigger value="marketplace" className="gap-2">
              <Store className="h-4 w-4" />
              Marketplace
            </TabsTrigger>
            <TabsTrigger value="team" className="gap-2">
              <Users className="h-4 w-4" />
              Team
            </TabsTrigger>
          </TabsList>

          <TabsContent value="general">
            <GeneralSettings />
          </TabsContent>

          <TabsContent value="payments">
            <SquareSettings />
          </TabsContent>

          <TabsContent value="marketplace">
            <EtsySettings />
          </TabsContent>

          <TabsContent value="team">
            <TeamSettings />
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}
