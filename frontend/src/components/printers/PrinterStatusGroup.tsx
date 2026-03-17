/**
 * PrinterStatusGroup — collapsible group of printer cards for a given status.
 *
 * The 'printing' group never collapses.  All other groups persist their
 * collapsed state to localStorage.
 */

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PrinterCard } from './PrinterCard'
import type { PrinterLiveState, PrinterModelInfo } from '@/types/printer'

const STORAGE_KEY_PREFIX = 'batchivo_printer_group_'

function useCollapsible(groupKey: string, defaultCollapsed = false) {
  const storageKey = `${STORAGE_KEY_PREFIX}${groupKey}`
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored !== null ? stored === 'true' : defaultCollapsed
    } catch {
      return defaultCollapsed
    }
  })

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev
      try { localStorage.setItem(storageKey, String(next)) } catch { /* ignore storage errors */ }
      return next
    })
  }

  return { collapsed, toggle }
}

interface PrinterStatusGroupProps {
  title: string
  groupKey: string
  printers: PrinterLiveState[]
  printerIds: Record<string, string>  // name → id map from REST data
  modelInfoMap: Record<string, PrinterModelInfo>  // model_key → info
  collapsible?: boolean
}

export function PrinterStatusGroup({
  title,
  groupKey,
  printers,
  printerIds,
  modelInfoMap,
  collapsible = true,
}: PrinterStatusGroupProps) {
  const { collapsed, toggle } = useCollapsible(groupKey)

  if (printers.length === 0) return null

  return (
    <div className="space-y-3">
      {/* Group header */}
      <div className="flex items-center gap-2">
        {collapsible ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-sm font-semibold text-foreground hover:bg-transparent"
            onClick={toggle}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4 mr-1" />
            ) : (
              <ChevronDown className="h-4 w-4 mr-1" />
            )}
            {title}
            <span className="ml-2 text-muted-foreground font-normal">({printers.length})</span>
          </Button>
        ) : (
          <div className="flex items-center gap-2 h-7 px-2">
            <span className="text-sm font-semibold">{title}</span>
            <span className="text-sm text-muted-foreground">({printers.length})</span>
          </div>
        )}
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Cards grid */}
      {!collapsed && (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          {printers.map((printer) => {
            const modelInfo = printer.model ? modelInfoMap[printer.model] ?? null : null
            const printerId = printerIds[printer.id] ?? printer.id
            return (
              <PrinterCard
                key={printer.id}
                printer={printer}
                modelInfo={modelInfo}
                printerId={printerId}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
