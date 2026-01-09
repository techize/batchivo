import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { motion, AnimatePresence } from 'framer-motion'
import { useSwipeable } from 'react-swipeable'
import { ChevronDown, ChevronUp, Pencil, Trash2, Copy, Sparkles, Droplets, QrCode } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { SpoolResponse } from '@/types/spool'

interface SpoolCardProps {
  spool: SpoolResponse
  onUpdateWeight: (spoolId: string) => void
  onEdit: (spoolId: string) => void
  onDelete: (spoolId: string) => void
  onDuplicate: (spoolId: string) => void
  onView: (spoolId: string) => void
  isDuplicating?: boolean
}

export function SpoolCard({ spool, onUpdateWeight, onEdit, onDelete, onDuplicate, onView, isDuplicating }: SpoolCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [swipeOffset, setSwipeOffset] = useState(0)

  const swipeHandlers = useSwipeable({
    onSwiping: (eventData) => {
      // Limit swipe distance
      const offset = Math.max(-100, Math.min(100, eventData.deltaX))
      setSwipeOffset(offset)
    },
    onSwiped: (eventData) => {
      // Trigger action if swiped far enough
      if (eventData.deltaX > 80) {
        // Swipe right - Edit
        onEdit(spool.id)
      } else if (eventData.deltaX < -80) {
        // Swipe left - Delete
        onDelete(spool.id)
      }
      // Reset offset
      setSwipeOffset(0)
    },
    trackMouse: false,
    trackTouch: true,
  })

  // Progress bar uses two-colour display (green for remaining, red for used)

  return (
    <div className="relative" {...swipeHandlers}>
      {/* Swipe action backgrounds */}
      <AnimatePresence>
        {swipeOffset > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: swipeOffset / 100 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-blue-500 rounded-lg flex items-center px-6"
          >
            <Pencil className="h-6 w-6 text-white" />
            <span className="ml-2 text-white font-medium">Edit</span>
          </motion.div>
        )}
        {swipeOffset < 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: Math.abs(swipeOffset) / 100 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-destructive rounded-lg flex items-center justify-end px-6"
          >
            <span className="mr-2 text-white font-medium">Delete</span>
            <Trash2 className="h-6 w-6 text-white" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Card content */}
      <motion.div
        animate={{ x: swipeOffset }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        <Card>
          <CardHeader
            className="pb-3 cursor-pointer"
            onClick={() => onView(spool.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                {/* Color swatch */}
                <div
                  className="w-10 h-10 rounded-md border border-border flex-shrink-0 mt-0.5"
                  style={{
                    backgroundColor: spool.color_hex
                      ? `#${spool.color_hex.length === 8 ? spool.color_hex.slice(2) : spool.color_hex}`
                      : '#e5e7eb'
                  }}
                  title={spool.color_hex ? `#${spool.color_hex}` : 'No color set'}
                />
                <div>
                  <CardTitle className="text-base font-mono">
                    {spool.spool_id}
                  </CardTitle>
                  <CardDescription className="text-sm mt-1">
                    {spool.material_type_code} • {spool.brand} • {spool.color}
                    {spool.finish && <span className="text-muted-foreground"> ({spool.finish})</span>}
                  </CardDescription>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation()
                  setExpanded(!expanded)
                }}
                className="h-8 w-8"
              >
                {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </CardHeader>

          <CardContent className="space-y-3">
            {/* Remaining percentage with two-colour progress bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Remaining</span>
                <span className="font-medium">{spool.remaining_percentage.toFixed(0)}%</span>
              </div>
              <div className="h-2 w-full rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-green-500 transition-all"
                  style={{ width: `${spool.remaining_percentage}%` }}
                />
                <div
                  className="h-full bg-destructive transition-all"
                  style={{ width: `${100 - spool.remaining_percentage}%` }}
                />
              </div>
            </div>

            {/* Status badges */}
            <div className="flex flex-wrap gap-2">
              {spool.is_active ? (
                <Badge variant="success">Active</Badge>
              ) : (
                <Badge variant="secondary">Inactive</Badge>
              )}
              {spool.remaining_percentage < 20 && (
                <Badge variant="warning">Low Stock</Badge>
              )}
              {spool.translucent && (
                <Badge variant="outline" className="gap-1">
                  <Droplets className="h-3 w-3" /> Translucent
                </Badge>
              )}
              {spool.glow && (
                <Badge variant="outline" className="gap-1">
                  <Sparkles className="h-3 w-3" /> Glow
                </Badge>
              )}
              {spool.pattern && (
                <Badge variant="outline">{spool.pattern}</Badge>
              )}
            </div>

            {/* Expandable details */}
            <AnimatePresence>
              {expanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-2 pt-2 border-t"
                >
                  <DetailRow label="Material" value={spool.material_type_name} />
                  <DetailRow label="Diameter" value={`${spool.diameter}mm`} />
                  <DetailRow
                    label="Weight"
                    value={`${spool.current_weight.toFixed(0)}g / ${spool.initial_weight.toFixed(0)}g`}
                  />
                  {(spool.extruder_temp || spool.bed_temp) && (
                    <DetailRow
                      label="Temps"
                      value={`${spool.extruder_temp || '—'}°C / ${spool.bed_temp || '—'}°C (bed)`}
                    />
                  )}
                  {spool.storage_location && (
                    <DetailRow label="Location" value={spool.storage_location} />
                  )}
                  {spool.purchase_date && (
                    <DetailRow
                      label="Purchased"
                      value={new Date(spool.purchase_date).toLocaleDateString()}
                    />
                  )}
                  {spool.supplier && (
                    <DetailRow label="Supplier" value={spool.supplier} />
                  )}
                  {spool.purchase_price && (
                    <DetailRow label="Price" value={`£${spool.purchase_price.toFixed(2)}`} />
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Action buttons */}
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => onUpdateWeight(spool.id)}
              >
                Update Weight
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(spool.id)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                asChild
                title="Print Label"
              >
                <Link to="/filaments/$spoolId/label" params={{ spoolId: spool.id }}>
                  <QrCode className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDuplicate(spool.id)}
                disabled={isDuplicating}
                title="Duplicate spool"
              >
                {isDuplicating ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDelete(spool.id)}
                className="text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string | React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
