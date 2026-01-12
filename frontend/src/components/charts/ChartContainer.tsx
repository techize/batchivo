/**
 * Reusable chart container with consistent styling
 */
/* eslint-disable react-refresh/only-export-components */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface ChartContainerProps {
  title: string
  description?: string
  children: React.ReactNode
  className?: string
  actions?: React.ReactNode
}

export function ChartContainer({
  title,
  description,
  children,
  className,
  actions,
}: ChartContainerProps) {
  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-base font-medium">{title}</CardTitle>
          {description && (
            <CardDescription className="text-sm text-muted-foreground">
              {description}
            </CardDescription>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </CardHeader>
      <CardContent className="pt-4">{children}</CardContent>
    </Card>
  )
}

// Chart color palette matching the Batchivo brand theme
export const CHART_COLORS = {
  primary: 'hsl(var(--primary))',
  secondary: 'hsl(var(--secondary))',
  muted: 'hsl(var(--muted))',
  accent: 'hsl(var(--accent))',
  destructive: 'hsl(var(--destructive))',
  // Semantic colors for variance
  positive: '#22c55e', // green-500 (good/success)
  negative: '#f56565', // coral (brand) - error/danger
  neutral: '#1a365d', // navy (brand) - neutral/baseline
  warning: '#d97706', // amber (brand) - warning
  // Series colors - Batchivo brand palette
  series: [
    '#1a365d', // navy (primary)
    '#0d9488', // teal
    '#d97706', // amber
    '#f56565', // coral
    '#2d3748', // charcoal
    '#ea580c', // orange
  ],
}

// Common chart margin configuration
export const CHART_MARGIN = {
  top: 10,
  right: 10,
  left: 0,
  bottom: 0,
}
