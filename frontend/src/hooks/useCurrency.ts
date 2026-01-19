/**
 * Currency Hook
 *
 * Provides currency formatting based on tenant settings.
 * Uses the currency symbol from the authenticated user's tenant.
 */

import { useAuth } from '@/contexts/AuthContext'

interface CurrencyConfig {
  code: string
  symbol: string
}

interface UseCurrencyReturn {
  currency: CurrencyConfig
  formatCurrency: (value: string | number) => string
}

/**
 * Hook to access tenant currency settings and formatting
 */
export function useCurrency(): UseCurrencyReturn {
  const { user } = useAuth()

  const currency: CurrencyConfig = {
    code: user?.currency_code || 'GBP',
    symbol: user?.currency_symbol || '£',
  }

  /**
   * Format a numeric value as currency using tenant settings
   */
  const formatCurrency = (value: string | number): string => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value
    if (isNaN(numValue)) {
      return `${currency.symbol}0.00`
    }
    return `${currency.symbol}${numValue.toFixed(2)}`
  }

  return { currency, formatCurrency }
}
