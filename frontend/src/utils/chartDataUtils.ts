/**
 * Utility functions for chart data transformation and CSV export
 */

import { format, parseISO } from 'date-fns'
import type { ProductionRun, ProductionRunDetail } from '@/types/production-run'

/**
 * Calculate variance statistics from production runs
 */
export interface VarianceStats {
  totalRuns: number
  completedRuns: number
  averageVarianceGrams: number
  averageVariancePercent: number
  maxVarianceGrams: number
  minVarianceGrams: number
  totalEstimatedGrams: number
  totalActualGrams: number
  runsOverEstimate: number
  runsUnderEstimate: number
}

export function calculateVarianceStats(runs: ProductionRun[]): VarianceStats {
  const completedRuns = runs.filter(
    (run) =>
      run.status === 'completed' &&
      run.variance_grams != null &&
      run.variance_percentage != null
  )

  if (completedRuns.length === 0) {
    return {
      totalRuns: runs.length,
      completedRuns: 0,
      averageVarianceGrams: 0,
      averageVariancePercent: 0,
      maxVarianceGrams: 0,
      minVarianceGrams: 0,
      totalEstimatedGrams: 0,
      totalActualGrams: 0,
      runsOverEstimate: 0,
      runsUnderEstimate: 0,
    }
  }

  const variances = completedRuns.map((run) => run.variance_grams || 0)
  const variancePercents = completedRuns.map((run) => run.variance_percentage || 0)

  return {
    totalRuns: runs.length,
    completedRuns: completedRuns.length,
    averageVarianceGrams:
      variances.reduce((sum, v) => sum + v, 0) / variances.length,
    averageVariancePercent:
      variancePercents.reduce((sum, v) => sum + v, 0) / variancePercents.length,
    maxVarianceGrams: Math.max(...variances),
    minVarianceGrams: Math.min(...variances),
    totalEstimatedGrams: completedRuns.reduce(
      (sum, run) => sum + (run.estimated_total_weight_grams || 0),
      0
    ),
    totalActualGrams: completedRuns.reduce(
      (sum, run) => sum + (run.actual_total_weight_grams || 0),
      0
    ),
    runsOverEstimate: variances.filter((v) => v > 0).length,
    runsUnderEstimate: variances.filter((v) => v < 0).length,
  }
}

/**
 * Filter runs by date range
 */
export function filterRunsByDateRange(
  runs: ProductionRun[],
  startDate?: Date,
  endDate?: Date
): ProductionRun[] {
  return runs.filter((run) => {
    const runDate = new Date(run.started_at)
    if (startDate && runDate < startDate) return false
    if (endDate && runDate > endDate) return false
    return true
  })
}

/**
 * Filter runs by variance threshold
 */
export function filterRunsByVarianceThreshold(
  runs: ProductionRun[],
  minVariancePercent?: number,
  maxVariancePercent?: number
): ProductionRun[] {
  return runs.filter((run) => {
    const variance = Math.abs(run.variance_percentage || 0)
    if (minVariancePercent != null && variance < minVariancePercent) return false
    if (maxVariancePercent != null && variance > maxVariancePercent) return false
    return true
  })
}

/**
 * CSV export types
 */
export interface CSVExportRow {
  [key: string]: string | number | null
}

/**
 * Convert production runs to CSV format
 */
export function runsToCSV(runs: ProductionRun[]): string {
  const headers = [
    'Run Number',
    'Date',
    'Status',
    'Estimated (g)',
    'Actual (g)',
    'Variance (g)',
    'Variance (%)',
    'Print Time (hrs)',
    'Printer',
  ]

  const rows = runs.map((run) => [
    run.run_number,
    format(parseISO(run.started_at), 'yyyy-MM-dd'),
    run.status,
    run.estimated_total_weight_grams?.toFixed(1) || '',
    run.actual_total_weight_grams?.toFixed(1) || '',
    run.variance_grams?.toFixed(1) || '',
    run.variance_percentage?.toFixed(1) || '',
    run.duration_hours?.toFixed(1) || '',
    run.printer_name || '',
  ])

  return [headers.join(','), ...rows.map((row) => row.join(','))].join('\n')
}

/**
 * Convert variance stats to CSV format
 */
export function statsToCSV(stats: VarianceStats, dateRange?: { start?: Date; end?: Date }): string {
  const lines = [
    ['Variance Analysis Report'],
    [''],
    [
      'Date Range:',
      dateRange?.start ? format(dateRange.start, 'yyyy-MM-dd') : 'All',
      'to',
      dateRange?.end ? format(dateRange.end, 'yyyy-MM-dd') : 'Present',
    ],
    [''],
    ['Summary Statistics'],
    ['Total Runs', stats.totalRuns],
    ['Completed Runs', stats.completedRuns],
    ['Average Variance (g)', stats.averageVarianceGrams.toFixed(1)],
    ['Average Variance (%)', stats.averageVariancePercent.toFixed(1)],
    ['Max Variance (g)', stats.maxVarianceGrams.toFixed(1)],
    ['Min Variance (g)', stats.minVarianceGrams.toFixed(1)],
    ['Total Estimated (g)', stats.totalEstimatedGrams.toFixed(1)],
    ['Total Actual (g)', stats.totalActualGrams.toFixed(1)],
    ['Runs Over Estimate', stats.runsOverEstimate],
    ['Runs Under Estimate', stats.runsUnderEstimate],
  ]

  return lines.map((line) => line.join(',')).join('\n')
}

/**
 * Download CSV content as file
 */
export function downloadCSV(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}

/**
 * Get products with highest variance for BOM review
 */
export interface HighVarianceProduct {
  modelId: string
  modelName: string
  modelSku: string
  averageVariancePercent: number
  runCount: number
  recommendation: 'update' | 'review' | 'ok'
}

export function getHighVarianceProducts(
  runs: ProductionRunDetail[],
  limit = 10
): HighVarianceProduct[] {
  const productMap = new Map<
    string,
    { name: string; sku: string; variances: number[] }
  >()

  runs
    .filter((run) => run.status === 'completed')
    .forEach((run) => {
      run.items.forEach((item) => {
        if (!item.model) return

        const existing = productMap.get(item.model.id)
        const variance = run.variance_percentage || 0

        if (existing) {
          existing.variances.push(variance)
        } else {
          productMap.set(item.model.id, {
            name: item.model.name,
            sku: item.model.sku,
            variances: [variance],
          })
        }
      })
    })

  return Array.from(productMap.entries())
    .map(([modelId, data]) => {
      const avgVariance =
        data.variances.reduce((sum, v) => sum + Math.abs(v), 0) / data.variances.length

      return {
        modelId,
        modelName: data.name,
        modelSku: data.sku,
        averageVariancePercent: avgVariance,
        runCount: data.variances.length,
        recommendation:
          avgVariance > 15 ? 'update' : avgVariance > 5 ? 'review' : 'ok',
      } as HighVarianceProduct
    })
    .sort((a, b) => b.averageVariancePercent - a.averageVariancePercent)
    .slice(0, limit)
}
