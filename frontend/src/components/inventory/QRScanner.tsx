/**
 * QRScanner Component
 *
 * Camera-based QR code scanner for quickly updating spool weights.
 * Uses html5-qrcode library for cross-browser camera access.
 */
/* eslint-disable react-refresh/only-export-components */

import { useState, useEffect, useRef, useCallback } from 'react'
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode'
import { Camera, CameraOff, FlipHorizontal, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface QRScannerProps {
  onScan: (data: string) => void
  onError?: (error: string) => void
  className?: string
}

type CameraFacing = 'environment' | 'user'

export function QRScanner({ onScan, onError, className }: QRScannerProps) {
  const [isScanning, setIsScanning] = useState(false)
  const [hasPermission, setHasPermission] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cameraFacing, setCameraFacing] = useState<CameraFacing>('environment')
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const elementId = 'qr-reader'

  // Initialize scanner
  useEffect(() => {
    scannerRef.current = new Html5Qrcode(elementId, {
      formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
      verbose: false,
    })

    return () => {
      if (scannerRef.current?.isScanning) {
        scannerRef.current.stop().catch(console.error)
      }
    }
  }, [])

  // Start scanning
  const startScanning = useCallback(async () => {
    if (!scannerRef.current) return

    setError(null)

    try {
      // Check if camera is available
      const devices = await Html5Qrcode.getCameras()
      if (devices.length === 0) {
        setError('No camera found on this device')
        setHasPermission(false)
        return
      }

      setHasPermission(true)

      await scannerRef.current.start(
        { facingMode: cameraFacing },
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1,
        },
        (decodedText) => {
          // Successful scan - provide haptic feedback if available
          if ('vibrate' in navigator) {
            navigator.vibrate(100)
          }
          onScan(decodedText)
        },
        () => {
          // QR code not found in frame - ignore
        }
      )

      setIsScanning(true)
    } catch (err) {
      console.error('Failed to start scanner:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to access camera'

      if (errorMessage.includes('Permission')) {
        setHasPermission(false)
        setError('Camera permission denied. Please allow camera access and try again.')
      } else if (errorMessage.includes('NotAllowedError')) {
        setHasPermission(false)
        setError('Camera access was blocked. Please enable camera permission in your browser settings.')
      } else {
        setError(errorMessage)
      }

      onError?.(errorMessage)
    }
  }, [cameraFacing, onScan, onError])

  // Stop scanning
  const stopScanning = useCallback(async () => {
    if (!scannerRef.current?.isScanning) return

    try {
      await scannerRef.current.stop()
      setIsScanning(false)
    } catch (err) {
      console.error('Failed to stop scanner:', err)
    }
  }, [])

  // Toggle camera facing
  const toggleCamera = async () => {
    if (isScanning) {
      await stopScanning()
    }
    setCameraFacing((prev) => (prev === 'environment' ? 'user' : 'environment'))
    // Restart with new camera after a brief delay
    setTimeout(() => startScanning(), 100)
  }

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            QR Scanner
          </span>
          {isScanning && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={toggleCamera}
                title="Switch camera"
              >
                <FlipHorizontal className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={stopScanning}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardTitle>
        <CardDescription>
          {isScanning
            ? 'Point your camera at a spool QR code'
            : 'Scan a QR code to quickly update spool weight'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Scanner viewport */}
        <div
          id={elementId}
          className={cn(
            'relative w-full aspect-square rounded-lg overflow-hidden bg-muted',
            !isScanning && 'flex items-center justify-center'
          )}
        >
          {!isScanning && !error && (
            <div className="text-center p-4">
              <CameraOff className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Camera is not active
              </p>
            </div>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-destructive/10 border border-destructive rounded-lg p-3">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Permission denied instructions */}
        {hasPermission === false && (
          <div className="bg-amber-50 dark:bg-amber-950/50 border border-amber-200 rounded-lg p-3">
            <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-2">
              Camera Permission Required
            </p>
            <ol className="text-xs text-amber-700 dark:text-amber-300 list-decimal list-inside space-y-1">
              <li>Click the camera/lock icon in your browser's address bar</li>
              <li>Select "Allow" for camera access</li>
              <li>Refresh the page and try again</li>
            </ol>
          </div>
        )}

        {/* Start/Retry button */}
        {!isScanning && (
          <Button
            className="w-full h-12"
            onClick={startScanning}
          >
            {hasPermission === false ? (
              'Retry Camera Access'
            ) : (
              <>
                <Camera className="mr-2 h-5 w-5" />
                Start Scanning
              </>
            )}
          </Button>
        )}

        {/* Scanning indicator */}
        {isScanning && (
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Scanning for QR code...
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Parse a scanned QR code URL to extract the spool ID
 * Expected formats:
 * - https://nozzly.app/filaments/{spoolId}/update
 * - /filaments/{spoolId}/update
 * - nozzly://spool/{spoolId}
 */
export function parseSpoolQRCode(data: string): string | null {
  // Try URL format: https://nozzly.app/filaments/{spoolId}/update
  const urlMatch = data.match(/\/filaments\/([a-f0-9-]+)\/update/i)
  if (urlMatch) {
    return urlMatch[1]
  }

  // Try deep link format: nozzly://spool/{spoolId}
  const deepLinkMatch = data.match(/nozzly:\/\/spool\/([a-f0-9-]+)/i)
  if (deepLinkMatch) {
    return deepLinkMatch[1]
  }

  // Try UUID format directly (for raw QR codes)
  const uuidMatch = data.match(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i)
  if (uuidMatch) {
    return data
  }

  return null
}
