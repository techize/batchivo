/**
 * API client functions for Dashboard
 *
 * Provides type-safe API calls for retrieving dashboard data,
 * analytics, and performance metrics.
 */

import { api } from '../api';

const BASE_PATH = '/api/v1/dashboard';

// Type definitions

export interface DashboardSummary {
  active_prints: number;
  completed_today: number;
  failed_today: number;
  cancelled_today: number;
  low_stock_count: number;
  success_rate_7d: number;
  total_waste_7d_grams: number;
}

export interface ActiveProductionRun {
  id: string;
  run_number: string;
  started_at: string;
  printer_name: string | null;
  estimated_print_time_hours: number | null;
  items_count: number;
  total_quantity: number;
  products_summary: string;
}

export interface LowStockSpool {
  id: string;
  spool_id: string;
  brand: string;
  color: string;
  color_hex: string | null;
  material_type: string;
  current_weight: number;
  initial_weight: number;
  percent_remaining: number;
  is_critical: boolean;
}

export interface RecentActivityItem {
  id: string;
  transaction_type: string;
  created_at: string;
  spool_id: string | null;
  spool_color: string | null;
  weight_change: number;
  description: string;
  production_run_id: string | null;
  run_number: string | null;
}

export interface SuccessRateTrend {
  date: string;
  success_rate: number;
  completed: number;
  failed: number;
}

export interface MaterialUsage {
  material_type: string;
  total_grams: number;
  color: string | null;
}

export interface DailyProduction {
  date: string;
  items_completed: number;
  items_failed: number;
  runs_completed: number;
}

export interface PerformanceChartData {
  success_rate_trend: SuccessRateTrend[];
  material_usage: MaterialUsage[];
  daily_production: DailyProduction[];
}

export interface FailureByReason {
  reason: string;
  count: number;
  percentage: number;
}

export interface FailureTrend {
  date: string;
  count: number;
  reasons: Record<string, number>;
}

export interface FailureAnalytics {
  failure_by_reason: FailureByReason[];
  most_common_failures: FailureByReason[];
  failure_trends: FailureTrend[];
  total_failures: number;
  failure_rate: number;
}

// API Functions

/**
 * Get dashboard summary statistics
 * @param lowStockThreshold - Percentage threshold for low stock (default: 10)
 */
export async function getDashboardSummary(
  lowStockThreshold: number = 10
): Promise<DashboardSummary> {
  const params = new URLSearchParams();
  params.append('low_stock_threshold', lowStockThreshold.toString());
  const response = await api.get<DashboardSummary>(
    `${BASE_PATH}/summary?${params.toString()}`
  );
  return response.data;
}

/**
 * Get active (in_progress) production runs
 */
export async function getActiveProduction(): Promise<ActiveProductionRun[]> {
  const response = await api.get<ActiveProductionRun[]>(
    `${BASE_PATH}/active-production`
  );
  return response.data;
}

/**
 * Get low stock spools
 * @param thresholdPercent - Percentage threshold for low stock (default: 10)
 * @param limit - Maximum number of spools to return (default: 20)
 */
export async function getLowStockSpools(
  thresholdPercent: number = 10,
  limit: number = 20
): Promise<LowStockSpool[]> {
  const params = new URLSearchParams();
  params.append('threshold_percent', thresholdPercent.toString());
  params.append('limit', limit.toString());
  const response = await api.get<LowStockSpool[]>(
    `${BASE_PATH}/low-stock?${params.toString()}`
  );
  return response.data;
}

/**
 * Get recent activity feed
 * @param limit - Maximum number of items to return (default: 20)
 */
export async function getRecentActivity(
  limit: number = 20
): Promise<RecentActivityItem[]> {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  const response = await api.get<RecentActivityItem[]>(
    `${BASE_PATH}/recent-activity?${params.toString()}`
  );
  return response.data;
}

/**
 * Get performance chart data
 * @param days - Number of days to include (default: 7)
 */
export async function getPerformanceCharts(
  days: number = 7
): Promise<PerformanceChartData> {
  const params = new URLSearchParams();
  params.append('days', days.toString());
  const response = await api.get<PerformanceChartData>(
    `${BASE_PATH}/performance-charts?${params.toString()}`
  );
  return response.data;
}

/**
 * Get failure analytics data
 * @param days - Number of days to analyze (default: 30)
 */
export async function getFailureAnalytics(
  days: number = 30
): Promise<FailureAnalytics> {
  const params = new URLSearchParams();
  params.append('days', days.toString());
  const response = await api.get<FailureAnalytics>(
    `${BASE_PATH}/failure-analytics?${params.toString()}`
  );
  return response.data;
}

// Utility functions

/**
 * Format transaction type for display
 */
export function formatTransactionType(type: string): string {
  const typeMap: Record<string, string> = {
    PURCHASE: 'Purchase',
    USAGE: 'Usage',
    ADJUSTMENT: 'Adjustment',
    TRANSFER: 'Transfer',
    RETURN: 'Return',
    WASTE: 'Waste',
    COUNT: 'Count',
  };
  return typeMap[type] || type;
}

/**
 * Get transaction type badge color
 */
export function getTransactionTypeColor(type: string): string {
  const colorMap: Record<string, string> = {
    PURCHASE: 'green',
    USAGE: 'blue',
    ADJUSTMENT: 'yellow',
    TRANSFER: 'purple',
    RETURN: 'cyan',
    WASTE: 'red',
    COUNT: 'gray',
  };
  return colorMap[type] || 'gray';
}

/**
 * Format weight change with sign for display
 */
export function formatWeightChange(grams: number): string {
  const sign = grams >= 0 ? '+' : '';
  return `${sign}${grams.toFixed(1)}g`;
}

/**
 * Calculate time ago for activity feed
 */
export function timeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/**
 * Format failure reason for display (capitalize and replace underscores)
 */
export function formatFailureReason(reason: string): string {
  return reason
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get color for failure reason chart (predefined colors for common reasons)
 */
export function getFailureReasonColor(reason: string): string {
  const colorMap: Record<string, string> = {
    spaghetti: '#ef4444', // red-500
    layer_shift: '#f97316', // orange-500
    clog: '#eab308', // yellow-500
    adhesion: '#22c55e', // green-500
    overheating: '#06b6d4', // cyan-500
    underextrusion: '#3b82f6', // blue-500
    mechanical: '#8b5cf6', // violet-500
    power_failure: '#ec4899', // pink-500
    other: '#6b7280', // gray-500
    Unknown: '#9ca3af', // gray-400
  };
  return colorMap[reason] || '#6b7280';
}
