/**
 * SpoolScanPage Component
 *
 * Mobile-first QR code scanner page for quickly updating spool weights.
 * Scans QR codes and redirects to the spool quick-update page.
 */

import { useState, useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { ArrowLeft, ScanLine, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { QRScanner, parseSpoolQRCode } from '@/components/inventory/QRScanner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AppLayout } from '@/components/layout/AppLayout'

export function SpoolScanPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [scanError, setScanError] = useState<string | null>(null)
  const [lastScanned, setLastScanned] = useState<string | null>(null)

  // Handle successful QR code scan
  const handleScan = useCallback(
    (data: string) => {
      setScanError(null)
      setLastScanned(data)

      // Parse the QR code to extract spool ID
      const spoolId = parseSpoolQRCode(data)

      if (spoolId) {
        // Navigate to the quick update page
        navigate({ to: '/filaments/$spoolId/update', params: { spoolId } })
      } else {
        setScanError('Invalid QR code. Please scan a Batchivo spool label.')
      }
    },
    [navigate]
  )

  // Handle scanner errors
  const handleError = useCallback((error: string) => {
    console.error('Scanner error:', error)
  }, [])

  // Show login prompt if not authenticated
  if (!authLoading && !isAuthenticated) {
    const currentPath = window.location.pathname
    return (
      <div className="min-h-screen bg-background p-4 flex items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader className="text-center">
            <CardTitle>Login Required</CardTitle>
            <CardDescription>Please log in to scan spool QR codes</CardDescription>
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

  return (
    <AppLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate({ to: '/dashboard' })}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <ScanLine className="h-6 w-6" />
              Scan Spool QR
            </h1>
            <p className="text-muted-foreground text-sm">
              Scan a spool label to quickly update its weight
            </p>
          </div>
        </div>

        {/* Scanner */}
        <div className="max-w-md mx-auto">
          <QRScanner onScan={handleScan} onError={handleError} />

          {/* Scan error */}
          {scanError && (
            <Card className="mt-4 border-destructive">
              <CardContent className="pt-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-destructive">{scanError}</p>
                    {lastScanned && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Scanned: {lastScanned.slice(0, 50)}
                        {lastScanned.length > 50 ? '...' : ''}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Instructions */}
          <Card className="mt-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">How to Use</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex items-start gap-3">
                <div className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-xs shrink-0">
                  1
                </div>
                <p>Click "Start Scanning" to activate your camera</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-xs shrink-0">
                  2
                </div>
                <p>Point your camera at the QR code on your spool label</p>
              </div>
              <div className="flex items-start gap-3">
                <div className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-xs shrink-0">
                  3
                </div>
                <p>
                  Once scanned, you'll be taken to the weight update page where you can
                  enter the new weight
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Manual entry link */}
          <div className="mt-4 text-center">
            <Button
              variant="link"
              onClick={() => navigate({ to: '/dashboard' })}
            >
              Or select a spool manually from inventory
            </Button>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
