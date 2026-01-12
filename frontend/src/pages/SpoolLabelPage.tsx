/**
 * SpoolLabelPage Component
 *
 * A minimal, print-ready label page optimized for 54mm thermal printers.
 * Displays QR code linking to quick update page, spool ID, and key info.
 * Designed to be screenshot-able for thermal printing apps.
 */

import { useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { QRCodeSVG } from 'qrcode.react'
import { Loader2 } from 'lucide-react'
import { spoolsApi } from '@/lib/api/spools'

export function SpoolLabelPage() {
  const { spoolId } = useParams({ strict: false })

  const { data: spool, isLoading, error } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => spoolsApi.get(spoolId!),
    enabled: !!spoolId,
  })

  // The URL the QR code will link to (quick update page)
  const updateUrl = `https://batchivo.com/filaments/${spoolId}/update`

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !spool) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white p-4">
        <div className="text-center text-gray-600">
          <p className="text-lg font-semibold">Spool not found</p>
          <p className="text-sm">{spoolId}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white text-black p-4">
      {/* Label container - optimized for 54mm width thermal printer */}
      <div className="max-w-[54mm] mx-auto space-y-3">
        {/* QR Code - centered, prominent */}
        <div className="flex justify-center">
          <QRCodeSVG
            value={updateUrl}
            size={140}
            level="M"
            includeMargin={false}
          />
        </div>

        {/* Spool ID - large and prominent */}
        <div className="text-center">
          <div className="text-2xl font-bold font-mono tracking-wide">
            {spool.spool_id}
          </div>
          <div className="w-full h-px bg-gray-300 my-2" />
        </div>

        {/* Material and Brand */}
        <div className="text-center text-sm">
          <div className="font-semibold">
            {spool.material_type_name} • {spool.brand}
          </div>
        </div>

        {/* Color and Finish */}
        <div className="text-center text-sm">
          <div>
            {spool.color}
            {spool.finish && ` • ${spool.finish}`}
          </div>
        </div>

        {/* Special properties */}
        {(spool.translucent || spool.glow || spool.pattern) && (
          <div className="text-center text-xs text-gray-600">
            {[
              spool.translucent && 'Translucent',
              spool.glow && 'Glow',
              spool.pattern,
            ]
              .filter(Boolean)
              .join(' • ')}
          </div>
        )}

        {/* Diameter */}
        <div className="text-center text-xs text-gray-500">
          {spool.diameter}mm
        </div>
      </div>
    </div>
  )
}
