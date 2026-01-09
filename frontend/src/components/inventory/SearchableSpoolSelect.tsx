/**
 * SearchableSpoolSelect Component
 *
 * A searchable dropdown for selecting spools from inventory.
 * Wraps the Combobox component with spool-specific display logic.
 *
 * Features:
 * - Displays spool_id, material_type, and color
 * - Filters by color name as user types
 * - Shows color swatch when color_hex is available
 * - Displays remaining weight as context
 */

import * as React from 'react'
import { Combobox, type ComboboxOption } from '@/components/ui/combobox'
import type { SpoolResponse } from '@/types/spool'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface SearchableSpoolSelectProps {
  /** Array of spools to display in the dropdown */
  spools: SpoolResponse[]
  /** Currently selected spool ID */
  value?: string
  /** Callback when spool selection changes */
  onValueChange?: (spoolId: string) => void
  /** Placeholder text when no spool is selected */
  placeholder?: string
  /** Text shown when search returns no results */
  emptyText?: string
  /** Additional CSS classes for the trigger button */
  className?: string
  /** Disable the component */
  disabled?: boolean
  /** Filter to exclude certain spools (e.g., already selected ones) */
  excludeSpoolIds?: string[]
}

/**
 * Creates a searchable value string for a spool.
 * The cmdk library filters on this value, so it includes all searchable fields.
 */
function createSearchableValue(spool: SpoolResponse): string {
  return `${spool.spool_id} ${spool.brand} ${spool.color} ${spool.material_type_code}`.toLowerCase()
}

/**
 * Custom render function for dropdown options.
 * Shows color swatch, spool ID, brand, color, material type, and remaining weight.
 */
function renderSpoolOption(
  option: ComboboxOption,
  isSelected: boolean,
  spoolsByValue: Map<string, SpoolResponse>
): React.ReactNode {
  const spool = spoolsByValue.get(option.value)
  if (!spool) return option.label

  return (
    <div className="flex items-center gap-2 w-full">
      {/* Selection indicator */}
      <div
        className={cn(
          'w-4 h-4 rounded-full border flex items-center justify-center flex-shrink-0',
          isSelected ? 'bg-primary border-primary' : 'border-muted-foreground/30'
        )}
      >
        {isSelected && (
          <svg
            className="w-3 h-3 text-primary-foreground"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>

      {/* Color swatch */}
      {spool.color_hex ? (
        <div
          className="w-4 h-4 rounded-full border border-border flex-shrink-0"
          style={{ backgroundColor: `#${spool.color_hex}` }}
          title={spool.color}
        />
      ) : (
        <div className="w-4 h-4 rounded-full border border-dashed border-muted-foreground/50 flex-shrink-0" />
      )}

      {/* Spool details */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium">{spool.spool_id}</span>
          <Badge variant="outline" className="text-xs">
            {spool.material_type_code}
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground truncate">
          {spool.brand} {spool.color}
          {spool.finish && ` (${spool.finish})`}
        </div>
      </div>

      {/* Remaining weight */}
      <div className="text-xs text-muted-foreground text-right flex-shrink-0">
        {spool.remaining_weight.toFixed(0)}g
      </div>
    </div>
  )
}

/**
 * Custom render function for the selected value display.
 * Shows a compact view with color swatch and key info.
 */
function renderSpoolValue(
  option: ComboboxOption | undefined,
  spoolsByValue: Map<string, SpoolResponse>,
  placeholder: string
): React.ReactNode {
  if (!option) return placeholder

  const spool = spoolsByValue.get(option.value)
  if (!spool) return option.label

  return (
    <div className="flex items-center gap-2">
      {/* Color swatch */}
      {spool.color_hex ? (
        <div
          className="w-4 h-4 rounded-full border border-border flex-shrink-0"
          style={{ backgroundColor: `#${spool.color_hex}` }}
        />
      ) : (
        <div className="w-4 h-4 rounded-full border border-dashed border-muted-foreground/50 flex-shrink-0" />
      )}

      {/* Compact spool info */}
      <span className="font-mono text-sm">{spool.spool_id}</span>
      <span className="text-muted-foreground">
        {spool.brand} {spool.color}
      </span>
      <Badge variant="outline" className="text-xs">
        {spool.material_type_code}
      </Badge>
    </div>
  )
}

/**
 * SearchableSpoolSelect Component
 *
 * A searchable dropdown for selecting spools from inventory.
 */
const SearchableSpoolSelect = React.forwardRef<HTMLButtonElement, SearchableSpoolSelectProps>(
  (
    {
      spools,
      value,
      onValueChange,
      placeholder = 'Select a spool...',
      emptyText = 'No spools found.',
      className,
      disabled = false,
      excludeSpoolIds = [],
    },
    ref
  ) => {
    // Create maps for lookups:
    // - spoolsByValue: searchable value → SpoolResponse (for render functions)
    // - valueToId: searchable value → spool ID (for onValueChange)
    // - idToValue: spool ID → searchable value (for converting incoming value prop)
    const { spoolsByValue, valueToId, idToValue, options } = React.useMemo(() => {
      const spoolsByValue = new Map<string, SpoolResponse>()
      const valueToId = new Map<string, string>()
      const idToValue = new Map<string, string>()

      // Build all maps in a single pass
      spools
        .filter((spool) => !excludeSpoolIds.includes(spool.id))
        .forEach((spool) => {
          const searchableValue = createSearchableValue(spool)
          spoolsByValue.set(searchableValue, spool)
          valueToId.set(searchableValue, spool.id)
          idToValue.set(spool.id, searchableValue)
        })

      // Create options using the existing maps
      const options: ComboboxOption[] = spools
        .filter((spool) => !excludeSpoolIds.includes(spool.id))
        .map((spool) => ({
          value: createSearchableValue(spool),
          label: `${spool.spool_id} - ${spool.brand} ${spool.color} (${spool.material_type_code})`,
          disabled: !spool.is_active,
        }))

      return { spoolsByValue, valueToId, idToValue, options }
    }, [spools, excludeSpoolIds])

    // Convert incoming spool ID to searchable value for Combobox
    const comboboxValue = value ? idToValue.get(value) : undefined

    // Handle selection: convert searchable value back to spool ID
    const handleValueChange = React.useCallback(
      (searchableValue: string) => {
        if (!onValueChange) return
        // If empty string (deselection), pass it through
        if (!searchableValue) {
          onValueChange('')
          return
        }
        // Convert searchable value to spool ID
        const spoolId = valueToId.get(searchableValue)
        if (spoolId) {
          onValueChange(spoolId)
        }
      },
      [onValueChange, valueToId]
    )

    // Memoized render functions with access to spoolsByValue
    const renderOption = React.useCallback(
      (option: ComboboxOption, isSelected: boolean) =>
        renderSpoolOption(option, isSelected, spoolsByValue),
      [spoolsByValue]
    )

    const renderValueFn = React.useCallback(
      (option: ComboboxOption | undefined) =>
        renderSpoolValue(option, spoolsByValue, placeholder),
      [spoolsByValue, placeholder]
    )

    return (
      <Combobox
        ref={ref}
        options={options}
        value={comboboxValue}
        onValueChange={handleValueChange}
        placeholder={placeholder}
        searchPlaceholder="Search by color..."
        emptyText={emptyText}
        className={className}
        disabled={disabled}
        renderOption={renderOption}
        renderValue={renderValueFn}
      />
    )
  }
)

SearchableSpoolSelect.displayName = 'SearchableSpoolSelect'

export { SearchableSpoolSelect }
