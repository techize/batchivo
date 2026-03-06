/**
 * AMSSlotIndicator — renders 4 AMS slot swatches for Bambu printers.
 *
 * Active slot gets a ring-2 ring-blue-500 border.
 * Slots without filament are rendered with a muted background.
 */

import { cn } from '@/lib/utils'
import type { AMSSlot } from '@/types/printer'

interface AMSSlotIndicatorProps {
  slots: AMSSlot[]
  /** Index of the currently loaded slot (0-based), or null */
  activeSlotIndex?: number | null
}

export function AMSSlotIndicator({ slots, activeSlotIndex }: AMSSlotIndicatorProps) {
  if (!slots || slots.length === 0) return null

  // Ensure we always render exactly 4 swatches
  const normalised: (AMSSlot | null)[] = Array.from({ length: 4 }, (_, i) => slots[i] ?? null)

  return (
    <div className="flex items-center gap-1.5" aria-label="AMS slots">
      {normalised.map((slot, idx) => {
        const isActive = activeSlotIndex === idx
        const hasFilament = slot?.is_loaded && slot.colour_hex
        const bg = hasFilament ? `#${slot!.colour_hex!.replace('#', '')}` : undefined

        return (
          <div
            key={idx}
            title={slot ? `Slot ${idx + 1}: ${slot.filament_type ?? 'Unknown'}` : `Slot ${idx + 1}: Empty`}
            className={cn(
              'w-7 h-7 rounded-sm border transition-all',
              isActive ? 'ring-2 ring-blue-500' : '',
              !hasFilament ? 'bg-muted border-border' : 'border-transparent',
            )}
            style={bg ? { backgroundColor: bg } : undefined}
          />
        )
      })}
    </div>
  )
}
