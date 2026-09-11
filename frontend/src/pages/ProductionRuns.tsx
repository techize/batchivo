/**
 * Production Runs Page
 *
 * Main page for production run management with list and analytics views
 */

import type { ProductionRunDetail } from '@/types/production-run'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Plus, List, BarChart3 } from 'lucide-react'
import { ProductionRunList } from '@/components/production-runs/ProductionRunList'
import { VarianceDashboard } from '@/components/charts'
import { AppLayout } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { listProductionRuns, getProductionRun } from '@/lib/api/production-runs'

export function ProductionRuns() {
  const [activeTab, setActiveTab] = useState('list')

  // Fetch all runs for analytics (separate from paginated list)
  const { data: analyticsData, isLoading: analyticsLoading, error: analyticsError, refetch } = useQuery({
    queryKey: ['production-runs-analytics'],
    queryFn: async () => {
      const page = await listProductionRuns({ limit: 500 })
      const runs: ProductionRunDetail[] = []
      // Bound requests so opening analytics cannot flood the backend.
      for (let offset = 0; offset < page.runs.length; offset += 5) {
        runs.push(...await Promise.all(
          page.runs.slice(offset, offset + 5).map(run => getProductionRun(run.id))
        ))
      }
      return { ...page, runs }
    },
    enabled: activeTab === 'analytics',
  })

  return (
    <AppLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Production Runs</h1>
            <p className="text-muted-foreground text-sm sm:text-base">
              Track print jobs and analyze material variance
            </p>
          </div>
          <Button asChild className="w-full sm:w-auto">
            <Link to="/production-runs/new">
              <Plus className="h-4 w-4 mr-2" />
              New Production Run
            </Link>
          </Button>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="list" className="gap-2">
              <List className="h-4 w-4" />
              Runs
            </TabsTrigger>
            <TabsTrigger value="analytics" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              Analytics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="list" className="mt-4">
            <ProductionRunList />
          </TabsContent>

          <TabsContent value="analytics" className="mt-4">
            {analyticsError && <p role="alert">Unable to load production analytics. Please try refreshing.</p>}
            <VarianceDashboard
              runs={analyticsData?.runs || []}
              isLoading={analyticsLoading}
              onRefresh={() => refetch()}
            />
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  )
}
