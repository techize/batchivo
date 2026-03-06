/**
 * ToolheadBadge — shows active/inactive toolheads for multi-tool printers (e.g., U1).
 */

import { Badge } from '@/components/ui/badge'

interface ToolheadBadgeProps {
  /** Currently active toolhead name, e.g. 'extruder' */
  activeToolhead: string | null | undefined
  /** All known toolhead names for this printer model */
  allToolheads?: string[]
}

const DEFAULT_TOOLHEADS = ['extruder', 'extruder1']

function labelFor(name: string): string {
  const match = name.match(/\d+$/)
  const num = match ? parseInt(match[0]) + 1 : 1
  return `T${num}`
}

export function ToolheadBadge({ activeToolhead, allToolheads = DEFAULT_TOOLHEADS }: ToolheadBadgeProps) {
  return (
    <div className="flex items-center gap-1" aria-label="Toolheads">
      {allToolheads.map((th) => {
        const isActive = th === activeToolhead
        return (
          <Badge
            key={th}
            variant="outline"
            className={
              isActive
                ? 'bg-primary/10 text-primary border-primary/30 font-medium'
                : 'text-muted-foreground border-border opacity-50'
            }
          >
            {labelFor(th)}
          </Badge>
        )
      })}
    </div>
  )
}
