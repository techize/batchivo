/**
 * FilamentTypeCard — mobile card for a single FilamentType aggregated row.
 * Rendered inside the lg:hidden section of FilamentLibrary.
 */

import { TestTube2 } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { FilamentTypeListItem } from '@/types/filament-type'

interface FilamentTypeCardProps {
  filamentType: FilamentTypeListItem
  onRowClick: (id: string) => void
  onToggleSample: (id: string, hasSample: boolean) => void
  isTogglingId?: string | null
}

export function FilamentTypeCard({
  filamentType,
  onRowClick,
  onToggleSample,
  isTogglingId,
}: FilamentTypeCardProps) {
  const { id, brand, color, color_hex, material_type_name, has_sample, spool_count, labeled_count } =
    filamentType

  const normalizedHex = color_hex
    ? `#${color_hex.length === 8 ? color_hex.slice(2) : color_hex}`
    : undefined

  const allLabeled = labeled_count === spool_count
  const isToggling = isTogglingId === id

  const toggleAriaLabel = has_sample
    ? `Sample printed for ${brand} ${color} — click to unmark`
    : `Mark sample printed for ${brand} ${color}`

  return (
    <Card className="cursor-pointer" onClick={() => onRowClick(id)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            {/* Brand + colour name + swatch */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-base">{brand}</span>
              {normalizedHex && (
                <span
                  className="w-3 h-3 rounded-full border border-border flex-shrink-0"
                  style={{ backgroundColor: normalizedHex }}
                  aria-hidden="true"
                />
              )}
              <span className="text-sm">{color}</span>
            </div>
            {/* Material */}
            <p className="text-muted-foreground text-sm mt-0.5">{material_type_name}</p>
          </div>

          {/* has_sample toggle */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="min-w-[44px] min-h-[44px] flex-shrink-0"
                  disabled={isToggling}
                  aria-label={toggleAriaLabel}
                  onClick={(e) => {
                    e.stopPropagation()
                    onToggleSample(id, !has_sample)
                  }}
                >
                  <TestTube2
                    className={`h-5 w-5 ${has_sample ? 'text-amber-600' : 'text-muted-foreground'}`}
                  />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {has_sample ? 'Sample printed' : 'Mark sample printed'}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{spool_count} spools</Badge>
          <Badge variant={allLabeled ? 'secondary' : 'warning'}>
            {labeled_count}/{spool_count} labeled
          </Badge>
          {has_sample ? (
            <Badge variant="success">Sample ✓</Badge>
          ) : (
            <Badge variant="outline">No sample</Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
