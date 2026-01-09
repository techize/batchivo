import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { spoolsApi } from '@/lib/api/spools'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Loader2, Pencil, Copy, QrCode } from 'lucide-react'
import { SpoolUsageHistory } from './SpoolUsageHistory'

interface ViewSpoolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  spoolId: string | null
  onEdit: (spoolId: string) => void
  onDuplicate: (spoolId: string) => void
}

export function ViewSpoolDialog({
  open,
  onOpenChange,
  spoolId,
  onEdit,
  onDuplicate,
}: ViewSpoolDialogProps) {
  // Fetch the specific spool
  const { data: spool, isLoading } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => spoolsApi.get(spoolId!),
    enabled: !!spoolId && open,
  })

  // Progress bar now shows green for remaining, red for used

  const handleEdit = () => {
    if (spoolId) {
      onOpenChange(false)
      onEdit(spoolId)
    }
  }

  const handleDuplicate = () => {
    if (spoolId) {
      onOpenChange(false)
      onDuplicate(spoolId)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-mono text-xl">
            {spool?.spool_id || 'Loading...'}
          </DialogTitle>
          <DialogDescription>
            Filament spool details
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-3">Loading spool data...</span>
          </div>
        ) : spool ? (
          <div className="space-y-6">
            {/* Status and Progress */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                {spool.is_active ? (
                  <Badge variant="success">Active</Badge>
                ) : (
                  <Badge variant="secondary">Inactive</Badge>
                )}
                {spool.remaining_percentage < 20 && (
                  <Badge variant="warning">Low Stock</Badge>
                )}
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Remaining</span>
                  <span className="font-medium">{spool.remaining_percentage.toFixed(0)}%</span>
                </div>
                {/* Two-colour progress bar: green for remaining, red for used */}
                <div className="h-3 w-full rounded-full overflow-hidden flex">
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
            </div>

            {/* Basic Info */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                Filament Details
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <DetailItem label="Material" value={spool.material_type_name} />
                <DetailItem label="Brand" value={spool.brand} />
                <DetailItem label="Colour" value={spool.color} />
                <DetailItem label="Finish" value={spool.finish || '—'} />
              </div>
            </div>

            {/* Weight Info */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                Weight Tracking
              </h4>
              <div className="grid grid-cols-3 gap-4">
                <DetailItem
                  label="Initial Filament"
                  value={`${spool.initial_weight.toFixed(0)}g`}
                />
                <DetailItem
                  label="Current Filament"
                  value={`${spool.current_weight.toFixed(0)}g`}
                />
                <DetailItem
                  label="Used"
                  value={`${(spool.initial_weight - spool.current_weight).toFixed(0)}g`}
                />
              </div>
              {spool.empty_spool_weight && (
                <div className="grid grid-cols-3 gap-4">
                  <DetailItem
                    label="Empty Spool"
                    value={`${spool.empty_spool_weight.toFixed(0)}g`}
                  />
                  <DetailItem
                    label="Gross Weight"
                    value={`${(spool.current_weight + spool.empty_spool_weight).toFixed(0)}g`}
                  />
                </div>
              )}
            </div>

            {/* Purchase Info */}
            {(spool.purchase_date || spool.purchase_price || spool.supplier) && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                  Purchase Information
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  {spool.purchase_date && (
                    <DetailItem
                      label="Purchase Date"
                      value={new Date(spool.purchase_date).toLocaleDateString()}
                    />
                  )}
                  {spool.purchase_price && (
                    <DetailItem
                      label="Price"
                      value={`£${spool.purchase_price.toFixed(2)}`}
                    />
                  )}
                  {spool.supplier && (
                    <DetailItem label="Supplier" value={spool.supplier} />
                  )}
                </div>
              </div>
            )}

            {/* Batch Info */}
            {(spool.purchased_quantity > 1 || spool.spools_remaining !== spool.purchased_quantity) && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                  Batch Information
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <DetailItem
                    label="Purchased Quantity"
                    value={`${spool.purchased_quantity} spools`}
                  />
                  <DetailItem
                    label="Spools Remaining"
                    value={`${spool.spools_remaining} spools`}
                  />
                </div>
              </div>
            )}

            {/* Organization */}
            {(spool.storage_location || spool.notes) && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                  Organization
                </h4>
                <div className="space-y-4">
                  {spool.storage_location && (
                    <DetailItem label="Storage Location" value={spool.storage_location} />
                  )}
                  {spool.notes && (
                    <div>
                      <span className="text-sm text-muted-foreground">Notes</span>
                      <p className="mt-1 text-sm bg-muted/50 rounded-md p-3">
                        {spool.notes}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Production Usage History */}
            <div className="border-t pt-4">
              <SpoolUsageHistory
                spoolId={spool.id}
                currentWeight={spool.current_weight}
                initialWeight={spool.initial_weight}
              />
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            Spool not found
          </div>
        )}

        <DialogFooter className="flex flex-wrap gap-2 sm:gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Close
          </Button>
          <Button
            type="button"
            variant="outline"
            asChild
            disabled={!spool}
          >
            <Link to="/filaments/$spoolId/label" params={{ spoolId: spool?.id || '' }}>
              <QrCode className="h-4 w-4 mr-2" />
              Print Label
            </Link>
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleDuplicate}
            disabled={!spool}
          >
            <Copy className="h-4 w-4 mr-2" />
            Duplicate
          </Button>
          <Button
            type="button"
            onClick={handleEdit}
            disabled={!spool}
          >
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-sm text-muted-foreground">{label}</span>
      <p className="font-medium">{value}</p>
    </div>
  )
}
