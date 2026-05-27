/**
 * AddFilamentDialog — three-screen dialog for adding filament to the library.
 *
 * Screens:
 *   1. mode selector — choose bulk or batch workflow
 *   2. bulk add form — one FilamentType + N spools
 *   3. batch form    — shared weight + accumulator table of color variants
 *
 * All state is held at this Dialog level so back navigation preserves form data (D-23).
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, ChevronDown, Layers, Loader2, Minus, Package, Plus, Trash2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useBulkCreateFilamentType, useBatchCreateFilamentTypes } from '@/hooks/useFilamentTypes'
import { materialTypesApi } from '@/lib/api/spools'
import type { BulkCreateRequest, BatchCreateRequest } from '@/types/filament-type'

// ============================================
// Types
// ============================================

type DialogMode = 'selector' | 'bulk' | 'batch'

type BatchRowEntry = {
  id: string
  brand: string
  color: string
  material_type_id: string
  finish?: string
  color_hex?: string
  notes?: string
}

// ============================================
// Zod Schemas
// ============================================

const bulkSchema = z.object({
  brand: z.string().min(1, 'Brand is required'),
  color: z.string().min(1, 'Color is required'),
  material_type_id: z.string().min(1, 'Material type is required'),
  finish: z.string().optional(),
  notes: z.string().optional(),
  color_hex: z
    .string()
    .regex(/^#[0-9a-fA-F]{6}$/)
    .optional()
    .or(z.literal('')),
  diameter: z.coerce.number().min(0.1).max(5).optional(),
  extruder_temp: z.coerce.number().int().min(150).max(320).optional(),
  bed_temp: z.coerce.number().int().min(0).max(120).optional(),
  density: z.coerce.number().min(0.5).max(2.5).optional(),
  pattern: z.string().optional(),
  translucent: z.boolean().optional(),
  glow: z.boolean().optional(),
  spool_type: z.string().optional(),
  quantity: z.coerce.number().int().min(1, 'Must add at least 1 spool').max(20, 'Maximum 20 spools per batch'),
  initial_weight: z.coerce.number().positive(),
})

const batchEntrySchema = z.object({
  brand: z.string().min(1, 'Brand is required'),
  color: z.string().min(1, 'Color is required'),
  material_type_id: z.string().min(1, 'Material type is required'),
  finish: z.string().optional(),
  color_hex: z
    .string()
    .regex(/^#[0-9a-fA-F]{6}$/)
    .optional()
    .or(z.literal('')),
  notes: z.string().optional(),
})

type BulkFormValues = z.infer<typeof bulkSchema>
type BatchEntryFormValues = z.infer<typeof batchEntrySchema>

// ============================================
// Props
// ============================================

interface AddFilamentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// ============================================
// Component
// ============================================

export function AddFilamentDialog({ open, onOpenChange }: AddFilamentDialogProps) {
  const [mode, setMode] = useState<DialogMode>('selector')
  const [moreOptionsOpen, setMoreOptionsOpen] = useState(false)
  const [sharedWeight, setSharedWeight] = useState(1000)
  const [batchRows, setBatchRows] = useState<BatchRowEntry[]>([])

  const bulkForm = useForm<BulkFormValues>({
    resolver: zodResolver(bulkSchema),
    defaultValues: {
      quantity: 1,
      initial_weight: 1000,
    },
  })

  const batchForm = useForm<BatchEntryFormValues>({
    resolver: zodResolver(batchEntrySchema),
    defaultValues: {
      brand: '',
      color: '',
      material_type_id: '',
    },
  })

  const { data: materialTypes } = useQuery({
    queryKey: ['material-types'],
    queryFn: () => materialTypesApi.list(),
  })

  const bulkMutation = useBulkCreateFilamentType()
  const batchMutation = useBatchCreateFilamentTypes()

  // ============================================
  // Handlers
  // ============================================

  const handleClose = () => {
    bulkForm.reset({ quantity: 1, initial_weight: 1000 })
    batchForm.reset({ brand: '', color: '', material_type_id: '' })
    setBatchRows([])
    setMode('selector')
    setMoreOptionsOpen(false)
    onOpenChange(false)
  }

  const handleBack = () => {
    // DO NOT reset forms — state preserved on back navigation (D-23)
    setMode('selector')
  }

  const handleBulkSubmit = async (values: BulkFormValues) => {
    const payload: BulkCreateRequest = {
      brand: values.brand,
      color: values.color,
      material_type_id: values.material_type_id,
      finish: values.finish || null,
      notes: values.notes || null,
      color_hex: values.color_hex ? values.color_hex.replace('#', '') : null,
      diameter: values.diameter,
      extruder_temp: values.extruder_temp ?? null,
      bed_temp: values.bed_temp ?? null,
      density: values.density ?? null,
      pattern: values.pattern || null,
      translucent: values.translucent,
      glow: values.glow,
      spool_type: values.spool_type || null,
      quantity: values.quantity,
      initial_weight: values.initial_weight,
    }
    await bulkMutation.mutateAsync(payload)
    handleClose()
  }

  const handleAddColor = (values: BatchEntryFormValues) => {
    const newRow: BatchRowEntry = {
      ...values,
      id: crypto.randomUUID(),
    }
    setBatchRows((prev) => [...prev, newRow])
    // Pre-fill from previous entry; clear color for next entry (D-11)
    batchForm.reset({ ...values, color: '' })
  }

  const handleRemoveRow = (id: string) => {
    setBatchRows((prev) => prev.filter((row) => row.id !== id))
  }

  const handleBatchSubmit = async () => {
    if (batchRows.length === 0) return
    const payload: BatchCreateRequest = {
      entries: batchRows.map(({ id: _unused, color_hex, ...rest }) => ({ // eslint-disable-line @typescript-eslint/no-unused-vars
        ...rest,
        color_hex: color_hex ? color_hex.replace('#', '') : null,
      })),
      initial_weight: sharedWeight,
    }
    const lastRow = batchRows[batchRows.length - 1]
    await batchMutation.mutateAsync(payload)
    // Dialog stays open; table clears; form resets to last-used values (D-14)
    setBatchRows([])
    batchForm.reset({
      brand: lastRow.brand,
      color: '',
      material_type_id: lastRow.material_type_id,
      finish: lastRow.finish,
      color_hex: lastRow.color_hex,
      notes: lastRow.notes,
    })
  }

  const handleQuantityChange = (delta: number) => {
    const current = bulkForm.getValues('quantity') ?? 1
    bulkForm.setValue('quantity', Math.max(1, Math.min(20, current + delta)))
  }

  // ============================================
  // Render
  // ============================================

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) handleClose()
        else onOpenChange(true)
      }}
    >
      <DialogContent className="max-w-lg overflow-y-auto max-h-[90vh]">
        <DialogHeader>
          {mode !== 'selector' && (
            <Button
              variant="ghost"
              size="sm"
              className="w-fit"
              onClick={handleBack}
              aria-label="Back to mode selector"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          <DialogTitle>
            {mode === 'selector'
              ? 'How would you like to add filament?'
              : mode === 'bulk'
                ? 'Add filament — batch'
                : 'Add filament — color variants'}
          </DialogTitle>
        </DialogHeader>

        {/* Mode Selector */}
        {mode === 'selector' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 py-2">
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setMode('bulk')}
            >
              <CardHeader>
                <Package className="h-8 w-8 mb-2 text-muted-foreground" />
                <CardTitle className="text-base">Batch of identical spools</CardTitle>
                <CardDescription>
                  Create one filament type and generate multiple spools at once
                </CardDescription>
              </CardHeader>
            </Card>
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setMode('batch')}
            >
              <CardHeader>
                <Layers className="h-8 w-8 mb-2 text-muted-foreground" />
                <CardTitle className="text-base">Multiple color variants</CardTitle>
                <CardDescription>
                  Set a shared weight then add different colors in rapid succession
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        )}

        {/* Bulk Add Form */}
        {mode === 'bulk' && (
          <Form {...bulkForm}>
            <form onSubmit={bulkForm.handleSubmit(handleBulkSubmit)} className="space-y-4">
              {/* Required fields */}
              <FormField
                control={bulkForm.control}
                name="brand"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Brand</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. JAYO" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={bulkForm.control}
                name="color"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Color</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Fire Red" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={bulkForm.control}
                name="material_type_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Material type</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value ?? ''}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select material type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {Array.isArray(materialTypes) &&
                          materialTypes.map((mat) => (
                            <SelectItem key={mat.id} value={mat.id}>
                              {mat.name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Optional fields */}
              <FormField
                control={bulkForm.control}
                name="finish"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Finish</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Matte" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={bulkForm.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Notes</FormLabel>
                    <FormControl>
                      <Input placeholder="Optional notes" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* More options collapsible */}
              <Collapsible open={moreOptionsOpen} onOpenChange={setMoreOptionsOpen}>
                <CollapsibleTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="flex items-center gap-1 text-sm text-muted-foreground p-0 h-auto"
                  >
                    <ChevronDown
                      className={`h-4 w-4 transition-transform ${moreOptionsOpen ? 'rotate-180' : ''}`}
                    />
                    More options
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-4 mt-4">
                  <FormField
                    control={bulkForm.control}
                    name="color_hex"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Color hex</FormLabel>
                        <FormControl>
                          <Input placeholder="#FF5733" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={bulkForm.control}
                    name="diameter"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Diameter (mm)</FormLabel>
                        <FormControl>
                          <Input type="number" step="0.01" placeholder="1.75" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={bulkForm.control}
                      name="extruder_temp"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Extruder temp (°C)</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="220" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={bulkForm.control}
                      name="bed_temp"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Bed temp (°C)</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="60" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={bulkForm.control}
                    name="density"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Density (g/cm³)</FormLabel>
                        <FormControl>
                          <Input type="number" step="0.01" placeholder="1.24" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={bulkForm.control}
                    name="pattern"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Pattern</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. Marble" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={bulkForm.control}
                    name="spool_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Spool type</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. Bambu AMS" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-6">
                    <FormField
                      control={bulkForm.control}
                      name="translucent"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-2 space-y-0">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value ?? false}
                              onChange={field.onChange}
                              className="h-4 w-4"
                            />
                          </FormControl>
                          <FormLabel className="font-normal">Translucent</FormLabel>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={bulkForm.control}
                      name="glow"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-2 space-y-0">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value ?? false}
                              onChange={field.onChange}
                              className="h-4 w-4"
                            />
                          </FormControl>
                          <FormLabel className="font-normal">Glow in the dark</FormLabel>
                        </FormItem>
                      )}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>

              <hr />

              {/* Weight per spool */}
              <FormField
                control={bulkForm.control}
                name="initial_weight"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Weight per spool (g)</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Quantity with +/− controls */}
              <FormField
                control={bulkForm.control}
                name="quantity"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Number of spools</FormLabel>
                    <FormControl>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          className="h-11 w-11"
                          onClick={() => handleQuantityChange(-1)}
                          aria-label="Decrease quantity"
                        >
                          <Minus className="h-4 w-4" />
                        </Button>
                        <Input
                          type="number"
                          min={1}
                          max={20}
                          className="w-16 text-center"
                          value={field.value}
                          onChange={(e) => {
                            const raw = parseInt(e.target.value, 10)
                            if (!isNaN(raw)) {
                              field.onChange(Math.max(1, Math.min(20, raw)))
                            }
                          }}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          className="h-11 w-11"
                          onClick={() => handleQuantityChange(1)}
                          aria-label="Increase quantity"
                        >
                          <Plus className="h-4 w-4" />
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Error display */}
              {bulkMutation.isError && (
                <Alert variant="destructive">
                  <AlertDescription>
                    Something went wrong. Check your connection and try again.
                  </AlertDescription>
                </Alert>
              )}

              {/* Submit */}
              <Button
                type="submit"
                className="w-full"
                disabled={bulkMutation.isPending}
              >
                {bulkMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Adding spools...
                  </>
                ) : (
                  'Add spools'
                )}
              </Button>
            </form>
          </Form>
        )}

        {/* Batch Add Form */}
        {mode === 'batch' && (
          <div className="space-y-4">
            {/* Shared weight at top */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium whitespace-nowrap">Weight per spool (g)</label>
              <Input
                type="number"
                value={sharedWeight}
                onChange={(e) => setSharedWeight(Number(e.target.value))}
                className="w-24"
              />
            </div>

            {/* Entry form */}
            <Form {...batchForm}>
              <form
                onSubmit={batchForm.handleSubmit(handleAddColor)}
                className="space-y-4"
              >
                <FormField
                  control={batchForm.control}
                  name="brand"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Brand</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. JAYO" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={batchForm.control}
                  name="color"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Color</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. Fire Red" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={batchForm.control}
                  name="material_type_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Material type</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value ?? ''}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select material type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {Array.isArray(materialTypes) &&
                            materialTypes.map((mat) => (
                              <SelectItem key={mat.id} value={mat.id}>
                                {mat.name}
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={batchForm.control}
                  name="finish"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Finish</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. Matte" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button type="submit" variant="outline" className="w-full">
                  Add color
                </Button>
              </form>
            </Form>

            {/* Accumulator table */}
            {batchRows.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Brand</TableHead>
                    <TableHead>Color</TableHead>
                    <TableHead>Material</TableHead>
                    <TableHead>Finish</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {batchRows.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell>{row.brand}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          {row.color_hex && (
                            <span
                              className="inline-block h-3 w-3 rounded-full border flex-shrink-0"
                              style={{ backgroundColor: row.color_hex }}
                            />
                          )}
                          {row.color}
                        </div>
                      </TableCell>
                      <TableCell>
                        {materialTypes?.find((m) => m.id === row.material_type_id)?.name ?? '...'}
                      </TableCell>
                      <TableCell>{row.finish ?? '—'}</TableCell>
                      <TableCell>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleRemoveRow(row.id)}
                          aria-label="Remove this entry"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-2">
                Add at least one color variant above to continue
              </p>
            )}

            {/* Error display */}
            {batchMutation.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  Something went wrong. Check your connection and try again.
                </AlertDescription>
              </Alert>
            )}

            {/* Submit all */}
            <Button
              type="button"
              className="w-full"
              disabled={batchRows.length === 0 || batchMutation.isPending}
              onClick={handleBatchSubmit}
            >
              {batchMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit all'
              )}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
