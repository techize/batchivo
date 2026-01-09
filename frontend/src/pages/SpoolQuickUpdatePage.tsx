/**
 * SpoolQuickUpdatePage Component
 *
 * Mobile-first quick weight update page - the destination of QR code scans.
 * Allows updating spool weight via direct input or scale reading.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from '@tanstack/react-router'
import { Loader2, Scale, Weight, ArrowLeft, Check } from 'lucide-react'
import { spoolsApi } from '@/lib/api/spools'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useAuth } from '@/contexts/AuthContext'

export function SpoolQuickUpdatePage() {
  const { spoolId } = useParams({ strict: false })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isAuthenticated, isLoading: authLoading } = useAuth()

  const [filamentUsed, setFilamentUsed] = useState('')
  const [scaleReading, setScaleReading] = useState('')
  const [inputMode, setInputMode] = useState<'used' | 'scale'>('used')

  const { data: spool, isLoading, error } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => spoolsApi.get(spoolId!),
    enabled: !!spoolId && isAuthenticated,
  })

  const updateMutation = useMutation({
    mutationFn: (newWeight: number) => spoolsApi.updateWeight(spoolId!, newWeight),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['spools'] })
      queryClient.invalidateQueries({ queryKey: ['spool', spoolId] })
      // Navigate to dashboard (filament inventory)
      navigate({ to: '/dashboard' })
    },
  })

  const handleUpdateWeight = () => {
    let newWeight: number

    if (inputMode === 'used') {
      // Filament used mode: subtract used amount from current weight
      const usedAmount = parseFloat(filamentUsed)
      newWeight = (spool?.current_weight || 0) - usedAmount
    } else {
      // Scale reading mode: subtract empty spool weight
      const grossWeight = parseFloat(scaleReading)
      const emptySpoolWeight = spool?.empty_spool_weight || 0
      newWeight = grossWeight - emptySpoolWeight
    }

    if (isNaN(newWeight) || newWeight < 0) {
      return
    }

    updateMutation.mutate(newWeight)
  }

  // Calculate new weight for "used" mode
  const calculatedNewWeightFromUsed = inputMode === 'used' && filamentUsed && spool
    ? Math.max(0, spool.current_weight - parseFloat(filamentUsed))
    : null

  // Calculate filament weight for "scale" mode
  const calculatedFilamentWeight = inputMode === 'scale' && scaleReading
    ? Math.max(0, parseFloat(scaleReading) - (spool?.empty_spool_weight || 0))
    : null

  // Show login prompt if not authenticated
  if (!authLoading && !isAuthenticated) {
    const currentPath = window.location.pathname
    return (
      <div className="min-h-screen bg-background p-4 flex items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <CardTitle>Login Required</CardTitle>
            <CardDescription>
              Please log in to update spool weights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              className="w-full"
              onClick={() => {
                window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
              }}
            >
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !spool) {
    return (
      <div className="min-h-screen bg-background p-4 flex items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <CardTitle className="text-destructive">Spool Not Found</CardTitle>
            <CardDescription>
              Could not find spool: {spoolId}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate({ to: '/dashboard' })}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Inventory
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isUsedValid = filamentUsed && !isNaN(parseFloat(filamentUsed)) && parseFloat(filamentUsed) >= 0
  const isScaleValid = scaleReading && !isNaN(parseFloat(scaleReading)) && parseFloat(scaleReading) >= 0
  const canSubmit = inputMode === 'used' ? isUsedValid : isScaleValid

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-sm mx-auto space-y-4">
        {/* Back button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate({ to: '/dashboard' })}
          className="mb-2"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Inventory
        </Button>

        {/* Spool Info Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-2xl font-mono">{spool.spool_id}</CardTitle>
            <CardDescription>
              {spool.material_type_name} • {spool.brand}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Color info */}
            <div className="flex items-center gap-3">
              {spool.color_hex && (
                <div
                  className="w-8 h-8 rounded-full border-2 border-gray-200"
                  style={{ backgroundColor: `#${spool.color_hex}` }}
                />
              )}
              <div>
                <p className="font-medium">{spool.color}</p>
                {spool.finish && <p className="text-sm text-muted-foreground">{spool.finish}</p>}
              </div>
            </div>

            {/* Current weight display */}
            <div className="bg-muted/50 rounded-lg p-4">
              <div className="text-sm text-muted-foreground">Current Weight</div>
              <div className="text-3xl font-bold">{spool.current_weight.toFixed(0)}g</div>
              <div className="text-sm text-muted-foreground">
                {spool.remaining_percentage.toFixed(0)}% remaining
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weight Update Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Update Weight</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs value={inputMode} onValueChange={(v) => setInputMode(v as 'used' | 'scale')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="used" className="flex items-center gap-2">
                  <Weight className="h-4 w-4" />
                  Used
                </TabsTrigger>
                <TabsTrigger value="scale" className="flex items-center gap-2">
                  <Scale className="h-4 w-4" />
                  Scale
                </TabsTrigger>
              </TabsList>

              <TabsContent value="used" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="filamentUsed">Filament Used (grams)</Label>
                  <Input
                    id="filamentUsed"
                    type="number"
                    inputMode="decimal"
                    placeholder="Enter amount of filament used"
                    value={filamentUsed}
                    onChange={(e) => setFilamentUsed(e.target.value)}
                    className="text-lg h-12"
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter how much filament was used (will be subtracted from current weight)
                  </p>
                </div>

                {/* Calculation breakdown */}
                <div className="bg-muted/50 rounded-lg p-3 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Current weight:</span>
                    <span>{spool.current_weight.toFixed(0)}g</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Filament used:</span>
                    <span>−{filamentUsed || '0'}g</span>
                  </div>
                  <div className="border-t pt-1 flex justify-between font-medium">
                    <span>New weight:</span>
                    <span>
                      {calculatedNewWeightFromUsed !== null
                        ? `${calculatedNewWeightFromUsed.toFixed(0)}g`
                        : `${spool.current_weight.toFixed(0)}g`}
                    </span>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="scale" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="scaleReading">Scale Reading (grams)</Label>
                  <Input
                    id="scaleReading"
                    type="number"
                    inputMode="decimal"
                    placeholder="Enter total scale reading"
                    value={scaleReading}
                    onChange={(e) => setScaleReading(e.target.value)}
                    className="text-lg h-12"
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter the weight shown on your scale (spool + filament)
                  </p>
                </div>

                {/* Calculation breakdown */}
                <div className="bg-muted/50 rounded-lg p-3 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Scale reading:</span>
                    <span>{scaleReading || '—'}g</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Empty spool weight:</span>
                    <span>−{spool.empty_spool_weight || 0}g</span>
                  </div>
                  <div className="border-t pt-1 flex justify-between font-medium">
                    <span>Filament weight:</span>
                    <span>
                      {calculatedFilamentWeight !== null
                        ? `${calculatedFilamentWeight.toFixed(0)}g`
                        : '—'}
                    </span>
                  </div>
                </div>

                {!spool.empty_spool_weight && (
                  <div className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-950/50 p-2 rounded">
                    No empty spool weight recorded. The scale reading will be used directly.
                  </div>
                )}
              </TabsContent>
            </Tabs>

            {/* Update button */}
            <Button
              className="w-full h-14 text-lg"
              onClick={handleUpdateWeight}
              disabled={!canSubmit || updateMutation.isPending}
            >
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Updating...
                </>
              ) : (
                <>
                  <Check className="mr-2 h-5 w-5" />
                  Update Weight
                </>
              )}
            </Button>

            {updateMutation.isError && (
              <p className="text-sm text-destructive text-center">
                Failed to update weight. Please try again.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
