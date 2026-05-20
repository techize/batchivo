/**
 * FilamentTypeRow — desktop table row for a single FilamentType aggregated row.
 * Rendered inside the hidden lg:block table section of FilamentLibrary.
 */

import { TestTube2 } from 'lucide-react'
import { TableRow, TableCell } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { FilamentTypeListItem } from '@/types/filament-type'

interface FilamentTypeRowProps {
  filamentType: FilamentTypeListItem
  onRowClick: (id: string) => void
  onToggleSample: (id: string, hasSample: boolean) => void
  isTogglingId?: string | null
}

export function FilamentTypeRow({
  filamentType,
  onRowClick,
  onToggleSample,
  isTogglingId,
}: FilamentTypeRowProps) {
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
    <TableRow
      className="cursor-pointer hover:bg-muted/50"
      tabIndex={0}
      onClick={() => onRowClick(id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onRowClick(id)
        }
      }}
    >
      {/* Brand */}
      <TableCell className="font-medium">{brand}</TableCell>

      {/* Colour */}
      <TableCell>
        <div className="flex items-center gap-2">
          {normalizedHex && (
            <span
              className="w-3 h-3 rounded-full border border-border flex-shrink-0"
              style={{ backgroundColor: normalizedHex }}
              aria-hidden="true"
            />
          )}
          <span>{color}</span>
        </div>
      </TableCell>

      {/* Material */}
      <TableCell>{material_type_name}</TableCell>

      {/* Spools */}
      <TableCell>
        <Badge variant="secondary">{spool_count} spools</Badge>
      </TableCell>

      {/* Labels */}
      <TableCell>
        <Badge variant={allLabeled ? 'secondary' : 'warning'}>
          {labeled_count}/{spool_count} labeled
        </Badge>
      </TableCell>

      {/* Sample */}
      <TableCell>
        {has_sample ? (
          <Badge variant="success">Sample ✓</Badge>
        ) : (
          <Badge variant="outline">No sample</Badge>
        )}
      </TableCell>

      {/* Actions */}
      <TableCell onClick={(e) => e.stopPropagation()}>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="min-w-[44px] min-h-[44px]"
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
      </TableCell>
    </TableRow>
  )
}
