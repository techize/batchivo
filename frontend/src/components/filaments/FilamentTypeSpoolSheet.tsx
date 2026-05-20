/**
 * FilamentTypeSpoolSheet — read-only spool drill-down sheet.
 * Opens from the right when a filament type row is clicked, showing all child spools.
 * Read-only per D-09: no edit, delete, or weight update actions.
 */

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { useFilamentTypeSpools } from '@/hooks/useFilamentTypes'

interface FilamentTypeSpoolSheetProps {
  filamentTypeId: string | null
  filamentTypeName?: string
  spoolCount?: number
  onClose: () => void
}

export function FilamentTypeSpoolSheet({
  filamentTypeId,
  filamentTypeName,
  spoolCount,
  onClose,
}: FilamentTypeSpoolSheetProps) {
  const { data, isLoading, isError } = useFilamentTypeSpools(filamentTypeId)

  return (
    <Sheet
      open={filamentTypeId !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent side="right" className="w-full sm:max-w-[480px]">
        <SheetHeader>
          <SheetTitle>{filamentTypeName ?? 'Spools'}</SheetTitle>
          {spoolCount !== undefined && (
            <SheetDescription>
              {spoolCount} {spoolCount !== 1 ? 'spools' : 'spool'}
            </SheetDescription>
          )}
        </SheetHeader>

        <div className="mt-6">
          {isLoading && (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex gap-4 py-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-16" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <p className="text-destructive text-sm">Could not load spools. Try again.</p>
          )}

          {!isLoading && !isError && data && data.length === 0 && (
            <p className="text-muted-foreground text-sm">
              No spools found for this filament type.
            </p>
          )}

          {!isLoading && !isError && data && data.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Spool ID</TableHead>
                  <TableHead>Weight</TableHead>
                  <TableHead>Labeled</TableHead>
                  <TableHead>Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((spool) => (
                  <TableRow key={spool.id}>
                    <TableCell className="font-mono text-sm">{spool.spool_id}</TableCell>
                    <TableCell>
                      {spool.current_weight.toFixed(0)}g / {spool.initial_weight.toFixed(0)}g
                    </TableCell>
                    <TableCell>
                      {spool.is_labeled ? (
                        <Badge variant="success">Labeled</Badge>
                      ) : (
                        <Badge variant="warning">Needs label</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {spool.is_active ? (
                        <Badge variant="success">Active</Badge>
                      ) : (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
