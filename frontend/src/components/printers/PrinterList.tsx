/**
 * PrinterList Component
 *
 * Displays a list of printers with filtering and CRUD operations.
 * Allows managing the printer fleet for production runs.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Plus, Search, Printer as PrinterIcon, Edit, Trash2 } from 'lucide-react'

import { listPrinters } from '@/lib/api/printers'
import type { Printer } from '@/types/printer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { PrinterFormDialog } from './PrinterFormDialog'
import { DeletePrinterDialog } from './DeletePrinterDialog'

export function PrinterList() {
  const [search, setSearch] = useState('')
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | undefined>(undefined)
  const [formDialogOpen, setFormDialogOpen] = useState(false)
  const [editingPrinterId, setEditingPrinterId] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingPrinter, setDeletingPrinter] = useState<Printer | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['printers', { isActiveFilter }],
    queryFn: () =>
      listPrinters({
        is_active: isActiveFilter,
        limit: 100,
      }),
  })

  const printers = data?.printers || []

  // Filter by search (client-side for now since API doesn't have search)
  const filteredPrinters = search
    ? printers.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.manufacturer?.toLowerCase().includes(search.toLowerCase()) ||
          p.model?.toLowerCase().includes(search.toLowerCase())
      )
    : printers

  const activeCount = printers.filter((p) => p.is_active).length
  const inactiveCount = printers.filter((p) => !p.is_active).length

  const handleEdit = (printer: Printer) => {
    setEditingPrinterId(printer.id)
    setFormDialogOpen(true)
  }

  const handleDelete = (printer: Printer) => {
    setDeletingPrinter(printer)
    setDeleteDialogOpen(true)
  }

  const handleAddNew = () => {
    setEditingPrinterId(null)
    setFormDialogOpen(true)
  }

  const formatBedSize = (printer: Printer): string => {
    if (!printer.bed_size_x_mm || !printer.bed_size_y_mm || !printer.bed_size_z_mm) {
      return '-'
    }
    return `${printer.bed_size_x_mm} × ${printer.bed_size_y_mm} × ${printer.bed_size_z_mm}`
  }

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading printers</p>
          <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Printers</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} printers • {activeCount} active • Manage your 3D printer fleet
          </p>
        </div>
        <Button onClick={handleAddNew}>
          <Plus className="mr-2 h-4 w-4" />
          Add Printer
        </Button>
      </div>

      {/* Filters Card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name, manufacturer, or model..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Status Filters */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={isActiveFilter === true ? 'default' : 'outline'}
              size="sm"
              onClick={() => setIsActiveFilter(isActiveFilter === true ? undefined : true)}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-green-500" />
              Active ({activeCount})
            </Button>
            <Button
              variant={isActiveFilter === false ? 'default' : 'outline'}
              size="sm"
              onClick={() => setIsActiveFilter(isActiveFilter === false ? undefined : false)}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-gray-400" />
              Inactive ({inactiveCount})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <PrinterIcon className="h-4 w-4" />
            Printer Fleet
            {data && (
              <Badge variant="secondary" className="ml-2">
                {filteredPrinters.length}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Your 3D printers available for production runs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Loading State */}
          {isLoading && (
            <div className="flex h-[200px] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-3">Loading printers...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && filteredPrinters.length === 0 && (
            <div className="flex h-[200px] items-center justify-center">
              <div className="text-center">
                <PrinterIcon className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">
                  {search
                    ? 'No printers match your search'
                    : 'No printers yet. Add your first printer to get started.'}
                </p>
                {!search && (
                  <Button onClick={handleAddNew} className="mt-4">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Printer
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Card View - Mobile */}
          {!isLoading && filteredPrinters.length > 0 && (
            <div className="lg:hidden space-y-3">
              {filteredPrinters.map((printer) => (
                <div
                  key={printer.id}
                  className="rounded-lg border p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-medium">{printer.name}</div>
                      {(printer.manufacturer || printer.model) && (
                        <p className="text-sm text-muted-foreground">
                          {[printer.manufacturer, printer.model].filter(Boolean).join(' ')}
                        </p>
                      )}
                    </div>
                    <Badge
                      variant="outline"
                      className={
                        printer.is_active
                          ? 'bg-green-500/10 text-green-600 border-green-200'
                          : 'bg-gray-500/10 text-gray-500 border-gray-200'
                      }
                    >
                      {printer.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    {printer.nozzle_diameter_mm && (
                      <span>Nozzle: {printer.nozzle_diameter_mm}mm</span>
                    )}
                    {printer.bed_size_x_mm && (
                      <span>Bed: {formatBedSize(printer)}mm</span>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleEdit(printer)}>
                      <Edit className="h-3 w-3 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleDelete(printer)}
                    >
                      <Trash2 className="h-3 w-3 mr-1" />
                      Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Table View - Desktop */}
          {!isLoading && filteredPrinters.length > 0 && (
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-[180px]">Manufacturer / Model</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[100px] text-right">Nozzle</TableHead>
                    <TableHead className="w-[180px] text-right">Build Volume (mm)</TableHead>
                    <TableHead className="w-[120px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPrinters.map((printer) => (
                    <TableRow key={printer.id} className="group">
                      <TableCell>
                        <span className="font-medium">{printer.name}</span>
                      </TableCell>
                      <TableCell>
                        {printer.manufacturer || printer.model ? (
                          <span className="text-muted-foreground">
                            {[printer.manufacturer, printer.model].filter(Boolean).join(' ')}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            printer.is_active
                              ? 'bg-green-500/10 text-green-600 border-green-200'
                              : 'bg-gray-500/10 text-gray-500 border-gray-200'
                          }
                        >
                          {printer.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {printer.nozzle_diameter_mm ? `${printer.nozzle_diameter_mm}mm` : '-'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatBedSize(printer)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(printer)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => handleDelete(printer)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <PrinterFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        printerId={editingPrinterId}
      />

      <DeletePrinterDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        printer={deletingPrinter}
      />
    </div>
  )
}
