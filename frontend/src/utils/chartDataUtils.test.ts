/**
 * Tests for chartDataUtils
 */

import { describe, it, expect } from 'vitest'
import {
  calculateVarianceStats,
  filterRunsByDateRange,
  filterRunsByVarianceThreshold,
  runsToCSV,
  statsToCSV,
  getHighVarianceProducts,
  type VarianceStats,
} from './chartDataUtils'
import type { ProductionRun, ProductionRunDetail } from '@/types/production-run'

// Mock production run factory
function createMockRun(overrides: Partial<ProductionRun> = {}): ProductionRun {
  return {
    id: 'run-1',
    run_number: 'RUN-001',
    status: 'completed',
    started_at: '2024-01-15T10:00:00Z',
    completed_at: '2024-01-15T12:00:00Z',
    estimated_total_weight_grams: 100,
    actual_total_weight_grams: 105,
    variance_grams: 5,
    variance_percentage: 5,
    duration_hours: 2,
    printer_name: 'Printer 1',
    printer_id: 'printer-1',
    items: [],
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T12:00:00Z',
    ...overrides,
  }
}

describe('calculateVarianceStats', () => {
  it('returns zeros for empty array', () => {
    const stats = calculateVarianceStats([])
    expect(stats.totalRuns).toBe(0)
    expect(stats.completedRuns).toBe(0)
    expect(stats.averageVarianceGrams).toBe(0)
    expect(stats.averageVariancePercent).toBe(0)
  })

  it('returns zeros for non-completed runs', () => {
    const runs = [
      createMockRun({ status: 'in_progress', variance_grams: null, variance_percentage: null }),
      createMockRun({ status: 'pending', variance_grams: null, variance_percentage: null }),
    ]
    const stats = calculateVarianceStats(runs)
    expect(stats.totalRuns).toBe(2)
    expect(stats.completedRuns).toBe(0)
    expect(stats.averageVarianceGrams).toBe(0)
  })

  it('calculates correct stats for completed runs', () => {
    const runs = [
      createMockRun({ variance_grams: 10, variance_percentage: 10, estimated_total_weight_grams: 100, actual_total_weight_grams: 110 }),
      createMockRun({ variance_grams: -5, variance_percentage: -5, estimated_total_weight_grams: 100, actual_total_weight_grams: 95 }),
      createMockRun({ variance_grams: 15, variance_percentage: 15, estimated_total_weight_grams: 100, actual_total_weight_grams: 115 }),
    ]
    const stats = calculateVarianceStats(runs)

    expect(stats.totalRuns).toBe(3)
    expect(stats.completedRuns).toBe(3)
    expect(stats.averageVarianceGrams).toBeCloseTo((10 + (-5) + 15) / 3)
    expect(stats.averageVariancePercent).toBeCloseTo((10 + (-5) + 15) / 3)
    expect(stats.maxVarianceGrams).toBe(15)
    expect(stats.minVarianceGrams).toBe(-5)
    expect(stats.totalEstimatedGrams).toBe(300)
    expect(stats.totalActualGrams).toBe(320)
    expect(stats.runsOverEstimate).toBe(2)
    expect(stats.runsUnderEstimate).toBe(1)
  })

  it('handles mixed completed and non-completed runs', () => {
    const runs = [
      createMockRun({ status: 'completed', variance_grams: 10, variance_percentage: 10 }),
      createMockRun({ status: 'in_progress', variance_grams: null, variance_percentage: null }),
      createMockRun({ status: 'completed', variance_grams: 20, variance_percentage: 20 }),
    ]
    const stats = calculateVarianceStats(runs)

    expect(stats.totalRuns).toBe(3)
    expect(stats.completedRuns).toBe(2)
    expect(stats.averageVarianceGrams).toBe(15)
  })
})

describe('filterRunsByDateRange', () => {
  const runs = [
    createMockRun({ started_at: '2024-01-10T10:00:00Z' }),
    createMockRun({ started_at: '2024-01-15T10:00:00Z' }),
    createMockRun({ started_at: '2024-01-20T10:00:00Z' }),
    createMockRun({ started_at: '2024-01-25T10:00:00Z' }),
  ]

  it('returns all runs when no date range specified', () => {
    const filtered = filterRunsByDateRange(runs)
    expect(filtered).toHaveLength(4)
  })

  it('filters by start date only', () => {
    const filtered = filterRunsByDateRange(runs, new Date('2024-01-15'))
    expect(filtered).toHaveLength(3)
  })

  it('filters by end date only', () => {
    const filtered = filterRunsByDateRange(runs, undefined, new Date('2024-01-18'))
    expect(filtered).toHaveLength(2)
  })

  it('filters by date range', () => {
    const filtered = filterRunsByDateRange(
      runs,
      new Date('2024-01-12'),
      new Date('2024-01-22')
    )
    expect(filtered).toHaveLength(2)
  })

  it('returns empty array when no runs in range', () => {
    const filtered = filterRunsByDateRange(
      runs,
      new Date('2024-02-01'),
      new Date('2024-02-28')
    )
    expect(filtered).toHaveLength(0)
  })
})

describe('filterRunsByVarianceThreshold', () => {
  const runs = [
    createMockRun({ variance_percentage: 2 }),
    createMockRun({ variance_percentage: -3 }),
    createMockRun({ variance_percentage: 10 }),
    createMockRun({ variance_percentage: -15 }),
    createMockRun({ variance_percentage: 25 }),
  ]

  it('returns all runs when no threshold specified', () => {
    const filtered = filterRunsByVarianceThreshold(runs)
    expect(filtered).toHaveLength(5)
  })

  it('filters by minimum variance', () => {
    const filtered = filterRunsByVarianceThreshold(runs, 5)
    expect(filtered).toHaveLength(3)
  })

  it('filters by maximum variance', () => {
    const filtered = filterRunsByVarianceThreshold(runs, undefined, 10)
    expect(filtered).toHaveLength(3)
  })

  it('filters by variance range', () => {
    const filtered = filterRunsByVarianceThreshold(runs, 5, 20)
    expect(filtered).toHaveLength(2)
  })

  it('uses absolute value for filtering', () => {
    // -15 has abs value 15, should be included when min is 10
    const filtered = filterRunsByVarianceThreshold(runs, 10)
    expect(filtered).toHaveLength(3)
  })
})

describe('runsToCSV', () => {
  it('generates CSV with headers', () => {
    const runs: ProductionRun[] = []
    const csv = runsToCSV(runs)
    expect(csv).toContain('Run Number')
    expect(csv).toContain('Date')
    expect(csv).toContain('Status')
    expect(csv).toContain('Variance (g)')
  })

  it('includes run data in CSV', () => {
    const runs = [
      createMockRun({
        run_number: 'RUN-123',
        status: 'completed',
        started_at: '2024-03-15T10:00:00Z',
        variance_grams: 5.5,
        variance_percentage: 3.2,
      }),
    ]
    const csv = runsToCSV(runs)
    expect(csv).toContain('RUN-123')
    expect(csv).toContain('completed')
    expect(csv).toContain('2024-03-15')
    expect(csv).toContain('5.5')
    expect(csv).toContain('3.2')
  })

  it('handles missing optional fields', () => {
    const runs = [
      createMockRun({
        actual_total_weight_grams: undefined,
        variance_grams: undefined,
        variance_percentage: undefined,
        duration_hours: undefined,
        printer_name: undefined,
      }),
    ]
    const csv = runsToCSV(runs)
    expect(csv).not.toContain('undefined')
    expect(csv).not.toContain('null')
  })
})

describe('statsToCSV', () => {
  const mockStats: VarianceStats = {
    totalRuns: 100,
    completedRuns: 80,
    averageVarianceGrams: 5.5,
    averageVariancePercent: 3.2,
    maxVarianceGrams: 25,
    minVarianceGrams: -15,
    totalEstimatedGrams: 10000,
    totalActualGrams: 10500,
    runsOverEstimate: 50,
    runsUnderEstimate: 30,
  }

  it('generates report header', () => {
    const csv = statsToCSV(mockStats)
    expect(csv).toContain('Variance Analysis Report')
    expect(csv).toContain('Summary Statistics')
  })

  it('includes all stats', () => {
    const csv = statsToCSV(mockStats)
    expect(csv).toContain('100')
    expect(csv).toContain('80')
    expect(csv).toContain('5.5')
    expect(csv).toContain('3.2')
    expect(csv).toContain('25.0')
    expect(csv).toContain('-15.0')
    expect(csv).toContain('10000.0')
    expect(csv).toContain('10500.0')
    expect(csv).toContain('50')
    expect(csv).toContain('30')
  })

  it('includes date range when provided', () => {
    const csv = statsToCSV(mockStats, {
      start: new Date('2024-01-01'),
      end: new Date('2024-12-31'),
    })
    expect(csv).toContain('2024-01-01')
    expect(csv).toContain('2024-12-31')
  })

  it('handles missing date range', () => {
    const csv = statsToCSV(mockStats)
    expect(csv).toContain('All')
    expect(csv).toContain('Present')
  })
})

describe('getHighVarianceProducts', () => {
  it('returns empty array for empty runs', () => {
    const result = getHighVarianceProducts([])
    expect(result).toHaveLength(0)
  })

  it('returns empty array for runs without items', () => {
    const runs: ProductionRunDetail[] = [
      {
        ...createMockRun(),
        items: [],
      } as ProductionRunDetail,
    ]
    const result = getHighVarianceProducts(runs)
    expect(result).toHaveLength(0)
  })

  it('only considers completed runs', () => {
    const runs: ProductionRunDetail[] = [
      {
        ...createMockRun({ status: 'in_progress', variance_percentage: 50 }),
        items: [
          { model: { id: 'model-1', name: 'Model 1', sku: 'MOD-001' } },
        ],
      } as ProductionRunDetail,
    ]
    const result = getHighVarianceProducts(runs)
    expect(result).toHaveLength(0)
  })

  it('calculates average variance per product', () => {
    const runs: ProductionRunDetail[] = [
      {
        ...createMockRun({ variance_percentage: 10 }),
        items: [{ model: { id: 'model-1', name: 'Model 1', sku: 'MOD-001' } }],
      } as ProductionRunDetail,
      {
        ...createMockRun({ variance_percentage: 20 }),
        items: [{ model: { id: 'model-1', name: 'Model 1', sku: 'MOD-001' } }],
      } as ProductionRunDetail,
    ]
    const result = getHighVarianceProducts(runs)

    expect(result).toHaveLength(1)
    expect(result[0].averageVariancePercent).toBe(15)
    expect(result[0].runCount).toBe(2)
  })

  it('sorts by variance descending', () => {
    const runs: ProductionRunDetail[] = [
      {
        ...createMockRun({ variance_percentage: 5 }),
        items: [{ model: { id: 'model-1', name: 'Low Variance', sku: 'MOD-001' } }],
      } as ProductionRunDetail,
      {
        ...createMockRun({ variance_percentage: 25 }),
        items: [{ model: { id: 'model-2', name: 'High Variance', sku: 'MOD-002' } }],
      } as ProductionRunDetail,
    ]
    const result = getHighVarianceProducts(runs)

    expect(result[0].modelName).toBe('High Variance')
    expect(result[1].modelName).toBe('Low Variance')
  })

  it('applies correct recommendations', () => {
    const runs: ProductionRunDetail[] = [
      {
        ...createMockRun({ variance_percentage: 3 }),
        items: [{ model: { id: 'model-1', name: 'OK', sku: 'MOD-001' } }],
      } as ProductionRunDetail,
      {
        ...createMockRun({ variance_percentage: 10 }),
        items: [{ model: { id: 'model-2', name: 'Review', sku: 'MOD-002' } }],
      } as ProductionRunDetail,
      {
        ...createMockRun({ variance_percentage: 20 }),
        items: [{ model: { id: 'model-3', name: 'Update', sku: 'MOD-003' } }],
      } as ProductionRunDetail,
    ]
    const result = getHighVarianceProducts(runs)

    expect(result.find(p => p.modelName === 'OK')?.recommendation).toBe('ok')
    expect(result.find(p => p.modelName === 'Review')?.recommendation).toBe('review')
    expect(result.find(p => p.modelName === 'Update')?.recommendation).toBe('update')
  })

  it('respects limit parameter', () => {
    const runs: ProductionRunDetail[] = Array.from({ length: 20 }, (_, i) => ({
      ...createMockRun({ variance_percentage: i + 1 }),
      items: [{ model: { id: `model-${i}`, name: `Model ${i}`, sku: `MOD-${i}` } }],
    })) as ProductionRunDetail[]

    const result = getHighVarianceProducts(runs, 5)
    expect(result).toHaveLength(5)
  })
})
