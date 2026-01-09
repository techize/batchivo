/**
 * Dashboard Home Page
 *
 * Main landing page for authenticated users showing:
 * - Summary statistics cards
 * - Active production runs
 * - Low stock alerts
 * - Performance charts
 * - Failure analytics
 * - Recent activity feed
 * - Quick actions
 */

import { AppLayout } from '@/components/layout/AppLayout';
import {
  SummaryCards,
  ActiveProduction,
  LowStockAlerts,
  ActivityFeed,
  PerformanceCharts,
  FailureAnalyticsPanel,
  QuickActions,
  RecentOrders,
} from '@/components/dashboard';

export function DashboardHome() {
  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your 3D printing operations
          </p>
        </div>

        {/* Summary Cards */}
        <SummaryCards />

        {/* Main Grid Layout */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column - Active Production & Performance */}
          <div className="space-y-6 lg:col-span-2">
            <ActiveProduction />
            <RecentOrders />
            <PerformanceCharts />
          </div>

          {/* Right Column - Alerts & Activity */}
          <div className="space-y-6">
            <QuickActions />
            <LowStockAlerts />
            <FailureAnalyticsPanel />
          </div>
        </div>

        {/* Activity Feed - Full Width */}
        <ActivityFeed />
      </div>
    </AppLayout>
  );
}
