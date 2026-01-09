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

// Chart color palette matching the app theme
export const CHART_COLORS = {
  primary: 'hsl(var(--primary))',
  secondary: 'hsl(var(--secondary))',
  muted: 'hsl(var(--muted))',
  accent: 'hsl(var(--accent))',
  destructive: 'hsl(var(--destructive))',
  // Semantic colors for variance
  positive: '#22c55e', // green-500
  negative: '#ef4444', // red-500
  neutral: '#6366f1', // indigo-500
  warning: '#f59e0b', // amber-500
  // Series colors
  series: [
    '#6366f1', // indigo
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#14b8a6', // teal
    '#f59e0b', // amber
    '#3b82f6', // blue
  ],
}

// Common chart margin configuration
export const CHART_MARGIN = {
  top: 10,
  right: 10,
  left: 0,
  bottom: 0,
}
