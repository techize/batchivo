/**
 * PrinterCardSkeleton — loading placeholder for PrinterCard.
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function PrinterCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-24" />
        <div className="flex gap-1.5 pt-1">
          <Skeleton className="h-7 w-7 rounded-sm" />
          <Skeleton className="h-7 w-7 rounded-sm" />
          <Skeleton className="h-7 w-7 rounded-sm" />
          <Skeleton className="h-7 w-7 rounded-sm" />
        </div>
      </CardContent>
    </Card>
  )
}
